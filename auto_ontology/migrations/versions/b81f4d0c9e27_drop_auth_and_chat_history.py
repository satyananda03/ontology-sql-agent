# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""drop auth, ownership and chat history

Revision ID: b81f4d0c9e27
Revises: a7c2e9f41d36
Create Date: 2026-11-15 00:00:00

Authentication will be rebuilt as a separate service, and the playground does
not keep chat history. This drops:

- the Better Auth and chat tables the upstream Next.js app left in
  ``frontend`` (only ``configurations`` and ``acronyms`` stay);
- the user groups and every ``owner_id`` / ``*_by`` column, which held ids
  from those accounts.

The downgrade restores the columns (empty) and the group tables, but not the
``frontend`` tables: their shape belonged to Prisma, and their rows are gone.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b81f4d0c9e27"
down_revision: str | Sequence[str] | None = "a7c2e9f41d36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FRONTEND_TABLES = (
    # chat history
    "conversation_analytics",
    "messages",
    "conversations",
    "prompts",
    # Better Auth
    "oauthAccessToken",
    "oauthRefreshToken",
    "oauthConsent",
    "oauthClientResource",
    "oauthClientAssertion",
    "oauthClient",
    "oauthResource",
    "ssoProvider",
    "apikey",
    "invitations",
    "verification",
    "account",
    "session",
    "user",
)

_OWNED = (
    "catalog_database",
    "catalog_schema",
    "catalog_table",
    "term",
    "sql_attribute",
)
_AUTHORED = ("term", "column_attribute", "sql_attribute", "tag", "rule")


def upgrade() -> None:
    for table in _FRONTEND_TABLES:
        op.execute(f'DROP TABLE IF EXISTS frontend."{table}" CASCADE')
    op.drop_table("user_group__member")
    op.drop_table("user_group")
    for table in _OWNED:
        op.drop_column(table, "owner_id")
    for table in _AUTHORED:
        op.drop_column(table, "created_by")
        op.drop_column(table, "modified_by")
    op.drop_column("tag_target", "tagged_by")


def downgrade() -> None:
    op.add_column("tag_target", sa.Column("tagged_by", sa.Text(), nullable=True))
    for table in _AUTHORED:
        op.add_column(table, sa.Column("modified_by", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("created_by", sa.Text(), nullable=True))
    for table in _OWNED:
        op.add_column(table, sa.Column("owner_id", sa.Text(), nullable=True))
    op.create_table(
        "user_group",
        sa.Column(
            "id",
            sa.Text(),
            server_default=sa.text("(gen_random_uuid())::text"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'viewer')", name=op.f("ck_user_group_role_value")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_group")),
    )
    op.create_index(
        "uq_user_group_name_lower",
        "user_group",
        [sa.literal_column("lower(TRIM(BOTH FROM name))")],
        unique=True,
    )
    op.create_table(
        "user_group__member",
        sa.Column("group_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["user_group.id"],
            name=op.f("fk_user_group__member_group_id_user_group"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "group_id", "user_id", name=op.f("pk_user_group__member")
        ),
    )
    op.create_index("ix_user_group__member_user_id", "user_group__member", ["user_id"])
