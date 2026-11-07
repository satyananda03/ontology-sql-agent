# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Smoke tests for files that must survive Python wheel packaging."""

from __future__ import annotations

import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Read at runtime, so a wheel without them fails on first use rather than install.
DATA_FILES = (
    "auto_ontology/server/users/access.json",
    "ontology_sql_agent/prompts.yaml",
)


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> ZipFile:
    out = tmp_path_factory.mktemp("wheel")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(out.glob("*.whl"))
    assert len(wheels) == 1
    return ZipFile(wheels[0])


@pytest.mark.parametrize("path", DATA_FILES)
def test_wheel_ships_runtime_data_files(wheel: ZipFile, path: str) -> None:
    assert wheel.read(path) == (ROOT / path).read_bytes()
