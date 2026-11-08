# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""The committed OpenAPI specs match the apps, so API changes show up in review."""

from __future__ import annotations

import json

import pytest

from sql_agent import openapi as generator


@pytest.mark.parametrize("name", ["backend.json", "ingestion.json"])
def test_committed_spec_is_up_to_date(name: str) -> None:
    committed = (generator.OUTPUT_DIR / name).read_text()
    generated = json.dumps(generator._specs()[name], indent=2, sort_keys=True) + "\n"
    assert committed == generated, f"docs/openapi/{name} is stale; run: make openapi"
