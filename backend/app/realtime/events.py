"""Domain event builders — payloads MUST match INTEGRATION_CONTRACT.md v0.2.0 §8.

Framework-agnostic (stdlib only) so it is unit-testable without FastAPI/Pydantic.
Changing any key/type here requires a Contract Change Request (§15).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Event type constants (contract §8). Do not add new types without a CCR.
ORDER_CREATED = "order.created"
ORDER_STATUS_CHANGED = "order.status_changed"
ORDER_DELETED = "order.deleted"
TABLE_SESSION_ENDED = "table_session.ended"


@dataclass(frozen=True)
class Event:
    """A single domain event routed to same-store admin subscribers."""

    type: str
    store_id: int
    payload: dict[str, Any]


def order_created_event(
    *,
    store_id: int,
    table_no: int,
    session_id: int,
    order_id: int,
    order_no: str,
    total: int,
    created_at: str,
    items: list[dict[str, Any]],
) -> Event:
    """§8 order.created — note `order.order_id` is the same id used by PATCH/DELETE."""
    return Event(
        type=ORDER_CREATED,
        store_id=store_id,
        payload={
            "store_id": store_id,
            "table_no": table_no,
            "session_id": session_id,
            "order": {
                "order_id": order_id,
                "order_no": order_no,
                "status": "PENDING",
                "total": total,
                "created_at": created_at,
                "items": [
                    {"name": i["name"], "qty": i["qty"], "unit_price": i["unit_price"]}
                    for i in items
                ],
            },
        },
    )


def order_status_changed_event(
    *, store_id: int, table_no: int, order_id: int, order_no: str, status: str
) -> Event:
    """§8 order.status_changed."""
    return Event(
        type=ORDER_STATUS_CHANGED,
        store_id=store_id,
        payload={
            "store_id": store_id,
            "table_no": table_no,
            "order_id": order_id,
            "order_no": order_no,
            "status": status,
        },
    )


def order_deleted_event(
    *, store_id: int, table_no: int, order_id: int, session_id: int, new_table_total: int
) -> Event:
    """§8 order.deleted."""
    return Event(
        type=ORDER_DELETED,
        store_id=store_id,
        payload={
            "store_id": store_id,
            "table_no": table_no,
            "order_id": order_id,
            "session_id": session_id,
            "new_table_total": new_table_total,
        },
    )


def table_session_ended_event(
    *, store_id: int, table_no: int, session_id: int, completed_at: str
) -> Event:
    """§8 table_session.ended."""
    return Event(
        type=TABLE_SESSION_ENDED,
        store_id=store_id,
        payload={
            "store_id": store_id,
            "table_no": table_no,
            "session_id": session_id,
            "completed_at": completed_at,
        },
    )
