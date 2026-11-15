"""The Glossary (``acronym``) and instance settings (``configuration``).

How a configuration value is parsed, and what an unreadable one falls back to,
is ``auto_ontology.infra.feature_flags``'s business; this module only stores
the strings.
"""

from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from auto_ontology.dal import schema as s
from auto_ontology.dal.session import store

_ACRONYM = (
    s.acronym.c.id,
    s.acronym.c.name,
    s.acronym.c.description,
    s.acronym.c.created_at,
    s.acronym.c.updated_at,
)


def _taken(name: str) -> ValueError:
    return ValueError(f"Acronym {name!r} already exists.")


def fetch_acronyms() -> list[dict[str, str]]:
    """The Glossary as ``[{"name", "description"}]``, for the SQL agent's prompt."""
    return store().query_read(
        select(s.acronym.c.name, s.acronym.c.description).order_by(
            s.acronym.c.created_at
        )
    )


def list_acronyms() -> list[dict[str, Any]]:
    """Every acronym with its id and timestamps, by name."""
    return store().query_read(select(*_ACRONYM).order_by(func.lower(s.acronym.c.name)))


def create_acronym(name: str, description: str) -> dict[str, Any]:
    """Insert one acronym. Raises ``ValueError`` when the name is taken."""
    try:
        rows = store().query_write(
            insert(s.acronym)
            .values(name=name, description=description)
            .returning(*_ACRONYM)
        )
    except IntegrityError as exc:
        raise _taken(name) from exc
    return rows[0]


def update_acronym(
    acronym_id: str, *, name: str | None, description: str | None
) -> dict[str, Any] | None:
    """Change the given fields; ``None`` when no acronym has *acronym_id*.

    Raises ``ValueError`` when *name* is taken by another acronym.
    """
    values = {
        key: value
        for key, value in (("name", name), ("description", description))
        if value is not None
    }
    statement = update(s.acronym).where(s.acronym.c.id == acronym_id)
    try:
        rows = store().query_write(
            # An empty patch still has to answer with the row (and bump
            # updated_at), so it writes the name back onto itself.
            statement.values(**(values or {"name": s.acronym.c.name})).returning(
                *_ACRONYM
            )
        )
    except IntegrityError as exc:
        raise _taken(name or "") from exc
    return rows[0] if rows else None


def delete_acronym(acronym_id: str) -> bool:
    """Remove one acronym; ``False`` when it did not exist."""
    return bool(
        store().query_write(
            delete(s.acronym)
            .where(s.acronym.c.id == acronym_id)
            .returning(s.acronym.c.id)
        )
    )


def read_configuration(key: str) -> str | None:
    """The stored value for *key*, or ``None`` when nothing is stored."""
    rows = store().query_read(
        select(s.configuration.c.value).where(s.configuration.c.key == key)
    )
    return rows[0]["value"] if rows else None


def write_configuration(key: str, value: str) -> None:
    """Store *value* under *key*, replacing any old value."""
    statement = insert(s.configuration).values(key=key, value=value)
    store().query_write(
        statement.on_conflict_do_update(
            index_elements=[s.configuration.c.key],
            set_={"value": statement.excluded.value, "updated_at": func.now()},
        )
    )
