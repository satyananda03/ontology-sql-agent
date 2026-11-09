# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Jobs run only when triggered, and jobs sharing a lock never overlap."""

import asyncio

from auto_ontology.ingestion_service.scheduler import OnDemandScheduler


class _Job(OnDemandScheduler):
    def __init__(self, name: str, log: list[str], lock: asyncio.Lock | None = None):
        super().__init__(lock)
        self.name = name
        self._log = log

    async def _run_once(self) -> None:
        self._log.append(f"{self.name} start")
        await asyncio.sleep(0.01)
        self._log.append(f"{self.name} end")


def test_nothing_runs_until_triggered() -> None:
    async def scenario() -> tuple[list[str], list[str]]:
        log: list[str] = []
        job = _Job("ingest", log)
        job.start()
        await asyncio.sleep(0.05)
        before = list(log)
        job.trigger()
        await asyncio.sleep(0.05)
        await job.stop()
        return before, log

    before, after = asyncio.run(scenario())

    assert before == []
    assert after == ["ingest start", "ingest end"]


def test_jobs_sharing_a_lock_never_overlap() -> None:
    async def scenario() -> list[str]:
        log: list[str] = []
        lock = asyncio.Lock()
        jobs = [_Job("ingest", log, lock), _Job("semantic", log, lock)]
        for job in jobs:
            job.start()
        for job in jobs:
            job.trigger()
        await asyncio.sleep(0.1)
        for job in jobs:
            await job.stop()
        return log

    log = asyncio.run(scenario())

    assert sorted(log) == sorted(
        ["ingest start", "ingest end", "semantic start", "semantic end"]
    )
    first, second = log[:2], log[2:]
    assert first[0].split()[0] == first[1].split()[0]
    assert second[0].split()[0] == second[1].split()[0]
