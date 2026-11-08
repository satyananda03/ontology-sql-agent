# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Dump the FastAPI apps' OpenAPI specs to ``docs/openapi/``.

They are committed so API changes show up in review, and so the specs can be
read without a running server, and the dashboard's TypeScript types are
generated from ``backend.json``. ``sql_agent/tests/test_openapi.py`` fails when
they are stale.

Usage (from the repo root)::

    make openapi
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "openapi"


def _specs() -> dict[str, dict[str, Any]]:
    # Imported lazily: building the apps pulls in the retrieval stack, which is
    # slow and noisy at import time.
    from auto_ontology.ingestion_service.__main__ import app as ingestion_app
    from auto_ontology.server.__main__ import create_app

    return {
        "backend.json": create_app().openapi(),
        "ingestion.json": ingestion_app.openapi(),
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, spec in _specs().items():
        target = OUTPUT_DIR / name
        # sort_keys keeps the committed file stable across runs, so the drift
        # test only fires on real changes.
        target.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
        ops = sum(len(methods) for methods in spec["paths"].values())
        print(f"{target.relative_to(REPO_ROOT)}: {len(spec['paths'])} paths, {ops} ops")
    return 0


if __name__ == "__main__":
    sys.exit(main())
