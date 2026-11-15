# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Aplikasi FastAPI: logging, lifespan, dan route. Dijalankan lewat ``run.py``."""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from auto_ontology.env import load_env
from sql_agent.core.config import settings
from sql_agent.core.logging import get_logger, setup_logging

setup_logging(settings.log_level)
# Sebelum import di bawah: auto_ontology membaca endpoint model dan koneksi
# database dari os.environ, sebagian saat modulnya di-import.
load_env()

from auto_ontology.connectors.registry import source_connection_string  # noqa: E402
from auto_ontology.dal import close_store  # noqa: E402
from auto_ontology.dal.schema_version import require_current_schema  # noqa: E402
from auto_ontology.version import get_app_version  # noqa: E402
from sql_agent.api.router import api_router  # noqa: E402
from sql_agent.services import rerank_service  # noqa: E402
from sql_agent.services.query_service import warm_up  # noqa: E402

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting Auto Ontology API server — app version %s", get_app_version())
    # Before anything else: refuse to serve against a schema this build does not
    # expect. Here rather than in `create_app` deliberately — the OpenAPI spec
    # generator builds the app with no database at all, so requiring one to
    # construct it would break the spec check in CI. The lifespan runs only when
    # the app is actually served.
    require_current_schema()
    # Raises when CLIENT_DATABASE holds more than one database.
    source_connection_string()
    # Background: a slow DB or LLM endpoint must not hold up startup.
    threading.Thread(target=warm_up, name="sql-agent-warm-up", daemon=True).start()
    try:
        yield
    finally:
        await rerank_service.close_client()
        close_store()


def create_app() -> FastAPI:
    """Build the API app without serving it.

    Kept separate from serving so tooling — the OpenAPI spec generator, tests —
    can construct the app and read ``app.openapi()`` without starting uvicorn.
    """
    app = FastAPI(title="Auto Ontology API", lifespan=lifespan)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
