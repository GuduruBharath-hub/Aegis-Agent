from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.core.event_bus import EventBus
from backend.core.models import Event, Job
from backend.storage.database import Database


def _job(job_id: str) -> Job:
    return Job(
        id=job_id,
        repository="org/repo",
        repository_url="https://github.com/org/repo",
        base_sha="abcdef123456",
        mode="demo",
        max_attempts=3,
    )


def _event(job_id: str, event_type: str) -> Event:
    return Event(
        job_id=job_id,
        type=event_type,
        severity="info",
        title=event_type.replace("_", " ").title(),
    )


def test_mid_run_subscriber_receives_backlog_then_live_without_overlap(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        db = Database(tmp_path / "events.db")
        conn = db.init_db()
        try:
            jobs = db.jobs(conn)
            events = db.events(conn)
            jobs.create(_job("target"))
            jobs.create(_job("other"))
            bus = EventBus(events)

            first = await bus.publish(_event("target", "job_created"))
            unrelated = await bus.publish(_event("other", "job_created"))
            second = await bus.publish(_event("target", "scan_started"))

            subscription = await bus.subscribe("target")
            third = await bus.publish(_event("target", "scan_completed"))
            await bus.publish(_event("other", "scan_started"))
            fourth = await bus.publish(_event("target", "finding_detected"))

            received = [await subscription.__anext__() for _ in range(4)]
            expected = [first, second, third, fourth]

            assert received == expected
            assert [event.seq for event in received] == sorted(
                event.seq for event in received if event.seq is not None
            )
            assert len({event.seq for event in received}) == len(received)
            assert first.seq is not None
            assert unrelated.seq is not None
            assert second.seq is not None
            assert first.seq < unrelated.seq < second.seq
            assert events.list_for_job("target") == expected

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(subscription.__anext__(), timeout=0.01)
            await subscription.aclose()
        finally:
            conn.close()

    asyncio.run(scenario())


def test_last_event_id_replays_only_newer_events(tmp_path: Path) -> None:
    async def scenario() -> None:
        db = Database(tmp_path / "resume.db")
        conn = db.init_db()
        try:
            jobs = db.jobs(conn)
            events = db.events(conn)
            jobs.create(_job("target"))
            bus = EventBus(events)

            first = await bus.publish(_event("target", "job_created"))
            second = await bus.publish(_event("target", "scan_started"))
            assert first.seq is not None

            subscription = await bus.subscribe("target", after_seq=first.seq)
            assert await subscription.__anext__() == second

            third = await bus.publish(_event("target", "scan_completed"))
            assert await subscription.__anext__() == third
            await subscription.aclose()
        finally:
            conn.close()

    asyncio.run(scenario())
