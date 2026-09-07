"""Application composition root (Integration Lead owned).

Assembles unit-provided artifacts only — it does NOT implement domain logic.
Currently wires U1 (Foundation·Auth·Menu). U2/U3 routers/static will be added
here by the Integration Lead as those units are merged.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.common import errors
from app.persistence.db import db_dependency, get_connection, init_db
from app.auth.dependencies import verify_admin_token, verify_tablet_token
from app.auth.security import hash_password
from app.auth.router import router as auth_router
from app.menu.repository import get_for_order
from app.menu.router import router as menu_router
from app.order import deps as order_deps
from app.order import router as order_router
from app.order_history import router as order_history_router
from app.realtime import router as realtime_router
from app.table_session import router as table_session_router
from seed.seeder import seed_if_empty


class _MenuLookupAdapter:
    def __init__(self, conn):
        self.conn = conn

    def get_menu(self, store_id: int, menu_id: int):
        row = get_for_order(self.conn, store_id, menu_id)
        if row is None:
            return None
        return order_deps.MenuInfo(
            id=int(row["id"]),
            store_id=store_id,
            name=str(row["name"]),
            price=int(row["price"]),
        )


class _PasswordHasherAdapter:
    @staticmethod
    def hash_password(plaintext: str) -> str:
        return hash_password(plaintext)


async def _u2_db_dependency():
    """Keep SQLite creation/use on U2's async endpoint event-loop thread."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _get_menu_lookup(conn=Depends(_u2_db_dependency)):
    return _MenuLookupAdapter(conn)


def _get_password_hasher():
    return _PasswordHasherAdapter()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup: create schema (idempotent) and seed sample data if the DB is empty.
    conn = get_connection()
    try:
        init_db(conn)
        seed_if_empty(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="테이블오더 MVP", lifespan=lifespan)

# U1 error handlers + routers (contract §4/§5).
errors.register_error_handlers(app)
app.include_router(auth_router)
app.include_router(menu_router)

# U2 routers and consumed U1 capabilities.
app.include_router(order_router.tablet_router)
app.include_router(order_router.admin_router)
app.include_router(table_session_router.admin_router)
app.include_router(order_history_router.admin_router)
app.include_router(realtime_router.admin_router)

app.dependency_overrides[order_deps.verify_tablet_token] = verify_tablet_token
app.dependency_overrides[order_deps.verify_admin_token] = verify_admin_token
app.dependency_overrides[order_deps.get_connection] = _u2_db_dependency
app.dependency_overrides[order_deps.get_menu_lookup] = _get_menu_lookup
app.dependency_overrides[order_deps.get_password_hasher] = _get_password_hasher

# U3 static mounts are added here after the frontend unit merges.
