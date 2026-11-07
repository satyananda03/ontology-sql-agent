# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""The migration history has exactly one head, so ``upgrade head`` is unambiguous."""

from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[3]
VERSIONS = ROOT / "alembic" / "versions"


def _head_revisions() -> list[str]:
    """Revisions nothing else lists as its ``down_revision``."""
    revisions: dict[str, str | None] = {}
    for path in VERSIONS.glob("*.py"):
        text = path.read_text()
        rev = re.search(r'^revision: str = ["\']([^"\']+)["\']', text, re.M)
        down = re.search(
            r'^down_revision: [^=]+= (?:["\']([^"\']+)["\']|None)', text, re.M
        )
        if rev:
            revisions[rev.group(1)] = down.group(1) if down else None
    parents = {d for d in revisions.values() if d}
    return sorted(set(revisions) - parents)


def test_there_is_exactly_one_head_migration() -> None:
    """Two heads mean `upgrade head` is ambiguous and the gate cannot be pinned."""
    heads = _head_revisions()
    assert len(heads) == 1, f"expected a single head, found {heads}"
