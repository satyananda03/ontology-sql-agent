# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Ingestion service.

Serves a FastAPI app and holds two on-demand schedulers in the app lifespan:

* :class:`DataScheduler` — ingest of the source database, ``POST /ingest/run``.
* :class:`SemanticScheduler` — semantic compilation over the catalog that
  ingest writes, ``POST /semantic/compile`` (and after ``POST /semantic/reset``).

Nothing runs on startup or on a timer: the review UI's buttons trigger each
job. They share one lock, so ingest and compilation never run at once.

Usage::

    uv run --no-sync python -m auto_ontology.ingestion_service
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
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
    # Same gate as the API server: this service writes the catalog, so against a
    # schema it does not expect every ingest fails partway through instead of
    # not starting. Worse here than there, because a scheduler runs unattended —
    # nobody is watching a request come back 500, so the failure surfaces as an
    # empty catalog hours later.
    require_current_schema()
    # Raises when CONNECTION_STRINGS holds more than one database.
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


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info(
        "Starting Auto Ontology Ingestion Service — app version %s", get_app_version()
    )
    uvicorn.run(
        app,
        # Loopback by default: the service has no login. A container sets 0.0.0.0.
        host=os.environ.get("BIND_HOST", "127.0.0.1"),
        port=int(os.environ.get("INGESTION_PORT", "3002")),
        log_config=None,
    )


if __name__ == "__main__":
    main()
