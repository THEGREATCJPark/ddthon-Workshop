"""TableSession/TableConfig repository (C4) — sqlite3 access for `tables` /
`table_sessions` (schema §3, owned by U1). Injected with a sqlite3.Connection.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Optional


class TableRepository:
    """`tables` = table config (number + bcrypt password_hash)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def exists(self, store_id: int, table_no: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM tables WHERE store_id = ? AND table_no = ?",
            (store_id, table_no),
        ).fetchone()
        return row is not None

    def insert_table(self, *, store_id: int, table_no: int, password_hash: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO tables (store_id, table_no, password_hash) VALUES (?, ?, ?)",
            (store_id, table_no, password_hash),
        )
        return int(cur.lastrowid)

    def get_table(self, store_id: int, table_no: int) -> Optional[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM tables WHERE store_id = ? AND table_no = ?",
            (store_id, table_no),
        ).fetchone()
        return dict(row) if row else None

    def list_table_numbers(self, store_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT table_no FROM tables WHERE store_id = ? ORDER BY table_no",
            (store_id,),
        ).fetchall()
        return [int(r["table_no"]) for r in rows]


class TableSessionRepository:
    """`table_sessions` = ACTIVE/ENDED usage session lifecycle."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def get_active_session(self, store_id: int, table_no: int) -> Optional[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM table_sessions "
            "WHERE store_id = ? AND table_no = ? AND status = 'ACTIVE' "
            "ORDER BY id DESC LIMIT 1",
            (store_id, table_no),
        ).fetchone()
        return dict(row) if row else None

    def get_session(self, session_id: int) -> Optional[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM table_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def create_session(self, *, store_id: int, table_no: int, started_at: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO table_sessions (store_id, table_no, status, started_at, ended_at) "
            "VALUES (?, ?, 'ACTIVE', ?, NULL)",
            (store_id, table_no, started_at),
        )
        return int(cur.lastrowid)

    def end_session(self, session_id: int, ended_at: str) -> None:
        self.conn.execute(
            "UPDATE table_sessions SET status = 'ENDED', ended_at = ? WHERE id = ?",
            (ended_at, session_id),
        )
