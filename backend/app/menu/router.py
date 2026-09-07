"""Menu HTTP routes (C2, contract §5.2).

Customer:  GET /api/menus            (tablet Bearer, store from TabletContext)
Admin:     GET/POST/PATCH/DELETE /api/admin/menus[...], POST .../reorder
           (admin Bearer, store from AdminContext)
"""
import sqlite3

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.auth.dependencies import verify_admin_token, verify_tablet_token
from app.common.context import AdminContext, TabletContext
from app.menu import service
from app.persistence.db import db_dependency

router = APIRouter(prefix="/api", tags=["menu"])


class MenuCreateRequest(BaseModel):
    category: str
    name: str
    price: int
    description: str | None = None
    image_url: str | None = None


class MenuUpdateRequest(BaseModel):
    category: str | None = None
    name: str | None = None
    price: int | None = None
    description: str | None = None
    image_url: str | None = None


class ReorderRequest(BaseModel):
    ordered_ids: list[int]


@router.get("/menus")
def list_customer_menus(
    category: str | None = None,
    ctx: TabletContext = Depends(verify_tablet_token),
    conn: sqlite3.Connection = Depends(db_dependency),
):
    return service.list_menus(conn, ctx.store_id, category)


@router.get("/admin/menus")
def list_admin_menus(
    category: str | None = None,
    ctx: AdminContext = Depends(verify_admin_token),
    conn: sqlite3.Connection = Depends(db_dependency),
):
    return service.list_menus(conn, ctx.store_id, category)


@router.post("/admin/menus")
def create_menu(
    body: MenuCreateRequest,
    ctx: AdminContext = Depends(verify_admin_token),
    conn: sqlite3.Connection = Depends(db_dependency),
):
    return service.create_menu(conn, ctx.store_id, body.model_dump())


@router.patch("/admin/menus/{menu_id}")
def update_menu(
    menu_id: int,
    body: MenuUpdateRequest,
    ctx: AdminContext = Depends(verify_admin_token),
    conn: sqlite3.Connection = Depends(db_dependency),
):
    return service.update_menu(conn, ctx.store_id, menu_id, body.model_dump(exclude_unset=True))


@router.delete("/admin/menus/{menu_id}", status_code=204)
def delete_menu(
    menu_id: int,
    ctx: AdminContext = Depends(verify_admin_token),
    conn: sqlite3.Connection = Depends(db_dependency),
):
    service.delete_menu(conn, ctx.store_id, menu_id)
    return Response(status_code=204)


@router.post("/admin/menus/reorder", status_code=204)
def reorder_menus(
    body: ReorderRequest,
    ctx: AdminContext = Depends(verify_admin_token),
    conn: sqlite3.Connection = Depends(db_dependency),
):
    service.reorder(conn, ctx.store_id, body.ordered_ids)
    return Response(status_code=204)
