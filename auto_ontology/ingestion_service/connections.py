"""Resolve configured connections for the ingestion-service schedulers.

The one connection comes from the ``CONNECTION_STRINGS`` env var (see
``auto_ontology.connectors.registry.source_connection_string``). Both the data and
semantic schedulers resolve through here so they see the same database.
"""

import logging

from auto_ontology.connectors.registry import create_connector, source_connection_string

logger = logging.getLogger(__name__)


def resolve_connection_strings() -> list[str]:
    """Return the connection string to process this pass: one, or none when unset."""
    url = source_connection_string()
    return [url] if url else []


def resolve_database_names() -> list[str]:
    """Return the distinct database names behind the configured connections.

    The name is read from the connector (``SELECT current_database()`` on
    Postgres, etc.) so it matches exactly what ingestion used as the catalog /
    VDB key — the same value ``run_ingest`` derives. A connection that can't be
    opened is skipped rather than failing the whole pass.
    """
    names: list[str] = []
    for connection_string in resolve_connection_strings():
        try:
            connector = create_connector(connection_string)
        except Exception:
            logger.exception("connections: failed to open connector; skipping")
            continue
        try:
            name = str(connector.database_name or "").strip()
        finally:
            connector.close()
        if name:
            names.append(name)
    # Preserve order, drop duplicates.
    return list(dict.fromkeys(names))
