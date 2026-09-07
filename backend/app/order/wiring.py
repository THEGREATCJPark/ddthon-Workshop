"""Service assembly helpers for the U2 router layer.

Given a per-request sqlite3 connection (from U1's `get_connection`) and the consumed
U1 ports, build the U2 services with all repos sharing that one connection so a single
`commit()` covers the whole operation (R-TX). Imports only U2 owned modules.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from app.order_history.repository import OrderHistoryRepository
from app.order_history.service import OrderHistoryService
from app.table_session.repository import TableRepository, TableSessionRepository
from app.table_session.service import TableSessionService

from .deps import MenuLookupPort, PasswordHasherPort
from .repository import OrderRepository
from .service import OrderService


def build_history_service(conn: sqlite3.Connection) -> OrderHistoryService:
    return OrderHistoryService(OrderHistoryRepository(conn))


def build_session_service(
    conn: sqlite3.Connection, password_hasher: Optional[PasswordHasherPort] = None
) -> TableSessionService:
    return TableSessionService(
        table_repo=TableRepository(conn),
        session_repo=TableSessionRepository(conn),
        order_repo=OrderRepository(conn),
        history_service=build_history_service(conn),
        password_hasher=password_hasher,
    )


def build_order_service(conn: sqlite3.Connection, menu_lookup: MenuLookupPort) -> OrderService:
    return OrderService(
        order_repo=OrderRepository(conn),
        session_service=build_session_service(conn),
        menu_lookup=menu_lookup,
    )
