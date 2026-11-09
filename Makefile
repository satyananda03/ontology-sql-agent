TAG ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)

.PHONY: help build up dev ingest-dev backend-dev migrate migrate-check \
        migrate-revision lint test openapi ui ui-build

help:
	@echo "  make build                     Build the backend image (host arch)"
	@echo "  make up                        Start postgres, migrate, backend, ingestion"
	@echo "  make dev                       ingest-dev, backend-dev and ui in one terminal"
	@echo "  make ingest-dev                Ingestion service on :3002 from source"
	@echo "  make backend-dev               FastAPI on :3001 with hot reload"
	@echo "  make migrate                   Apply Alembic migrations"
	@echo "  make migrate-check             Fail if the schema drifted from the metadata"
	@echo "  make migrate-revision m=\"...\"  Autogenerate a revision from dal/schema.py"
	@echo "  make lint                      Ruff check and format check"
	@echo "  make test                      Backend and agent tests"
	@echo "  make openapi                   Regenerate docs/openapi/ after an API change"
	@echo "  make ui                        Review UI on http://127.0.0.1:5173 (needs the backend)"
	@echo "  make ui-build                  Type-check and build the review UI"

build:
	docker build -t ontology-sql-agent:$(TAG) -t ontology-sql-agent:latest .

up:
	docker compose up -d --build

# The three dev processes in one terminal, each line prefixed with its name.
# Background jobs ignore SIGINT, so the trap turns Ctrl+C into a TERM for the
# whole group; `wait -n` stops the other two when one exits, so a backend that
# refuses to start is not buried under the others' logs.
dev: SHELL := /bin/bash
dev:
	@export PYTHONUNBUFFERED=1; \
	trap 'trap - INT TERM EXIT; kill 0' INT TERM EXIT; \
	$(MAKE) --no-print-directory ingest-dev 2>&1 | sed -u 's/^/[ingest]  /' & \
	$(MAKE) --no-print-directory backend-dev 2>&1 | sed -u 's/^/[backend] /' & \
	$(MAKE) --no-print-directory ui 2>&1 | sed -u 's/^/[ui]      /' & \
	wait -n

ingest-dev:
	uv run python -m auto_ontology.ingestion_service

backend-dev:
	uv run uvicorn auto_ontology.server.__main__:create_app --factory --reload --host 127.0.0.1 --port 3001

migrate:
	uv run alembic upgrade head

# Fails when auto_ontology/dal/schema.py and the database disagree: a schema
# change committed without its migration is invisible until deploy.
migrate-check:
	uv run alembic check

migrate-revision:
	@test -n "$(m)" || (echo 'usage: make migrate-revision m="what changed"' >&2; exit 2)
	uv run alembic revision --autogenerate -m "$(m)"

lint:
	uv run ruff check auto_ontology sql_agent
	uv run ruff format --check auto_ontology sql_agent

test:
	uv run pytest auto_ontology sql_agent -q

# The dashboard's TypeScript types are generated from docs/openapi/backend.json.
openapi:
	uv run python -m sql_agent.openapi

ui:
	npm --prefix dashboard install --no-audit --no-fund
	npm --prefix dashboard run dev

ui-build:
	npm --prefix dashboard ci --no-audit --no-fund
	npm --prefix dashboard run build
