"""How many LLM requests may be in flight at once.

Unbounded by default. Fan-out that multiplies -- semantic compilation runs
tables in parallel and fans out again inside each -- asks for a bound with
:func:`limit_inflight`; ``llm_invoke`` takes :func:`inflight_guard` around every
request.
"""

import contextlib
import os
import threading
from typing import Iterator

# Concurrent LLM requests are unbounded here by default. A process-wide cap used
# to live at this call site, defaulting to 6, to stop semantic compilation's
# nested fan-out (tables x terms) from saturating the endpoint's per-worker
# request cap and drawing HTTP 503s.
#
# The cost was paid by every caller. Callers that already bound their own
# concurrency -- a server handling N requests, an eval running N questions --
# gained nothing and hit a second, lower ceiling they could not see: measured on
# a 60-question benchmark at 12 workers, lifting this cap cut wall clock 25%
# with no change in error rate, because threads sat ~3s per node waiting on the
# semaphore before reaching the network.
#
# Fan-out that needs a bound now asks for one with `limit_inflight`, which
# applies it for the duration of a block. See `run_semantic_compilation`.
LLM_MAX_INFLIGHT = int(os.environ.get("LLM_MAX_INFLIGHT", "0"))

# The process-wide default, from the environment. None means unbounded. This is
# what the guard falls back to whenever no `limit_inflight` block is active.
_ENV_INFLIGHT: threading.BoundedSemaphore | None = (
    threading.BoundedSemaphore(LLM_MAX_INFLIGHT) if LLM_MAX_INFLIGHT > 0 else None
)

# Every `limit_inflight` block currently open, as (max_inflight, semaphore).
# Tracking the whole set rather than a save/restore of one global is what makes
# overlapping blocks safe: two blocks that overlap without nesting exit in the
# opposite order to a stack, and a save/restore would then have each one put
# back the value *it* captured -- dropping the bound of a block still running,
# and leaving a stale bound installed forever once both had exited.
_ACTIVE: list[tuple[int, threading.BoundedSemaphore]] = []
_ACTIVE_LOCK = threading.Lock()

# The bound in force. Rebound only under _ACTIVE_LOCK by `_refresh_inflight`,
# but read on the hot path without it: the read is a single attribute lookup,
# and a caller that reads a semaphore just as its block ends simply waits on a
# still-valid bound for that one invoke. That is a bounded staleness, not a
# correctness problem, and it keeps the lock off every LLM call.
_INFLIGHT: threading.BoundedSemaphore | None = _ENV_INFLIGHT


def _refresh_inflight() -> None:
    """Recompute the bound in force. Caller must hold ``_ACTIVE_LOCK``."""
    global _INFLIGHT
    # The most restrictive active block wins. Only one semaphore is ever
    # acquired, so nested blocks cannot deadlock against each other.
    _INFLIGHT = (
        min(_ACTIVE, key=lambda entry: entry[0])[1] if _ACTIVE else _ENV_INFLIGHT
    )


@contextlib.contextmanager
def limit_inflight(max_inflight: int) -> Iterator[None]:
    """Bound concurrent LLM invokes to *max_inflight* for the duration of the block.

    For call paths whose own parallelism multiplies -- semantic compilation runs
    tables in parallel and fans out again within each -- where the resulting
    request rate can exceed what the endpoint will serve and come back as 503.

    The bound is process-wide, because the fan-out it exists to limit spans
    worker threads the caller does not own. While several blocks overlap the
    most restrictive one applies, in any nesting or interleaving; once the last
    one exits the process returns to ``LLM_MAX_INFLIGHT``.

    A value of 0 or less registers nothing and leaves any other block's bound
    alone -- "I need no bound" must not mean "remove someone else's".
    """
    if max_inflight <= 0:
        yield
        return
    entry = (max_inflight, threading.BoundedSemaphore(max_inflight))
    with _ACTIVE_LOCK:
        _ACTIVE.append(entry)
        _refresh_inflight()
    try:
        yield
    finally:
        with _ACTIVE_LOCK:
            # Removal is by identity of the semaphore, so concurrent blocks
            # asking for the same size still remove their own entry.
            for index, candidate in enumerate(_ACTIVE):
                if candidate[1] is entry[1]:
                    del _ACTIVE[index]
                    break
            _refresh_inflight()


def inflight_guard() -> "contextlib.AbstractContextManager[object]":
    """The active concurrency bound, or a no-op when unbounded."""
    semaphore = _INFLIGHT
    return semaphore if semaphore is not None else contextlib.nullcontext()
