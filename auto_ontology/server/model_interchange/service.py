"""Orchestration for Auto Ontology model YAML export/import."""

import logging
from collections.abc import Mapping
from typing import Any

import yaml

from auto_ontology.connectors import get_connectors
from auto_ontology.dal import model_interchange as dal
from auto_ontology.dal.connections import list_connections
from auto_ontology.server.model_interchange.embed import (
    ImportEmbedBuffer,
    flush_import_embeddings,
)
from auto_ontology.server.model_interchange.schemas import (
    ExportRequest,
    AutoOntologyModelDocument,
    ModelFormat,
)

logger = logging.getLogger(__name__)

_AUTO_ONTOLOGY_ROOT_KEYS = frozenset(AutoOntologyModelDocument.model_fields)


def _dialect_by_database_name() -> dict[str, str]:
    """Resolve SQL dialect strings keyed by catalog database name.

    Live connectors give the most precise dialect, but building them connects
    to every database, and one that cannot be reached would otherwise fail the
    whole export. The dialect is informational in an export, so when that
    happens the saved connection settings are used for every database instead.
    """
    dialects: dict[str, str] = {}
    try:
        connectors = get_connectors()
    except Exception as exc:
        logger.warning(
            "Could not connect to every configured database (%s); exporting "
            "dialects from the saved connection settings instead",
            exc,
        )
        connectors = []
    for connector in connectors:
        database_name = getattr(connector, "database_name", None)
        dialect = getattr(connector, "dialect", None)
        if database_name and dialect:
            dialects[str(database_name)] = str(dialect)

    for connection in list_connections():
        database_name = str(
            connection.get("database")
            or connection.get("database_name")
            or connection.get("name")
            or "",
        )
        if not database_name or database_name in dialects:
            continue
        dialect = connection.get("dialect") or connection.get("type") or ""
        dialects[database_name] = str(dialect)
    return dialects


def require_auto_ontology_document(payload: Mapping[str, Any]) -> None:
    """Refuse a document whose root holds none of Auto Ontology's own keys.

    Read as a model anyway, it would validate as an empty document, and an
    import with ``replace`` would then wipe the catalog.
    """
    if not _AUTO_ONTOLOGY_ROOT_KEYS.intersection(payload):
        raise ValueError(
            "Not an Auto Ontology model: the root must hold one of "
            + ", ".join(sorted(_AUTO_ONTOLOGY_ROOT_KEYS))
        )


def _dump_yaml(document: AutoOntologyModelDocument) -> str:
    return yaml.safe_dump(
        document.model_dump(mode="python"),
        sort_keys=False,
        default_flow_style=False,
    )


def _export_document(request: ExportRequest) -> AutoOntologyModelDocument:
    """Assemble the native model document for the databases *request* scopes."""
    database_ids = request.databases
    dal.validate_database_ids(database_ids)
    rows = dal.fetch_export_rows(database_ids)
    return dal.assemble_export_document(
        rows,
        dialect_by_db_name=_dialect_by_database_name(),
        sql_column_resolver=dal.make_cached_sql_column_resolver(),
    )


def export_model(request: ExportRequest) -> str:
    """Export the scoped model document as a YAML string."""
    return _dump_yaml(_export_document(request))


def import_model(
    yaml_text: str,
    *,
    replace: bool = True,
    embed: bool = True,
) -> dict[str, Any]:
    """Validate and apply an Auto Ontology model YAML document."""
    payload = yaml.safe_load(yaml_text)
    if not isinstance(payload, dict):
        raise ValueError("YAML document must deserialize to a mapping")
    require_auto_ontology_document(payload)
    document = AutoOntologyModelDocument.model_validate(payload)
    embed_buffer = ImportEmbedBuffer() if embed else None
    summary = dal.apply_import_model(
        document,
        replace=replace,
        embed_buffer=embed_buffer,
    )
    summary["format"] = ModelFormat.AUTO_ONTOLOGY.value
    if embed and embed_buffer is not None:
        summary["embeddings"] = flush_import_embeddings(embed_buffer)
    return summary
