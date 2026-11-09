"""Resolve the running application version."""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version as _pkg_version


def get_app_version() -> str:
    """Return the app version for logs and UX.

    Prefers the ``APP_VERSION`` env var, then the installed package version,
    then ``"unknown"``.
    """
    env_version = os.environ.get("APP_VERSION")
    if env_version:
        return env_version
    try:
        return _pkg_version("ontology-sql-agent")
    except PackageNotFoundError:
        return "unknown"
