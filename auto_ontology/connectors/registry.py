"""Load and cache the SQLDatabase connector for the one source database.

The source database comes from ``CONNECTION_STRINGS`` only, and it must hold
exactly one connection: this build answers from a single database.
"""

import logging
import os
import re
from urllib.parse import urlparse

from auto_ontology.catalog.table_filter import TableFilter
from auto_ontology.connectors.base import SQLDatabase
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


def source_connection_string() -> str | None:
    """The source database's URL from ``CONNECTION_STRINGS``, or None when unset.

    More than one URL is a configuration error, not a list to route between:
    this build supports a single source database.
    """
    connection_strings = parse_connection_strings(
        os.environ.get("CONNECTION_STRINGS", "")
    )
    if len(connection_strings) > 1:
        raise ValueError(
            f"CONNECTION_STRINGS holds {len(connection_strings)} connections; "
            "this build supports exactly one source database."
        )
    return connection_strings[0] if connection_strings else None


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
    """Return the cached connector for the source database.

    Still a list, so the retrieval and ingestion code written for several
    databases keeps working unchanged; it holds at most one connector.
    """
    global _connectors
    if _connectors is None:
        url = source_connection_string()
        if url is None:
            logger.warning(
                "No connection configured. Add CONNECTION_STRINGS to your .env."
            )
            return []
        _connectors = [create_connector(url)]
    return list(_connectors)
