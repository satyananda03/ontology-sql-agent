"""FastAPI application entry-point — middleware, routers, lifespan."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from auto_ontology.env import load_env

import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

load_env()

logger = logging.getLogger(__name__)

from auto_ontology.version import get_app_version  # noqa: E402
from auto_ontology.dal import close_store  # noqa: E402
from auto_ontology.connectors.registry import source_connection_string  # noqa: E402
from auto_ontology.dal.schema_version import require_current_schema  # noqa: E402
from auto_ontology.server.datasources.router import router as datasources_router  # noqa: E402
from auto_ontology.server.exploration.router import router as exploration_router  # noqa: E402
from auto_ontology.server.health.router import router as health_router  # noqa: E402
from auto_ontology.server.metadata.router import router as metadata_router  # noqa: E402
from auto_ontology.server.rules.router import router as rules_router  # noqa: E402
from auto_ontology.server.semantic_compilation.router import (  # noqa: E402
    router as semantic_compilation_router,
)
from auto_ontology.server.sql_attributes.router import router as sql_attributes_router  # noqa: E402
from auto_ontology.server.users.router import router as users_router  # noqa: E402
from auto_ontology.server.zones.router import router as zones_router  # noqa: E402
from auto_ontology.server.tags.router import router as tags_router  # noqa: E402
from auto_ontology.server.terms.router import router as terms_router  # noqa: E402
from auto_ontology.server.model_interchange.router import (  # noqa: E402
    router as model_interchange_router,
)
from auto_ontology.server.search.router import router as search_router  # noqa: E402
from auto_ontology.server.settings.router import router as settings_router  # noqa: E402
from sql_agent.server.connection import router as connection_router  # noqa: E402
from sql_agent.server.router import router as sql_agent_router  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Before anything else: refuse to serve against a schema this build does not
    # expect. Here rather than in `create_app` deliberately — the OpenAPI spec
    # generator builds the app with no database at all (see that docstring), so
    # requiring one to construct it would break the spec check in CI. The
    # lifespan runs only when the app is actually served, which covers both
    # documented commands: `python -m auto_ontology.server` and `uvicorn ... --factory`.
    require_current_schema()
    # Raises when CONNECTION_STRINGS holds more than one database.
    source_connection_string()
    try:
        yield
    finally:
        close_store()


def create_app() -> FastAPI:
    """Build the API app without serving it.

    Kept separate from ``main`` so tooling — the OpenAPI spec generator,
    tests — can construct the app and read ``app.openapi()`` without
    starting uvicorn.
    """
    app = FastAPI(title="Auto Ontology API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        datasources_router, prefix="/api", tags=["datasources", "connectors"]
    )
    app.include_router(exploration_router, prefix="/api", tags=["exploration"])
    app.include_router(connection_router, prefix="/api", tags=["connection"])
    app.include_router(metadata_router, prefix="/api", tags=["metadata"])
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(sql_attributes_router, prefix="/api", tags=["sql-attributes"])
    app.include_router(
        semantic_compilation_router, prefix="/api", tags=["semantic-compilation"]
    )
    app.include_router(zones_router, prefix="/api", tags=["zones"])
    app.include_router(users_router, prefix="/api", tags=["users"])
    app.include_router(tags_router, prefix="/api", tags=["tags"])
    app.include_router(rules_router, prefix="/api", tags=["rules"])
    app.include_router(terms_router, prefix="/api", tags=["terms"])
    app.include_router(
        model_interchange_router, prefix="/api", tags=["model-interchange"]
    )
    app.include_router(search_router, prefix="/api", tags=["search"])
    app.include_router(settings_router, prefix="/api", tags=["settings"])
    app.include_router(sql_agent_router, prefix="/api", tags=["sql-agent"])

    return app


def main() -> None:
    logger.info("Starting Auto Ontology API server — app version %s", get_app_version())

    app = create_app()

    uvicorn.run(
        app,
        # Loopback by default: the API has no login. A container sets 0.0.0.0.
        host=os.environ.get("BIND_HOST", "127.0.0.1"),
        port=3001,
        log_config=None,
    )


if __name__ == "__main__":
    main()
