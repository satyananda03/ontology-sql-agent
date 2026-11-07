# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Licensing check: every tracked source file carries an SPDX header."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Files that cannot carry a comment header, are generated, or are third-party
# data. A `<file>.license` sidecar also satisfies the check.
EXEMPT_SUFFIXES = {
    ".json",
    ".sig",
    ".lock",
    ".sql",
    ".csv",
    ".parquet",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".whl",
    ".pdf",
    ".license",
}
EXEMPT_NAMES = {
    "LICENSE",
    "uv.lock",
    ".python-version",
}


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line]


def _needs_header(path: str) -> bool:
    p = Path(path)
    return not (
        p.suffix.lower() in EXEMPT_SUFFIXES
        or p.name in EXEMPT_NAMES
        or (ROOT / f"{path}.license").exists()
    )


def test_every_source_file_has_an_spdx_header() -> None:
    try:
        files = _tracked_files()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    missing = []
    for path in files:
        full = ROOT / path
        if not _needs_header(path) or not full.is_file():
            continue
        head = full.read_bytes()[:2000].decode("utf-8", errors="ignore")
        if "SPDX-License-Identifier" not in head:
            missing.append(path)
    assert not missing, "Add an SPDX header to:\n  " + "\n  ".join(missing)
