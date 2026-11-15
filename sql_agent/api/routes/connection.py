# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""The one source database, for the review UI: its connection and its ingest."""

from urllib.parse import unquote, urlparse

from fastapi import APIRouter, HTTPException

from auto_ontology.connectors.registry import source_connection_string
from auto_ontology.server.ingestion.proxy import is_ingest_running, trigger_ingest_run
from sql_agent.schemas import IngestStatus, SourceConnection

router = APIRouter()


@router.get("/connection", response_model=SourceConnection)
def get_connection() -> SourceConnection:
    """The source database from ``CLIENT_DATABASE``, without its password.

    It is the only source: change it in ``.env`` and restart both services.
    404 when ``CLIENT_DATABASE`` is empty.
    """
    url = source_connection_string()
    if url is None:
        raise HTTPException(status_code=404, detail="CLIENT_DATABASE is empty.")
    parsed = urlparse(url)
    return SourceConnection(
        database=unquote(parsed.path.lstrip("/")),
        host=parsed.hostname or "",
        port=parsed.port or 5432,
        user=unquote(parsed.username or ""),
    )


@router.post("/ingest", status_code=202, response_model=IngestStatus)
def start_ingest() -> IngestStatus:
    """Re-ingest the source database's structure into the catalog.

    Runs on the ingestion service, after any compilation in flight. 502 when
    that service cannot be reached.
    """
    try:
        trigger_ingest_run()
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="Ingestion service tidak terjangkau di :3002."
        ) from exc
    return IngestStatus(running=True)


@router.get("/ingest/status", response_model=IngestStatus)
def ingest_status() -> IngestStatus:
    """Whether an ingest pass is running; False when the service is unreachable."""
    return IngestStatus(running=is_ingest_running())
