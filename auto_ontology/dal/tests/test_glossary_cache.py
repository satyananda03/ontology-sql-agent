"""The glossary is read once and re-read after every write."""

import os
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from auto_ontology.dal import settings  # noqa: E402
from auto_ontology.dal.session import store  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def require_schema():
    if not os.environ.get("POSTGRES_USER"):
        pytest.skip("POSTGRES_* not set")
    try:
        store().query_read("SELECT 1 FROM glossary LIMIT 1")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"auto_ontology schema unavailable (alembic upgrade head): {exc}")


def _names() -> list[str]:
    return [entry["name"] for entry in settings.fetch_glossary()]


def test_every_write_is_seen_by_the_next_read() -> None:
    name = f"cache-probe-{uuid.uuid4().hex[:8]}"
    _names()  # fill the cache before writing
    entry = settings.create_glossary_entry(name, "first")
    try:
        assert name in _names()
        settings.update_glossary_entry(entry["id"], name=None, description="second")
        assert {"name": name, "description": "second"} in settings.fetch_glossary()
    finally:
        settings.delete_glossary_entry(entry["id"])
    assert name not in _names()


def test_a_caller_cannot_change_the_cached_glossary() -> None:
    entries = settings.fetch_glossary()
    entries.append({"name": "injected", "description": ""})
    for entry in entries:
        entry["name"] = "changed"
    assert "injected" not in _names() and "changed" not in _names()
