"""Tests for schema init and DB helpers (C0)."""
from app.persistence.db import get_connection, init_db, transaction

CONTRACT_TABLES = {
    "stores", "admin_users", "tables", "menus",
    "table_sessions", "orders", "order_items", "order_history",
}


def _table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r["name"] for r in rows}


def test_init_db_creates_all_contract_tables(db_path):
    conn = get_connection(str(db_path))
    try:
        init_db(conn)
        assert CONTRACT_TABLES.issubset(_table_names(conn))
    finally:
        conn.close()


def test_init_db_is_idempotent(db_path):
    conn = get_connection(str(db_path))
    try:
        init_db(conn)
        init_db(conn)  # must not raise
        assert CONTRACT_TABLES.issubset(_table_names(conn))
    finally:
        conn.close()


def test_transaction_rolls_back_on_error(db_path):
    conn = get_connection(str(db_path))
    try:
        init_db(conn)
        try:
            with transaction(conn):
                conn.execute("INSERT INTO stores(name) VALUES('x')")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert conn.execute("SELECT COUNT(*) AS c FROM stores").fetchone()["c"] == 0
    finally:
        conn.close()


def test_foreign_keys_enforced(db_path):
    conn = get_connection(str(db_path))
    try:
        init_db(conn)
        pragma = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert pragma == 1
    finally:
        conn.close()
