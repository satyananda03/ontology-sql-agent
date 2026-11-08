# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""On-demand data ingestion, triggered by the review UI's "Ingest ulang" button.

Runs :func:`run_ingest` for the source database. The connector is reloaded on
every pass so a changed ``CONNECTION_STRINGS`` is picked up. A pass ends by
replaying the tagging rules, so columns ingested now are labelled without
waiting for a compilation — see ``auto_ontology.ingestion_service.rules``.
"""

from __future__ import annotations

import asyncio
import logging
import time

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

    async def _run_once(self) -> None:
        # Reload connectors each pass so newly added connections are picked up
        # without a restart. get_connectors caches, so invalidate first; the
        # returned connectors carry each connection's schema allowlist and are
        # owned by the cache (run_ingest must not close them).
        invalidate_connectors_cache()
        connectors = get_connectors()
        if not connectors:
            logger.info(
                "ingest: no connection configured. Set CONNECTION_STRINGS in your .env."
            )
            return

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
