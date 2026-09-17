from __future__ import annotations

import asyncio
import uuid

from ..models.events import SentinelEvent


class EventHub:
    """Fan-out for live events to WebSocket clients per session."""

    def __init__(self) -> None:
        self._subs: dict[str, dict[str, asyncio.Queue]] = {}

    def subscriber_count(self, session_id: str) -> int:
        return len(self._subs.get(session_id, {}))

    async def subscribe(self, session_id: str) -> tuple[str, asyncio.Queue[SentinelEvent]]:
        client_id = uuid.uuid4().hex[:8]
        queue: asyncio.Queue[SentinelEvent] = asyncio.Queue(maxsize=200)
        self._subs.setdefault(session_id, {})[client_id] = queue
        return client_id, queue

    def unsubscribe(self, session_id: str, client_id: str) -> None:
        subs = self._subs.get(session_id)
        if not subs:
            return
        subs.pop(client_id, None)
        if not subs:
            self._subs.pop(session_id, None)

    async def publish(self, event: SentinelEvent) -> None:
        subs = self._subs.get(event.session_id)
        if not subs:
            return
        for queue in list(subs.values()):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except Exception:
                    pass