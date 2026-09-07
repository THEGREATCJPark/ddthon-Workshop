"""Auth data access (C1). Reads admin_users and tables for login."""
import sqlite3

from app.persistence.repository import fetch_one


def get_admin(conn: sqlite3.Connection, store_id: int, username: str):
    return fetch_one(
        conn,
        "SELECT id, store_id, username, password_hash FROM admin_users "
        "WHERE store_id = ? AND username = ?",
        (store_id, username),
    )


def get_table(conn: sqlite3.Connection, store_id: int, table_no: int):
    return fetch_one(
        conn,
        "SELECT id, store_id, table_no, password_hash FROM tables "
        "WHERE store_id = ? AND table_no = ?",
        (store_id, table_no),
    )
