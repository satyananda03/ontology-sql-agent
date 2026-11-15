# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""move settings to public, drop the frontend schema

Revision ID: c5e0a3b7d912
Revises: b81f4d0c9e27
Create Date: 2026-11-15 00:00:00

``frontend`` was the upstream Next.js app's Prisma schema. With the UI now a
plain React app talking to this API, its two remaining tables become ordinary
tables of this schema: ``frontend.acronyms`` -> ``acronym`` and
``frontend.configurations`` -> ``configuration``. Rows are carried over, except
the configuration keys nothing reads any more.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c5e0a3b7d912"
down_revision: str | Sequence[str] | None = "b81f4d0c9e27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Written by the old app for features since removed.
_DEAD_KEYS = ("pii_detection_enabled", "semantic_compilation_enabled")


def upgrade() -> None:
    op.create_table(
        "acronym",
        sa.Column(
            "id",
            sa.Text(),
            server_default=sa.text("(gen_random_uuid())::text"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "description", sa.Text(), server_default=sa.text("''"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acronym")),
        sa.UniqueConstraint("name", name=op.f("uq_acronym_name")),
    )
    op.create_table(
        "configuration",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_configuration")),
    )
    dead = ", ".join(f"'{key}'" for key in _DEAD_KEYS)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF to_regclass('frontend.acronyms') IS NOT NULL THEN
                INSERT INTO acronym (id, name, description, created_at, updated_at)
                SELECT id::text, name, description, created_at, updated_at
                FROM frontend.acronyms;
            END IF;
            IF to_regclass('frontend.configurations') IS NOT NULL THEN
                INSERT INTO configuration (key, value, updated_at)
                SELECT key, value, updated_at FROM frontend.configurations
                WHERE key NOT IN ({dead});
            END IF;
        END
        $$;
        """
    )
    op.execute("DROP SCHEMA IF EXISTS frontend CASCADE")


def downgrade() -> None:
    """Put both tables back in ``frontend``, in the shape Prisma gave them."""
    op.execute(
        """
        CREATE SCHEMA frontend;
        CREATE TABLE frontend.configurations (
            key        text PRIMARY KEY,
            value      text NOT NULL,
            updated_at timestamptz NOT NULL
        );
        CREATE TABLE frontend.acronyms (
            id          uuid PRIMARY KEY,
            name        text NOT NULL,
            description text NOT NULL DEFAULT '',
            created_at  timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at  timestamptz NOT NULL
        );
        CREATE UNIQUE INDEX acronyms_name_key ON frontend.acronyms (name);
        INSERT INTO frontend.configurations SELECT key, value, updated_at
            FROM configuration;
        INSERT INTO frontend.acronyms
            SELECT id::uuid, name, description, created_at, updated_at FROM acronym;
        """
    )
    op.drop_table("configuration")
    op.drop_table("acronym")
