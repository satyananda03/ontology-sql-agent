"""Acronyms, custom prompts and configuration rows in the ``frontend`` schema.

Upstream, the Next.js app owned these tables through Prisma. Here the readers
below serve the SQL agent (the glossary, on every question) and the metadata
endpoint, and the writers serve ``/api/acronyms`` and ``/api/settings``.

The readers are best-effort and swallow errors; the writers raise, because a
failed save must reach the person who made it. Prisma filled ``id`` and
``updated_at`` on the client, so the tables have no defaults for them and every
write sets both itself.
"""

import logging
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from auto_ontology.infra.postgres import FRONTEND_SCHEMA, get_postgres_connection_string

logger = logging.getLogger(__name__)


def fetch_acronyms() -> list[dict[str, str]]:
    """Return acronyms as ``[{"name": ..., "description": ...}, ...]``.

    Shape matches ``AgentState.acronyms`` / the dicts
    consumed by ``rules_to_text`` in the text-to-SQL pipeline.
    """
    try:
        with psycopg.connect(
            get_postgres_connection_string(), connect_timeout=3
        ) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"SELECT name, description FROM {FRONTEND_SCHEMA}.acronyms ORDER BY created_at"
                )
                return [dict(row) for row in cur.fetchall()]
    except Exception:
        # Settings are best-effort: a DB hiccup here must not break a question.
        logger.exception("Failed to fetch acronyms; continuing with empty list")
        return []


def fetch_custom_prompts() -> str:
    """Return all stored prompts joined into one string (blank if none).

    Served by the metadata endpoint; the SQL agent does not read them.
    """
    try:
        with psycopg.connect(
            get_postgres_connection_string(), connect_timeout=3
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT content FROM {FRONTEND_SCHEMA}.prompts")
                rows = cur.fetchall()
    except Exception:
        logger.exception("Failed to fetch custom prompts; continuing with empty string")
        return ""

    contents = [row[0] for row in rows if row[0]]
    return "\n\n".join(contents)


_ACRONYM = "id, name, description, created_at, updated_at"


def _connect() -> psycopg.Connection[dict[str, Any]]:
    return psycopg.connect(
        get_postgres_connection_string(), connect_timeout=3, row_factory=dict_row
    )


def list_acronyms() -> list[dict[str, Any]]:
    """Every acronym with its id and timestamps, by name."""
    with _connect() as conn:
        return conn.execute(
            f"SELECT {_ACRONYM} FROM {FRONTEND_SCHEMA}.acronyms ORDER BY lower(name)"
        ).fetchall()


def create_acronym(name: str, description: str) -> dict[str, Any]:
    """Insert one acronym; a taken name raises ``psycopg.errors.UniqueViolation``."""
    with _connect() as conn:
        row = conn.execute(
            f"INSERT INTO {FRONTEND_SCHEMA}.acronyms "
            "(id, name, description, created_at, updated_at) "
            "VALUES (gen_random_uuid(), %s, %s, now(), now()) "
            f"RETURNING {_ACRONYM}",
            (name, description),
        ).fetchone()
    assert row is not None
    return row


def update_acronym(
    acronym_id: UUID, *, name: str | None, description: str | None
) -> dict[str, Any] | None:
    """Change the given fields; ``None`` when no acronym has *acronym_id*."""
    with _connect() as conn:
        return conn.execute(
            f"UPDATE {FRONTEND_SCHEMA}.acronyms "
            "SET name = COALESCE(%s, name), "
            "description = COALESCE(%s, description), updated_at = now() "
            f"WHERE id = %s RETURNING {_ACRONYM}",
            (name, description, acronym_id),
        ).fetchone()


def delete_acronym(acronym_id: UUID) -> bool:
    """Remove one acronym; ``False`` when it did not exist."""
    with _connect() as conn:
        cursor = conn.execute(
            f"DELETE FROM {FRONTEND_SCHEMA}.acronyms WHERE id = %s", (acronym_id,)
        )
        return cursor.rowcount == 1


def write_configuration(key: str, value: str) -> None:
    """Store *value* under *key* in ``configurations``, replacing any old value."""
    with _connect() as conn:
        conn.execute(
            f"INSERT INTO {FRONTEND_SCHEMA}.configurations (key, value, updated_at) "
            "VALUES (%s, %s, now()) "
            "ON CONFLICT (key) DO UPDATE "
            "SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at",
            (key, value),
        )
