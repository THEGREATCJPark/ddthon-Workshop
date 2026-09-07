"""In-process pub/sub broker (C7) — single-process assumption (contract §7/§8).

- One asyncio.Queue per admin SSE connection, grouped by store_id topic.
- publish() is synchronous (uses put_nowait) and MUST be called from the event loop
  thread (U2 routes are `async def`, calling sync services directly).
- No persistence, no replay, no Last-Event-ID (Q9=A). Reconnect just re-subscribes.

Framework-agnostic (stdlib asyncio only) → unit-testable without FastAPI.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Set

from .events import Event


class EventBroker:
    """Broadcasts events to same-store subscribers via per-connection queues."""

    def __init__(self) -> None:
        self._subscribers: Dict[int, Set[asyncio.Queue]] = {}

    def subscribe(self, store_id: int) -> asyncio.Queue:
        """Register a new subscriber queue for a store and return it."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(store_id, set()).add(queue)
        return queue

    def unsubscribe(self, store_id: int, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue (on SSE disconnect)."""
        subs = self._subscribers.get(store_id)
        if not subs:
            return
        subs.discard(queue)
        if not subs:
            self._subscribers.pop(store_id, None)

    def publish(self, event: Event) -> None:
        """Push event to every live subscriber of event.store_id (best-effort).

        Called after DB commit. A full queue does not raise (drops for that slow
        consumer) so a stuck client cannot block order processing.
        """
        for queue in tuple(self._subscribers.get(event.store_id, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover - defensive
                pass

    def subscriber_count(self, store_id: int) -> int:
        """Number of live subscribers for a store (test/introspection helper)."""
        return len(self._subscribers.get(store_id, ()))


# Process-wide singleton shared by Order/TableSession services and the SSE route.
broker = EventBroker()


def get_broker() -> EventBroker:
    """FastAPI dependency provider for the shared broker singleton."""
    return broker
