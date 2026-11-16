# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""rename acronym to glossary

Revision ID: e7a1c4f9b2d6
Revises: d2b6f8e1a4c3
Create Date: 2026-11-15 00:00:00

The page, the API and the code all call it the Glossary; the table follows.
Its constraints are renamed with it -- ``pk_acronym``, ``uq_acronym_name`` and,
on Postgres 18+, the named ``acronym_*_not_null`` ones -- so the names stay
what the naming convention would give a table created as ``glossary``.
Postgres renames a constraint's backing index along with it.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7a1c4f9b2d6"
down_revision: str | Sequence[str] | None = "d2b6f8e1a4c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rename(old: str, new: str) -> None:
    op.rename_table(old, new)
    op.execute(
        f"""
        DO $$
        DECLARE con record;
        BEGIN
            FOR con IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = '{new}'::regclass AND conname LIKE '%{old}%'
            LOOP
                EXECUTE format(
                    'ALTER TABLE {new} RENAME CONSTRAINT %I TO %I',
                    con.conname, replace(con.conname, '{old}', '{new}')
                );
            END LOOP;
        END
        $$;
        """
    )


def upgrade() -> None:
    _rename("acronym", "glossary")


def downgrade() -> None:
    _rename("glossary", "acronym")
