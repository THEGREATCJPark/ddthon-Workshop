"""Test helper: build a FastAPI app wired with U1 routers against a temp DB.

This is a TEST factory only — it is NOT the composition root (main.py, owned by
the Integration Lead). It exists so U1 can be verified independently before
integration.
"""
from app.common import config, errors
from app.persistence.db import get_connection, init_db


def build_test_app(db_path, seed: bool = True):
    from fastapi import FastAPI
    from app.auth import rate_limit
    from app.auth.router import router as auth_router
    from app.menu.router import router as menu_router
    from seed.seeder import seed_if_empty

    config.DB_PATH = str(db_path)
    rate_limit.reset_all()

    conn = get_connection(str(db_path))
    try:
        init_db(conn)
        if seed:
            seed_if_empty(conn)
    finally:
        conn.close()

    app = FastAPI()
    errors.register_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(menu_router)
    return app
