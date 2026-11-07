# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Backend SQL against Prisma-owned tables must name their schema.

This is a source-level scan rather than a database test, because the failure it
guards against does not need a database to happen and does not reliably show up
in one.

The history: these tables lived in `public` and every backend statement reached
them unqualified, which worked only because the role's `search_path` resolved
there. Moving them to `frontend` broke all fifteen statements at once — and
mostly broke them *silently*, since the call sites catch their own exceptions.
`is_semantic_compilation_enabled()` began returning False (so semantic
compilation just stopped running), and acronyms and custom prompts began
returning empty. Nothing crashed. The only evidence was one ERROR line in the
ingestion log.

A schema-qualified name cannot fail that way, so the rule is simply that the
qualification is always present — enforced here rather than left to review.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from auto_ontology.infra.postgres import FRONTEND_SCHEMA

#: Tables the review UI owns in the `frontend` schema (Prisma upstream).
PRISMA_TABLES = (
    "conversations",
    "messages",
    "prompts",
    "configurations",
    "acronyms",
    "conversation_analytics",
    # Better Auth accounts. The role lookup reads this; an unqualified name
    # fails closed and reports every caller as not an admin.
    "user",
)

_AUTO_ONTOLOGY_ROOT = Path(__file__).resolve().parents[2]

#: `FROM foo`, `INTO foo`, `UPDATE foo`, `JOIN foo` — the places a bare table
#: name can appear. A qualified reference has a `.` before the name and so does
#: not match.
# Optional quotes: Better Auth maps the account model to `"user"`, and the
# SQL quotes that name. A qualified reference still has a `.` before it.
_UNQUALIFIED = re.compile(
    r'\b(?:FROM|INTO|UPDATE|JOIN)\s+"?(' + "|".join(PRISMA_TABLES) + r')"?\b'
)


def _python_sources() -> list[Path]:
    return [
        path
        for path in _AUTO_ONTOLOGY_ROOT.rglob("*.py")
        if "tests" not in path.parts and "__pycache__" not in path.parts
    ]


def test_no_unqualified_prisma_table_references() -> None:
    offenders: list[str] = []
    for path in _python_sources():
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            match = _UNQUALIFIED.search(line)
            if match:
                offenders.append(
                    f"{path.relative_to(_AUTO_ONTOLOGY_ROOT)}:{number}: "
                    f"unqualified {match.group(1)!r} — "
                    f"use {{FRONTEND_SCHEMA}}.{match.group(1)}"
                )

    assert not offenders, (
        "Backend SQL references a Prisma-owned table without its schema. These "
        "resolve via search_path and will silently read nothing once it "
        "changes:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "module",
    [
        "auto_ontology/server/settings_dal.py",
        # The `configurations` reader that ingestion_service/config.py delegates
        # to; it owns the SQL, so it is the file that has to qualify.
        "auto_ontology/infra/feature_flags.py",
    ],
)
def test_known_readers_qualify_and_interpolate(module: str) -> None:
    """The known readers must actually interpolate the constant.

    Guards the specific way this can regress silently: writing
    ``"... FROM {FRONTEND_SCHEMA}.acronyms"`` without the ``f`` prefix is a
    perfectly valid string that Postgres rejects at runtime, inside a
    ``try/except`` that swallows it.
    """
    source = (
        _AUTO_ONTOLOGY_ROOT / Path(module).relative_to("auto_ontology")
    ).read_text()
    assert f"{FRONTEND_SCHEMA}." not in source.replace("FRONTEND_SCHEMA", ""), (
        f"{module} hard-codes the schema name; import FRONTEND_SCHEMA instead"
    )
    for line in source.splitlines():
        if "{FRONTEND_SCHEMA}" in line and "#:" not in line:
            # The literal containing it has to be an f-string. Checked per file
            # rather than per line because triple-quoted blocks span lines.
            assert 'f"' in source or "f'" in source, (
                f"{module}: {{FRONTEND_SCHEMA}} appears in a non-f-string"
            )
            break
