# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""create the frontend settings tables when absent

Revision ID: 5d2e8b7c41af
Revises: 99d4d343dd0b
Create Date: 2026-11-08 00:00:00

``frontend.configurations`` and ``frontend.acronyms`` were created by the
upstream Next.js app through Prisma. This repository has no Prisma, yet the
backend reads both (feature flags, the glossary) and now writes them through
``/api/settings`` and ``/api/acronyms``. A fresh database therefore needs them
created here, in the exact shape Prisma gave them, so an existing store that
Prisma already populated is left untouched.

Every statement is guarded by an existence check rather than ``IF NOT
EXISTS``: Postgres checks the CREATE privilege before it looks for the object,
so a role that does not own the existing ``frontend`` schema would fail on a
no-op. ``alembic/env.py`` keeps ``frontend`` out of autogenerate, which is why
this migration is written by hand.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "5d2e8b7c41af"
down_revision: str | Sequence[str] | None = "99d4d343dd0b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the schema and both tables, each only when missing."""
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regnamespace('frontend') IS NULL THEN
                CREATE SCHEMA frontend;
            END IF;
            IF to_regclass('frontend.configurations') IS NULL THEN
                CREATE TABLE frontend.configurations (
                    key        text PRIMARY KEY,
                    value      text NOT NULL,
                    updated_at timestamptz NOT NULL
                );
            END IF;
            IF to_regclass('frontend.acronyms') IS NULL THEN
                CREATE TABLE frontend.acronyms (
                    id          uuid PRIMARY KEY,
                    name        text NOT NULL,
                    description text NOT NULL DEFAULT '',
                    created_at  timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at  timestamptz NOT NULL
                );
                CREATE UNIQUE INDEX acronyms_name_key ON frontend.acronyms (name);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Keep the tables: on an existing store they belong to Prisma's data."""
