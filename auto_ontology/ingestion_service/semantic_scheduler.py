"""On-demand semantic compilation, triggered by the review UI's buttons.

Runs :func:`run_semantic_compilation` for the source database when "Jalankan
kompilasi" is clicked, and after "Regenerate ontologi" has deleted the layer
(see ``auto_ontology.ingestion_service.ingest.reset_semantic_layer_and_recompile``).

A completed pass also re-applies every tagging rule — see
:meth:`SemanticScheduler._reapply_rules`. That is the one piece of work here
which is not compilation, and it lives here because it is the point at which
both the catalog and the semantic layer a rule labels are current.
``auto_ontology.ingestion_service.rules`` holds the shared half.

Compilation reads the catalog that :class:`DataScheduler` writes. The two share
a lock (see ``auto_ontology.ingestion_service.scheduler``), so a compile never
reads a catalog that an ingest is halfway through rewriting.
"""

from __future__ import annotations

import asyncio
import logging
import time

from auto_ontology.ingestion_service.connections import resolve_database_names
from auto_ontology.ingestion_service.history import (
    RUN_FAILED,
    RUN_SUCCEEDED,
    record_run_finish,
    record_run_start,
)
from auto_ontology.ingestion_service.pii import run_pii_propagation_in_thread
from auto_ontology.ingestion_service.rules import replay_rules_in_thread
from auto_ontology.ingestion_service.scheduler import OnDemandScheduler
from auto_ontology.semantic.cancellation import clear_cancel, request_cancel
from auto_ontology.semantic.compile import run_semantic_compilation

logger = logging.getLogger(__name__)

# Appended when a pass compiles nothing. The count is tables that *needed*
# compiling (``compile_semantic_layer`` works from the tables with no Term yet),
# so zero is a legitimate outcome — while the elapsed time can still be minutes,
# because the FK, SqlAttribute and bridge-table stages run afterwards
# regardless. Without this, "0 table(s) ... in 620.7s" reads as a stall or a
# silently failed run.
#
# Deliberately does not name a cause. Zero establishes only that nothing needed
# compiling; whether that is a settled catalog, one whose tables are all
# excluded by a connection's table filter, or an empty catalog, this cannot
# tell — and claiming the first would hide the other two.
_NOTHING_TO_COMPILE = (
    " (no table needed compiling; the elapsed time is the FK, SqlAttribute "
    "and bridge-table stages, which run on every pass)"
)


