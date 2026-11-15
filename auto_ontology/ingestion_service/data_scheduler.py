"""On-demand data ingestion, triggered by the review UI's "Ingest ulang" button.

Runs :func:`run_ingest` for the source database. The connector is reloaded on
every pass so a changed ``CLIENT_DATABASE`` is picked up. A pass ends by
replaying the tagging rules, so columns ingested now are labelled without
waiting for a compilation — see ``auto_ontology.ingestion_service.rules``.

How the last pass ended is kept for ``GET /ingest/status``, so the review UI can
report a failed ingest instead of reading every finished pass as a success.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime

from auto_ontology.connectors.registry import (
    get_connectors,
    invalidate_connectors_cache,
)
from auto_ontology.ingestion_service.ingest import run_ingest
from auto_ontology.ingestion_service.rules import replay_rules_in_thread
from auto_ontology.ingestion_service.scheduler import OnDemandScheduler

logger = logging.getLogger(__name__)


class DataScheduler(OnDemandScheduler):
    """Runs data ingestion each time it is triggered."""

    name = "ingest"

    def __init__(self, lock: asyncio.Lock | None = None) -> None:
        super().__init__(lock)
        # ISO 8601, mirroring ``semantic_compilation_status``: a success clears
        # the failure, so ``last_failure_at`` is set only while the latest pass failed.
        # ponytail: in memory, a restart forgets it; persist like semantic_compilation_status if that matters.
        self.last_success_at: str | None = None
        self.last_failure_at: str | None = None

    async def _run_once(self) -> None:
        try:
            succeeded = await self._ingest_all()
        except Exception:
            self._record_outcome(succeeded=False)
            raise
        self._record_outcome(succeeded)

    def _record_outcome(self, succeeded: bool) -> None:
        now = datetime.now(UTC).isoformat()
        if succeeded:
            self.last_success_at, self.last_failure_at = now, None
        else:
            self.last_failure_at = now

    async def _ingest_all(self) -> bool:
        """Ingest every connection; True only when there was one and all succeeded."""
        # Reload connectors each pass so newly added connections are picked up
        # without a restart. get_connectors caches, so invalidate first; the
        # returned connectors carry each connection's schema allowlist and are
        # owned by the cache (run_ingest must not close them).
        invalidate_connectors_cache()
        connectors = get_connectors()
        if not connectors:
            logger.info(
                "ingest: no connection configured. Set CLIENT_DATABASE in your .env."
            )
            return False

        logger.info("ingest: starting (%s connection(s))", len(connectors))
        started = time.monotonic()
        succeeded = failed = 0
        for connector in connectors:
            database_name = getattr(connector, "database_name", "?")
            try:
                await asyncio.to_thread(run_ingest, connector)
                succeeded += 1
            except Exception:
                failed += 1
                logger.exception("ingest: failed for connection %s", database_name)

        await replay_rules_in_thread(self.name)

        # A per-connection failure is caught above so the remaining connections
        # still run, which means reaching this point says nothing on its own.
        # Report the tally rather than a bare "finished": the old line was
        # indistinguishable whether all connections ingested or all of them threw.
        elapsed = time.monotonic() - started
        if failed:
            logger.warning(
                "ingest: finished with errors — %d of %d connection(s) succeeded, "
                "%d failed in %.1fs",
                succeeded,
                len(connectors),
                failed,
                elapsed,
            )
        else:
            logger.info(
                "ingest: finished successfully — %d connection(s) ingested in %.1fs",
                succeeded,
                elapsed,
            )
        return not failed
