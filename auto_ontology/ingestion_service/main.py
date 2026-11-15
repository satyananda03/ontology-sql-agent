"""Ingestion service.

Serves a FastAPI app and holds two on-demand schedulers in the app lifespan:

* :class:`DataScheduler` — ingest of the source database, ``POST /ingest/run``.
* :class:`SemanticScheduler` — semantic compilation over the catalog that
  ingest writes, ``POST /semantic/compile`` (and after ``POST /semantic/reset``).

Nothing runs on startup or on a timer: the review UI's buttons trigger each
job. They share one lock, so ingest and compilation never run at once.

Usage::

    uv run python run.py ingestion
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from auto_ontology.env import load_env

load_env()

from auto_ontology.connectors.registry import source_connection_string  # noqa: E402
from auto_ontology.dal.schema_version import require_current_schema  # noqa: E402
from auto_ontology.ingestion_service.data_scheduler import DataScheduler  # noqa: E402
from auto_ontology.ingestion_service.router import router  # noqa: E402
from auto_ontology.ingestion_service.semantic_scheduler import SemanticScheduler  # noqa: E402
from auto_ontology.version import get_app_version  # noqa: E402

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting Auto Ontology Ingestion Service — app version %s", get_app_version()
    )
    # Same gate as the API server: this service writes the catalog, so against a
    # schema it does not expect every ingest fails partway through instead of
    # not starting. Worse here than there, because a scheduler runs unattended —
    # nobody is watching a request come back 500, so the failure surfaces as an
    # empty catalog hours later.
    require_current_schema()
    # Raises when CLIENT_DATABASE holds more than one database.
    source_connection_string()

    # Nothing runs until the review UI triggers it: both schedulers wait for
    # the router. One lock, so ingest and compilation never overlap.
    # uvicorn owns SIGINT/SIGTERM; stop() unwinds each scheduler's wait.
    jobs = asyncio.Lock()
    data_scheduler = DataScheduler(lock=jobs)
    semantic_scheduler = SemanticScheduler(lock=jobs)
    app.state.data_scheduler = data_scheduler
    app.state.semantic_scheduler = semantic_scheduler
    data_scheduler.start()
    semantic_scheduler.start()
    try:
        yield
    finally:
        await data_scheduler.stop()
        await semantic_scheduler.stop()
        logger.info("ingestion_service: shutting down")


app = FastAPI(title="Auto Ontology Ingestion Service", lifespan=lifespan)
app.include_router(router)
