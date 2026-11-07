# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Load and cache SQLDatabase connectors from CONNECTION_STRINGS."""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import urlparse

from auto_ontology.catalog.table_filter import TableFilter, from_connection
from auto_ontology.connectors.base import SQLDatabase

from auto_ontology.connectors.connection_string_factory import build_connection_string
from auto_ontology.connectors.postgres import PostgresDatabase

logger = logging.getLogger(__name__)

# Every connector here MUST expose a ``dialect`` that sqlglot recognises
# (one of ``sqlglot.dialects.DIALECTS``). Callers pass ``connector.dialect``
# straight into ``sqlglot.parse_one(read=...)`` / ``Expression.sql(dialect=...)``
# with no translation layer in between, and sqlglot raises on an unknown
# dialect *name* before it ever looks at the SQL — so a bad name is a hard
# error, not a silent fall back to the generic parser.
#
# The keys are connection-string schemes, not dialects. Only Postgres is
# supported.
CONNECTOR_REGISTRY: dict[str, type[SQLDatabase]] = {
    "postgres": PostgresDatabase,
    "postgresql": PostgresDatabase,
}

_connectors: list[SQLDatabase] | None = None


def parse_connection_strings(raw: str) -> list[str]:
    """Return connection URLs separated by commas, newlines, or both."""
    return [
        connection_string.strip()
        for connection_string in re.split(r"[,\r\n]+", raw)
        if connection_string.strip()
    ]


def _redact(connection_string: str) -> str:
    """Mask the password in a connection string before logging it."""
    parsed = urlparse(connection_string)
    if not parsed.password:
        return connection_string
    return connection_string.replace(parsed.password, "***", 1)


def _table_filter(connection: dict) -> TableFilter:
    """Build the regex table allow/deny filter off a connection dict.

    A malformed pattern is logged and dropped here rather than raised: this runs
    while loading every configured connection, and one bad pattern must not stop
    the others from loading. The API validates patterns on save (422), so an
    invalid one should never reach this point.
    """
    try:
        return from_connection(connection)
    except ValueError:
        logger.exception(
            "Ignoring invalid table filter on connection %r",
            connection.get("database"),
        )
        return TableFilter()


def invalidate_connectors_cache() -> None:
    """Drop cached connectors so the next :func:`get_connectors` reloads."""
    global _connectors
    if _connectors is not None:
        for connector in _connectors:
            try:
                connector.close()
            except Exception:
                logger.exception("Failed to close connector during cache invalidation")
    _connectors = None


def create_connector(
    connection_string: str,
    table_filter: "TableFilter | None" = None,
) -> SQLDatabase:
    """Parse *connection_string*, select a connector class, and return an instance.

    *table_filter* is the connection's regex allow/deny pair, enforced centrally
    in :func:`auto_ontology.catalog.extract.create_dataframe`. Which schemas are
    ingested is set by ``ingest.yaml`` (see ``auto_ontology.catalog.ingest_config``).
    """
    try:
        parsed = urlparse(connection_string)
        scheme = parsed.scheme

        if not scheme:
            raise ValueError("Invalid connection string: No protocol scheme found.")

        connector_type = scheme.split("+", 1)[0].lower()
        connector_class = CONNECTOR_REGISTRY.get(connector_type)

        if connector_class is None:
            raise ValueError(
                f"Unsupported database type: {connector_type!r}. "
                f"Connection string: {_redact(connection_string)}"
            )

        connector = connector_class(connection_string)

        # Carried on the instance rather than passed to __init__: every
        # connector must honour it, and none of them should have to accept a
        # new constructor argument to do so.
        if table_filter is not None and table_filter.active:
            connector.table_filter = table_filter
        return connector

    except Exception:
        logger.exception(
            "Failed to initialize connector for connection string: %s",
            _redact(connection_string),
        )
        raise


def get_connectors() -> list[SQLDatabase]:
    """Return cached connectors for all configured connections.

    Text-to-SQL resolves the execution connector from
    ``relevant_tables[*].database_name`` (see
    ``auto_ontology.retrieval.text_to_sql.connector_routing``).
    Each connector's ``database_name`` must therefore be unique across the
    returned list.
    """
    global _connectors
    if _connectors is None:
        from auto_ontology.dal.connections import list_connections

        # Each spec is (connection_string, table_filter). The table filter is
        # ingestion-only; retrieval executes SQL rather than introspecting.
        try:
            specs: list[tuple[str, TableFilter]] = [
                (build_connection_string(conn), _table_filter(conn))
                for conn in list_connections()
            ]
        except Exception:
            logger.exception("Failed to load connection strings from the catalog")
            specs = []
        if not specs:
            # CONNECTION_STRINGS carries no connection dict, so an env-configured
            # connection cannot express a table filter.
            raw = os.environ.get("CONNECTION_STRINGS", "")
            specs = [
                (connection_string, TableFilter())
                for connection_string in parse_connection_strings(raw)
            ]
        if not specs:
            logger.warning(
                "No connections configured. Add CONNECTION_STRINGS to your .env "
                "or create a connection in Settings → Connections."
            )
            return []

        loaded: list[SQLDatabase] = []
        seen_database_names: set[str] = set()
        for cs, table_filter in specs:
            connector = create_connector(cs, table_filter=table_filter)
            database_name = connector.database_name
            if database_name in seen_database_names:
                logger.warning(
                    "Duplicate connector database_name %r — SQL is routed by "
                    "database_name, so only one connector per name can be used.",
                    database_name,
                )
            seen_database_names.add(database_name)
            loaded.append(connector)
        _connectors = loaded
    return list(_connectors)
