"""Application composition root (Integration Lead owned).

Assembles unit-provided artifacts only — it does NOT implement domain logic.
Currently wires U1 (Foundation·Auth·Menu). U2/U3 routers/static will be added
here by the Integration Lead as those units are merged.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.common import errors
from app.persistence.db import get_connection, init_db
from app.auth.router import router as auth_router
from app.menu.router import router as menu_router
from seed.seeder import seed_if_empty


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

# NOTE: U2 (order/session/history/realtime) routers and U3 static mounts are
# added here when those units merge. No stubs are added on their behalf.