class SemanticScheduler(OnDemandScheduler):
    """Runs semantic compilation each time it is triggered."""

    name = "semantic"

    def abort(self) -> None:
        """Stop the in-flight pass at the next *table*, not the next database.

        The base class only sets its own flag, which the pass checks between
        databases — so an abort could take as long as the slowest single
        database (312s observed here). Cancelling the semantic work as well
        makes queued tables no-ops and skips the post-compile stages, which
        brings a stop down to roughly one table.
        """
        request_cancel()
        super().abort()

    async def _reapply_rules(self) -> None:
        """Re-label the catalog through every stored rule, after compiling it.

        A rule is a saved search plus the tags to apply to what it matches, and
        it goes on matching as the catalog grows -- a column ingested last
        night is not labelled by anything else while compilation is on. See
        ``auto_ontology.ingestion_service.rules`` for the other two callers and
        why the three disagree about when to run.

        Here rather than only in the data scheduler because a rule labels
        *both* layers: Tables and Columns, which ingest writes, and Terms and
        their attributes, which this pass writes. Running it at the end of this
        pass is the only point at which both are current -- and no ingest runs
        alongside it (see the module docstring), so the catalog beneath the
        semantic layer is current too.

        Only reached when the pass ran to completion. A stop returns before
        this, which is the right way round: it cuts the pass short at a
        database boundary, so the semantic layer is half
        written, and labels applied against half of it would be taken back
        again on the next pass.
        """
        await replay_rules_in_thread(self.name)

    async def _run_once(self) -> None:
        # A cancellation belongs to the pass that was running when it was
        # requested; leaving it set would abort this one before it starts.
        clear_cancel()

        databases = resolve_database_names()
        if not databases:
            logger.info(
                "semantic: no connection configured; nothing to compile. "
                "Set CONNECTION_STRINGS in your .env."
            )
            return

        logger.info("semantic: starting (%d database(s))", len(databases))
        started = time.monotonic()
        succeeded = failed = 0
        total_tables = 0
        run_id = record_run_start()
        # Starts optimistic; only ever downgraded, never upgraded back — a
        # stop after a real failure must still be recorded as failed,
        # not left NULL, so a genuine bug isn't masked by the fact that the run
        # was also stopped. An explicit stop downgrades to None instead,
        # which record_run_finish treats as a no-op — see history.py on why an
        # aborted run leaves the row NULL rather than storing an outcome.
        outcome: str | None = RUN_SUCCEEDED
        try:
            for index, database_name in enumerate(databases):
                # Checked per database rather than once per pass, so a stop
                # request ends the run at the next boundary instead
                # of after every database. The database in flight is not
                # abandoned — Python cannot kill its worker threads — but
                # ``abort`` also cancels the semantic work, so it stops at its
                # next table and skips the post-compile stages rather than
                # running to completion.
                if self.aborting:
                    logger.info(
                        "semantic: stopped on request; %d database(s) not compiled",
                        len(databases) - index,
                    )
                    if outcome != RUN_FAILED:
                        outcome = None
                    return

                try:
                    database_started = time.monotonic()
                    tables_processed = await asyncio.to_thread(
                        run_semantic_compilation, database_name
                    )
                    succeeded += 1
                    total_tables += tables_processed
                    # "compiled", not "processed": the count is tables that
                    # *needed* compiling. The pass summary carries the why when
                    # it is zero; repeating it per database would be five copies
                    # of the same sentence.
                    logger.info(
                        "Finished semantic compilation successfully for database %s: "
                        "%d table(s) compiled in %.1fs",
                        database_name,
                        tables_processed,
                        time.monotonic() - database_started,
                    )
                except Exception:
                    failed += 1
                    outcome = RUN_FAILED
                    logger.exception("semantic: failed for database %s", database_name)

            # The boundary checks above catch a stop before the next
            # database. There is no next boundary after the final database, so
            # re-check here before operating on a pass that was cancelled
            # while that database was in flight.
            if self.aborting:
                logger.info(
                    "semantic: stopped on request; skipping post-compilation work"
                )
                if outcome != RUN_FAILED:
                    outcome = None
                return

            # Before the rules, so a rule matching on the PII tag sees the
            # attributes compilation just created already labelled.
            await run_pii_propagation_in_thread(self.name)
            await self._reapply_rules()
        finally:
            # A no-op when outcome is None (stop) — see
            # record_run_finish's docstring on why that leaves the row NULL
            # rather than recording an "aborted" outcome.
            record_run_finish(run_id, outcome)
            # As in the data scheduler: per-database failures are caught so the
            # rest still compile, so the closing line has to carry the tally to
            # mean anything.
            elapsed = time.monotonic() - started
            if outcome is None:
                # The early return above already logged *why* it stopped; this
                # says how far it got before it did.
                logger.info(
                    "semantic: stopped — %d of %d database(s) compiled, "
                    "%d table(s) processed in %.1fs",
                    succeeded,
                    len(databases),
                    total_tables,
                    elapsed,
                )
            elif failed:
                logger.warning(
                    "semantic: finished with errors — %d of %d database(s) succeeded, "
                    "%d failed, %d table(s) processed in %.1fs",
                    succeeded,
                    len(databases),
                    failed,
                    total_tables,
                    elapsed,
                )
            else:
                logger.info(
                    "semantic: finished successfully — %d database(s), "
                    "%d table(s) compiled in %.1fs%s",
                    succeeded,
                    total_tables,
                    elapsed,
                    "" if total_tables else _NOTHING_TO_COMPILE,
                )
