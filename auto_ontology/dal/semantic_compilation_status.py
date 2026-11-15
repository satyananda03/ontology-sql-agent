"""How the last semantic compilation pass ended, for the Settings page.

One row, overwritten (see ``semantic_compilation_status`` in
:mod:`auto_ontology.dal.schema`). The ingestion scheduler writes it when a pass
reaches a verdict; both services' status endpoints read it back.

Best-effort both ways: a database hiccup must neither fail a compilation pass
nor break a status page, so errors are logged and swallowed here.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from auto_ontology.dal import schema as s
from auto_ontology.dal.session import store

logger = logging.getLogger(__name__)

RUN_SUCCEEDED = "succeeded"
RUN_FAILED = "failed"

_STATUS = s.semantic_compilation_status


def record_outcome(outcome: str) -> None:
    """Store *outcome* for a pass that just finished. A success clears the failure."""
    if outcome == RUN_SUCCEEDED:
        values = {"last_success_at": func.now(), "last_failure_at": None}
    elif outcome == RUN_FAILED:
        values = {"last_failure_at": func.now()}
    else:
        raise ValueError(f"invalid semantic compilation outcome: {outcome!r}")
    statement = insert(_STATUS).values(id=True, **values)
    try:
        store().query_write(
            statement.on_conflict_do_update(index_elements=[_STATUS.c.id], set_=values)
        )
    except Exception:
        logger.exception("Failed to record semantic compilation outcome %s", outcome)


def last_outcomes() -> dict[str, str | None]:
    """``last_success_at`` and ``last_failure_at`` as ISO 8601, or ``None``.

    ``last_failure_at`` is set only while the most recent verdict is a failure.
    """
    try:
        rows = store().query_read(
            select(_STATUS.c.last_success_at, _STATUS.c.last_failure_at)
        )
    except Exception:
        logger.exception("Failed to read semantic compilation status")
        rows = []
    row = rows[0] if rows else {}
    return {
        key: moment.isoformat() if (moment := row.get(key)) else None
        for key in ("last_success_at", "last_failure_at")
    }
