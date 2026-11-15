# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import pytest

from sql_agent.core.config import Settings, settings


@pytest.fixture(autouse=True)
def default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests run on the built-in defaults, not on the developer's ``.env``."""
    for name, field in Settings.model_fields.items():
        monkeypatch.setattr(settings, name, field.default)
