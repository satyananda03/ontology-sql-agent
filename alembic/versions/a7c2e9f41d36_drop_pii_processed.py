# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""drop pii_processed

Revision ID: a7c2e9f41d36
Revises: 5d2e8b7c41af
Create Date: 2026-11-14 00:00:00

Built-in PII detection and its propagation onto attributes are removed; PII
classification moves to a separate pipeline. Nothing reads these flags any
more. Existing ``PII`` tags and their labels are left in place as ordinary
tags.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a7c2e9f41d36"
down_revision: str | Sequence[str] | None = "5d2e8b7c41af"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("catalog_column", "column_attribute", "sql_attribute")


def upgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "pii_processed")


def downgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                "pii_processed",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
        )
