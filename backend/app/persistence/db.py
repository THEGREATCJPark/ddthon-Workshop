"""SQLite connection, transaction, and schema initialization (C0).

Provided to U2/Integration Lead:
  - get_connection() / transaction()
  - init_db()
  - db_dependency() : FastAPI dependency yielding a per-request connection
"""
import sqlite3
from contextlib import contextmanager

from app.common import config
from app.persistence.schema import CREATE_STATEMENTS


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Unit-of-work: commit on success, rollback on exception."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db(conn: sqlite3.Connection) -> None:
    """Create all contract §3 tables/indexes (idempotent)."""
    with transaction(conn):
        for stmt in CREATE_STATEMENTS:
            conn.execute(stmt)


def db_dependency():
    """FastAPI dependency: one connection per request, closed afterwards."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
