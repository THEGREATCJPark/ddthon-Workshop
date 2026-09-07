"""OrderHistory admin router (§5.4, C5 / U2).

GET /api/admin/tables/{table_no}/history?date_from=&date_to=
Reverse-chronological archived records; each item carries both `ordered_at`
(original order time) and `completed_at` (usage-completion time). Date filter Q8=A:
inclusive on both bounds, by completed_at date.
"""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query

from app.order import deps
from app.order.deps import AdminContext
from app.order.wiring import build_history_service

from . import schemas

admin_router = APIRouter(prefix="/api/admin", tags=["admin-history"])


@admin_router.get(
    "/tables/{table_no}/history", response_model=List[schemas.HistoryRecordOut]
)
async def table_history(
    table_no: int = Path(..., gt=0),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    admin: AdminContext = Depends(deps.verify_admin_token),
    conn: sqlite3.Connection = Depends(deps.get_connection),
):
    service = build_history_service(conn)
    return service.list_history(
        store_id=admin.store_id, table_no=table_no, date_from=date_from, date_to=date_to
    )
