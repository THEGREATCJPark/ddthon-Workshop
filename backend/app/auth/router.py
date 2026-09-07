"""Auth HTTP routes (C1, contract §5.1).

POST /api/tablet/login  (none)  -> {tablet_token, expires_at}
POST /api/admin/login   (none)  -> {access_token, expires_at}
"""
import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import service
from app.persistence.db import db_dependency

router = APIRouter(prefix="/api", tags=["auth"])


class TabletLoginRequest(BaseModel):
    store_id: int
    table_no: int
    table_password: str


class AdminLoginRequest(BaseModel):
    store_id: int
    username: str
    password: str


@router.post("/tablet/login")
def tablet_login(body: TabletLoginRequest, conn: sqlite3.Connection = Depends(db_dependency)):
    return service.tablet_login(conn, body.store_id, body.table_no, body.table_password)


@router.post("/admin/login")
def admin_login(body: AdminLoginRequest, conn: sqlite3.Connection = Depends(db_dependency)):
    return service.admin_login(conn, body.store_id, body.username, body.password)
