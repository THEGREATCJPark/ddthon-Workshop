"""Order REST routers (§5.3 customer + §5.4 admin, C3 / U2).

Publish-after-commit: each mutating route calls the service (writes only), then
`conn.commit()`, then publishes the returned events to the store's SSE subscribers.
Auth/menu/connection dependencies are U1-provided placeholders wired in main.py.
"""
from __future__ import annotations

import sqlite3
from typing import List

from fastapi import APIRouter, Depends, Path

from app.realtime.broker import EventBroker, get_broker

from . import deps, schemas
from .deps import AdminContext, MenuLookupPort, TabletContext
from .errors import DomainError
from .http_errors import error_response
from .wiring import build_order_service

# Customer-facing (tablet Bearer)
tablet_router = APIRouter(prefix="/api/orders", tags=["orders"])
# Admin-facing (admin Bearer)
admin_router = APIRouter(prefix="/api/admin", tags=["admin-orders"])


@tablet_router.post("", response_model=schemas.CreateOrderResponse)
async def create_order(
    body: schemas.CreateOrderRequest,
    tablet: TabletContext = Depends(deps.verify_tablet_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
    menu_lookup: MenuLookupPort = Depends(deps.get_menu_lookup),
    broker: EventBroker = Depends(get_broker),
):
    service = build_order_service(conn, menu_lookup)
    try:
        order, events = service.create_order(
            tablet=tablet, items=[i.model_dump() for i in body.items]
        )
    except DomainError as exc:
        return error_response(exc)
    conn.commit()
    for evt in events:
        broker.publish(evt)
    return {"order_no": order["order_no"], "session_id": order["session_id"], "total": order["total"]}


@tablet_router.get("/current", response_model=List[schemas.CurrentOrderOut])
async def current_orders(
    tablet: TabletContext = Depends(deps.verify_tablet_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
    menu_lookup: MenuLookupPort = Depends(deps.get_menu_lookup),
):
    service = build_order_service(conn, menu_lookup)
    result = service.list_session_orders(store_id=tablet.store_id, table_no=tablet.table_no)
    return [
        {
            "order_no": str(o["order_no"]),
            "created_at": o["created_at"],
            "status": o["status"],
            "total": int(o["total"]),
            "items": o.get("items", []),
        }
        for o in result["orders"]
    ]


@admin_router.patch("/orders/{order_id}/status", response_model=schemas.UpdatedOrderResponse)
async def change_status(
    body: schemas.UpdateStatusRequest,
    order_id: int = Path(..., gt=0),
    admin: AdminContext = Depends(deps.verify_admin_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
    menu_lookup: MenuLookupPort = Depends(deps.get_menu_lookup),
    broker: EventBroker = Depends(get_broker),
):
    service = build_order_service(conn, menu_lookup)
    try:
        updated, events = service.change_status(
            store_id=admin.store_id, order_id=order_id, status=body.status
        )
    except DomainError as exc:
        return error_response(exc)
    conn.commit()
    for evt in events:
        broker.publish(evt)
    return updated


@admin_router.delete("/orders/{order_id}", status_code=204)
async def delete_order(
    order_id: int = Path(..., gt=0),
    admin: AdminContext = Depends(deps.verify_admin_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
    menu_lookup: MenuLookupPort = Depends(deps.get_menu_lookup),
    broker: EventBroker = Depends(get_broker),
):
    service = build_order_service(conn, menu_lookup)
    try:
        _, events = service.delete_order(store_id=admin.store_id, order_id=order_id)
    except DomainError as exc:
        return error_response(exc)
    conn.commit()
    for evt in events:
        broker.publish(evt)
    return None


@admin_router.get("/tables", response_model=List[schemas.AdminTableOverviewOut])
async def admin_tables(
    admin: AdminContext = Depends(deps.verify_admin_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
    menu_lookup: MenuLookupPort = Depends(deps.get_menu_lookup),
):
    service = build_order_service(conn, menu_lookup)
    return service.admin_tables_overview(store_id=admin.store_id)


@admin_router.get("/tables/{table_no}/orders", response_model=List[schemas.AdminOrderOut])
async def admin_table_orders(
    table_no: int = Path(..., gt=0),
    admin: AdminContext = Depends(deps.verify_admin_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
    menu_lookup: MenuLookupPort = Depends(deps.get_menu_lookup),
):
    service = build_order_service(conn, menu_lookup)
    try:
        return service.admin_table_orders(store_id=admin.store_id, table_no=table_no)
    except DomainError as exc:
        return error_response(exc)
