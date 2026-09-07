"""TableSession/TableConfig admin routers (§5.4, C4 / U2).

- POST /api/admin/tables            : create a table config (bcrypt hash via U1 hasher)
- POST /api/admin/tables/{n}/end-session : archive + reset + publish table_session.ended
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Path

from app.order import deps
from app.order.deps import AdminContext, PasswordHasherPort
from app.order.errors import DomainError
from app.order.http_errors import error_response
from app.order.wiring import build_session_service
from app.realtime.broker import EventBroker, get_broker

from . import schemas

admin_router = APIRouter(prefix="/api/admin", tags=["admin-tables"])


@admin_router.post("/tables", response_model=schemas.CreateTableResponse, status_code=201)
async def create_table(
    body: schemas.CreateTableRequest,
    admin: AdminContext = Depends(deps.verify_admin_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
    hasher: PasswordHasherPort = Depends(deps.get_password_hasher),
):
    service = build_session_service(conn, password_hasher=hasher)
    try:
        table = service.setup_table(
            admin=admin, table_no=body.table_no, password=body.table_password
        )
    except DomainError as exc:
        return error_response(exc)
    conn.commit()
    return table


@admin_router.post("/tables/{table_no}/end-session", response_model=schemas.EndSessionResponse)
async def end_session(
    table_no: int = Path(..., gt=0),
    admin: AdminContext = Depends(deps.verify_admin_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
    broker: EventBroker = Depends(get_broker),
):
    service = build_session_service(conn)
    try:
        summary, events = service.end_session(store_id=admin.store_id, table_no=table_no)
    except DomainError as exc:
        return error_response(exc)
    conn.commit()
    for evt in events:
        broker.publish(evt)
    return {"ended": True, "session_id": summary["session_id"]}
