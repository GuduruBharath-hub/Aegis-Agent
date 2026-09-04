from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from types import TracebackType

from backend.core.models import Event
from backend.storage.repositories import EventRepo


class EventSubscription(AsyncIterator[Event]):
    def __init__(
        self,
        bus: EventBus,
        job_id: str,
        backlog: list[Event],
        queue: asyncio.Queue[Event],
    ) -> None:
        self._bus = bus
        self._job_id = job_id
        self._backlog = deque(backlog)
        self._queue = queue
        self._closed = False

    def __aiter__(self) -> EventSubscription:
        return self

    async def __anext__(self) -> Event:
        if self._closed:
            raise StopAsyncIteration
        if self._backlog:
            return self._backlog.popleft()
        return await self._queue.get()

    async def __aenter__(self) -> EventSubscription:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._bus._unsubscribe(self._job_id, self._queue)


class EventBus:
    """Durable per-job event fan-out for the single orchestrator process."""

    def __init__(self, repository: EventRepo) -> None:
        self._repository = repository
        self._subscribers: dict[str, set[asyncio.Queue[Event]]] = {}
        self._boundary = asyncio.Lock()

    async def publish(self, event: Event) -> Event:
        async with self._boundary:
            # Holding this boundary across both operations closes the race where
            # an event could appear in replay and then be published live again.
            persisted = self._repository.create(event)
            for queue in tuple(self._subscribers.get(event.job_id, ())):
                queue.put_nowait(persisted)
            return persisted

    async def subscribe(
        self,
        job_id: str,
        *,
        after_seq: int = 0,
    ) -> EventSubscription:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        async with self._boundary:
            backlog = self._repository.list_for_job(job_id, since_seq=after_seq)
            self._subscribers.setdefault(job_id, set()).add(queue)
        return EventSubscription(self, job_id, backlog, queue)

    async def _unsubscribe(
        self,
        job_id: str,
        queue: asyncio.Queue[Event],
    ) -> None:
        async with self._boundary:
            subscribers = self._subscribers.get(job_id)
            if subscribers is None:
                return
            subscribers.discard(queue)
            if not subscribers:
                del self._subscribers[job_id]
