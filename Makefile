# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

TAG ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)

.PHONY: help build up ingest-dev backend-dev migrate migrate-check \
        migrate-revision lint test eval eval-report ui ui-build

help:
	@echo "  make build                     Build the backend image (host arch)"
	@echo "  make up                        Start postgres, migrate, backend, ingestion"
	@echo "  make ingest-dev                Ingestion service on :3002 from source"
	@echo "  make backend-dev               FastAPI on :3001 with hot reload"
	@echo "  make migrate                   Apply Alembic migrations"
	@echo "  make migrate-check             Fail if the schema drifted from the metadata"
	@echo "  make migrate-revision m=\"...\"  Autogenerate a revision from dal/schema.py"
	@echo "  make lint                      Ruff check and format check"
	@echo "  make test                      Backend and agent tests"
	@echo "  make eval                      Ask the golden questions, write runs/agent.jsonl"
	@echo "  make eval-report               Score runs/*.jsonl against the golden SQL"
	@echo "  make ui                        Review UI on http://127.0.0.1:5173 (needs the backend)"
	@echo "  make ui-build                  Type-check and build the review UI"

build:
	docker build -t ontology-sql-agent:$(TAG) -t ontology-sql-agent:latest .

up:
	docker compose up -d --build

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
	uv run ruff check auto_ontology ontology_sql_agent dev_tools
	uv run ruff format --check auto_ontology ontology_sql_agent dev_tools

test:
	uv run pytest auto_ontology ontology_sql_agent dev_tools -q

eval:
	uv run python -m ontology_sql_agent.eval.run --out runs/agent.jsonl

eval-report:
	uv run python -m ontology_sql_agent.eval.report runs/*.jsonl

ui:
	npm --prefix ui install --no-audit --no-fund
	npm --prefix ui run dev

ui-build:
	npm --prefix ui ci --no-audit --no-fund
	npm --prefix ui run build
