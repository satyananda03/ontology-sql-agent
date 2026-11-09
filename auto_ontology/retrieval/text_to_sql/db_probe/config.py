"""Limits for live DB probing, tunable through the environment."""

from __future__ import annotations

import os


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except (TypeError, ValueError):
        return default


# Total read-only queries allowed per probe run.
DB_PROBE_MAX_CALLS = _int_env("DB_PROBE_MAX_CALLS", 40)
# Max rows returned per probe (also the auto-appended LIMIT).
DB_PROBE_MAX_ROWS = _int_env("DB_PROBE_MAX_ROWS", 50)

__all__ = ["DB_PROBE_MAX_CALLS", "DB_PROBE_MAX_ROWS"]
