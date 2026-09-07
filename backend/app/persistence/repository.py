"""Repository base helpers (C0).

Thin, parameter-bound query helpers shared by domain repositories. All queries
use bound parameters (never string formatting) to avoid SQL injection.
"""
import sqlite3


def fetch_one(conn: sqlite3.Connection, sql: str, params: tuple = ()):
    return conn.execute(sql, params).fetchone()


def fetch_all(conn: sqlite3.Connection, sql: str, params: tuple = ()):
    return conn.execute(sql, params).fetchall()


def execute(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> sqlite3.Cursor:
    return conn.execute(sql, params)
