# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Semua route di bawah ``/api``: API review ontologi (auto_ontology) dan SQL agent."""

from fastapi import APIRouter

from auto_ontology.server.datasources.router import router as datasources_router
from auto_ontology.server.exploration.router import router as exploration_router
from auto_ontology.server.health.router import router as health_router
from auto_ontology.server.metadata.router import router as metadata_router
from auto_ontology.server.model_interchange.router import (
    router as model_interchange_router,
)
from auto_ontology.server.rules.router import router as rules_router
from auto_ontology.server.search.router import router as search_router
from auto_ontology.server.semantic_compilation.router import (
    router as semantic_compilation_router,
)
from auto_ontology.server.settings.router import router as settings_router
from auto_ontology.server.sql_attributes.router import router as sql_attributes_router
from auto_ontology.server.tags.router import router as tags_router
from auto_ontology.server.terms.router import router as terms_router
from auto_ontology.server.zones.router import router as zones_router
from sql_agent.api.routes import connection, query

api_router = APIRouter()

# ─── Ontology review API (dipakai dashboard) ───
api_router.include_router(datasources_router, tags=["datasources", "connectors"])
api_router.include_router(exploration_router, tags=["exploration"])
api_router.include_router(metadata_router, tags=["metadata"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(sql_attributes_router, tags=["sql-attributes"])
api_router.include_router(semantic_compilation_router, tags=["semantic-compilation"])
api_router.include_router(zones_router, tags=["zones"])
api_router.include_router(tags_router, tags=["tags"])
api_router.include_router(rules_router, tags=["rules"])
api_router.include_router(terms_router, tags=["terms"])
api_router.include_router(model_interchange_router, tags=["model-interchange"])
api_router.include_router(search_router, tags=["search"])
api_router.include_router(settings_router, tags=["settings"])

# ─── SQL agent ───
api_router.include_router(connection.router, tags=["connection"])
api_router.include_router(query.router, tags=["sql-agent"])
