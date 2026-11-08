# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""On-demand job runner shared by the ingestion service's background jobs.

A job runs only when :meth:`OnDemandScheduler.trigger` is called — from the
review UI's buttons, through the API. There is no startup run and no timer.

Ingest writes the catalog that semantic compilation reads, so the two must
never run at once. The lifespan hands both schedulers the same lock: a job
triggered while the other is running waits for it, then runs.

Subclasses implement :meth:`_run_once`.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class OnDemandScheduler:
    """Runs a job on its own task each time it is triggered, one run at a time."""

    #: Short label used as a log prefix; overridden by subclasses.
    name = "scheduler"

    def __init__(self, lock: asyncio.Lock | None = None) -> None:
        self._lock = lock or asyncio.Lock()
        self._stop = asyncio.Event()
        self._trigger = asyncio.Event()
        self._abort = asyncio.Event()
        self._running = False
        self._paused = False
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Launch the background loop, which then waits for a trigger."""
        if self._task is None:
            self._task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        """Signal the loop to exit and wait for it to unwind."""
        self._stop.set()
        if self._task is not None:
            await self._task

    def trigger(self) -> None:
        """Request a run without blocking the caller.

        Triggers that arrive while a run is in flight collapse into one more run
        after it, so clicking twice never queues two passes.
        """
        self._trigger.set()

    def abort(self) -> None:
        """Ask the in-flight pass to stop at its next safe point.

        A queued trigger is dropped as well, so aborting cannot be followed
        immediately by another pass.
        """
        self._abort.set()
        self._trigger.clear()

    def pause(self) -> None:
        """Suppress passes until :meth:`resume`.

        ``abort`` alone is not enough to hold the scheduler off: it stops the
        *current* pass, but ``_run_pass`` clears the abort flag before each new
        one. A caller that has to mutate the data a pass reads — the semantic
        reset deleting the layer — would otherwise race a trigger that starts a
        pass against the half-changed state.
        """
        self._paused = True

    def resume(self) -> None:
        """Allow passes again after :meth:`pause`."""
        self._paused = False

    @property
    def paused(self) -> bool:
        """Whether passes are currently suppressed."""
        return self._paused

    @property
    def aborting(self) -> bool:
        """Whether the pass currently running was asked to stop."""
        return self._abort.is_set()

    @property
    def running(self) -> bool:
        """Whether a pass is executing right now, as opposed to idle or waiting."""
        return self._running

    async def _run_once(self) -> None:
        """Perform one pass of the job. Implemented by subclasses."""
        raise NotImplementedError

    async def _run_pass(self) -> None:
        """Run one pass with a fresh abort flag, surviving unhandled errors.

        A paused scheduler skips the pass entirely rather than aborting it part
        way: the point of the pause is that the data a pass reads is being
        rewritten, so starting one at all is what has to be prevented.
        """
        if self._paused:
            logger.info("%s: paused; skipping this pass", self.name)
            return
        if self._lock.locked():
            logger.info("%s: waiting for the other job to finish", self.name)
        async with self._lock:
            self._abort.clear()
            self._running = True
            try:
                await self._run_once()
            except Exception:
                logger.exception("%s: unhandled error", self.name)
            finally:
                self._running = False

    async def _wait_for_trigger(self) -> None:
        """Sleep until a trigger or a stop request arrives."""
        waiters = [
            asyncio.create_task(self._stop.wait()),
            asyncio.create_task(self._trigger.wait()),
        ]
        try:
            await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for waiter in waiters:
                waiter.cancel()

    async def _run_forever(self) -> None:
        while not self._stop.is_set():
            await self._wait_for_trigger()
            if self._stop.is_set():
                break
            self._trigger.clear()
            await self._run_pass()
