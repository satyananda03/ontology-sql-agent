# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import pytest

from sql_agent.core.config import Settings


def test_settings_read_the_environment_and_blank_means_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SQL_AGENT_RERANK_POOL", "25")
    monkeypatch.setenv("SQL_AGENT_MAX_ROWS", "")
    monkeypatch.setenv("LLM_BINDING_HOST", "https://gateway/v1")
    loaded = Settings(_env_file=None)
    assert loaded.sql_agent_rerank_pool == 25
    assert loaded.sql_agent_max_rows == 200
    assert loaded.llm_binding_host == "https://gateway/v1"
