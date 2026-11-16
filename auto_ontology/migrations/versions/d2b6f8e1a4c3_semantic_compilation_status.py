# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""replace semantic_compilation_history with a single status row

Revision ID: d2b6f8e1a4c3
Revises: c5e0a3b7d912
Create Date: 2026-11-15 00:00:00

The Settings page only ever showed the last success and, when more recent, the
last failure. A row per pass kept growing for nothing, so the history becomes
one overwritten row holding just those two, seeded from the history it
replaces.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d2b6f8e1a4c3"
down_revision: str | Sequence[str] | None = "c5e0a3b7d912"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_compilation_status",
        sa.Column("id", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "id", name=op.f("ck_semantic_compilation_status_single_row")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semantic_compilation_status")),
    )
    op.execute(
        """
        WITH last AS (
            SELECT
                MAX(finished_at) FILTER (WHERE status = 'succeeded') AS success,
                MAX(finished_at) FILTER (WHERE status = 'failed') AS failure
            FROM semantic_compilation_history
        )
        INSERT INTO semantic_compilation_status (last_success_at, last_failure_at)
        SELECT success,
               CASE WHEN failure > COALESCE(success, '-infinity') THEN failure END
        FROM last
        WHERE success IS NOT NULL OR failure IS NOT NULL
        """
    )
    op.drop_table("semantic_compilation_history")


def downgrade() -> None:
    """Recreate the history table, holding the status row's two timestamps."""
    op.create_table(
        "semantic_compilation_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IS NULL OR status IN ('succeeded', 'failed')",
            name=op.f("ck_semantic_compilation_history_status_value"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semantic_compilation_history")),
    )
    op.execute(
        """
        INSERT INTO semantic_compilation_history (started_at, finished_at, status)
        SELECT last_success_at, last_success_at, 'succeeded'
        FROM semantic_compilation_status WHERE last_success_at IS NOT NULL
        UNION ALL
        SELECT last_failure_at, last_failure_at, 'failed'
        FROM semantic_compilation_status WHERE last_failure_at IS NOT NULL
        """
    )
    op.drop_table("semantic_compilation_status")
