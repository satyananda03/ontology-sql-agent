"""Limit what ingestion reads, per database, from an optional YAML file.

The file is ``ingest.yaml`` at the repo root, or ``INGEST_CONFIG_FILE``::

    databases:
      sales_db:
        schemas: [analytics]
        exclude_tables: [tmp_import]

A missing file, or a database it does not list, means everything is ingested.
Connection credentials do not belong here; they stay in ``CONNECTION_STRINGS``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "ingest.yaml"


def _names(scope: dict[str, Any], key: str, path: Path) -> set[str]:
    value = scope.get(key) or []
    if not isinstance(value, list):
        raise ValueError(f"{path}: {key} must be a list of names")
    return {str(name).lower() for name in value}


def load_scope(database_name: str) -> tuple[set[str], set[str]]:
    """Return lowercased ``(schemas, exclude_tables)`` for *database_name*.

    A malformed file raises rather than being ignored: ingesting everything the
    operator meant to exclude is the wrong way to fail.
    """
    path = Path(os.environ.get("INGEST_CONFIG_FILE") or _DEFAULT_PATH)
    if not path.is_file():
        return set(), set()
    config = yaml.safe_load(path.read_text()) or {}
    databases = config.get("databases") if isinstance(config, dict) else None
    if not isinstance(databases, dict):
        raise ValueError(f"{path}: expected a top-level 'databases' mapping")
    scope = databases.get(database_name) or {}
    if not isinstance(scope, dict):
        raise ValueError(f"{path}: {database_name} must be a mapping")
    return _names(scope, "schemas", path), _names(scope, "exclude_tables", path)


def _keep(
    frame: pd.DataFrame | None, schemas: set[str], excluded: set[str]
) -> pd.DataFrame | None:
    if frame is None or frame.empty:
        return frame
    keep = pd.Series(True, index=frame.index)
    if schemas and "table_schema" in frame.columns:
        keep &= frame["table_schema"].astype(str).str.lower().isin(schemas)
    if excluded and "table_name" in frame.columns:
        keep &= ~frame["table_name"].astype(str).str.lower().isin(excluded)
    return frame[keep]


def apply(
    database_name: str, *frames: pd.DataFrame | None
) -> list[pd.DataFrame | None]:
    """Filter *frames*, the first of which must be the table listing.

    Raises when a listed schema matches no table. Ingest deletes catalog schemas
    it no longer sees, so a typo must not read as "this schema is gone".
    """
    schemas, excluded = load_scope(database_name)
    if not schemas and not excluded:
        return list(frames)

    tables = frames[0]
    found = (
        set()
        if tables is None or tables.empty
        else set(tables["table_schema"].astype(str).str.lower())
    )
    if missing := schemas - found:
        raise ValueError(
            f"Ingest config for {database_name}: no readable tables in schema(s) "
            f"{sorted(missing)}. Found: {sorted(found)}"
        )
    filtered = [_keep(frame, schemas, excluded) for frame in frames]
    logger.info(
        "Ingest config for %s kept %d of %d table(s)",
        database_name,
        len(filtered[0]),
        len(tables),
    )
    return filtered
