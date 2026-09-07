"""Admin SSE stream (§5.4 / §7, C7 / U2).

GET /api/admin/orders/stream  (auth: admin Bearer via Depends(verify_admin_token))
Returns text/event-stream. Each domain event is emitted as an SSE frame:

    event: <event.type>
    data: <json payload>

Heartbeat uses an SSE comment line (`: keep-alive`) — NOT a new event type — so proxies
don't drop idle connections (contract §7/§8 event set is closed). No replay / no
Last-Event-ID (Q9=A); a reconnecting client just re-subscribes.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.order import deps
from app.order.deps import AdminContext

from .broker import EventBroker, get_broker

admin_router = APIRouter(prefix="/api/admin", tags=["admin-stream"])

HEARTBEAT_SECONDS = 15.0


def _format_event(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@admin_router.get("/orders/stream")
async def orders_stream(
    request: Request,
    admin: AdminContext = Depends(deps.verify_admin_token),
    broker: EventBroker = Depends(get_broker),
):
    store_id = admin.store_id
    queue = broker.subscribe(store_id)

    async def event_generator():
        try:
            # Prime the stream so the client's fetch reader unblocks immediately.
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                # Only events for this store are ever enqueued (store-scoped topic).
                yield _format_event(event.type, event.payload)
        finally:
            broker.unsubscribe(store_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
