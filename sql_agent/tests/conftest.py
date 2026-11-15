# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import pytest

from sql_agent.core.config import Settings, settings
from sql_agent.modules.retrieval import cache


@pytest.fixture(autouse=True)
def default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests run on the built-in defaults, not on the developer's ``.env``."""
    for name, field in Settings.model_fields.items():
        monkeypatch.setattr(settings, name, field.default)


@pytest.fixture(autouse=True)
def empty_retrieval_cache() -> None:
    """Each test retrieves for itself; a cached result never leaks between tests."""
    cache.clear()
