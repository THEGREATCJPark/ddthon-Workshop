"""OrderHistory repository (C5) — sqlite3 access for `order_history` (schema §3).

Injected with a sqlite3.Connection. Date filtering (Q8=A) is by `completed_at`,
both bounds inclusive, compared on the date part (YYYY-MM-DD) so it is robust to
timezone-suffix formatting differences.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Optional


class OrderHistoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def insert_record(
        self,
        *,
        store_id: int,
        table_no: int,
        session_id: int,
        order_no: str,
        total: int,
        items_json: str,
        ordered_at: str,
        completed_at: str,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO order_history "
            "(store_id, table_no, session_id, order_no, total, items_json, ordered_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (store_id, table_no, session_id, order_no, total, items_json, ordered_at, completed_at),
        )
        return int(cur.lastrowid)

    def list_history(
        self,
        *,
        store_id: int,
        table_no: int,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Reverse-chronological history for a table, optional inclusive date range.

        `date_from`/`date_to` are date strings (YYYY-MM-DD). Compared against the
        date part of completed_at.
        """
        sql = ["SELECT * FROM order_history WHERE store_id = ? AND table_no = ?"]
        params: list[Any] = [store_id, table_no]
        if date_from is not None:
            sql.append("AND substr(completed_at, 1, 10) >= ?")
            params.append(date_from[:10])
        if date_to is not None:
            sql.append("AND substr(completed_at, 1, 10) <= ?")
            params.append(date_to[:10])
        sql.append("ORDER BY completed_at DESC, id DESC")
        rows = self.conn.execute(" ".join(sql), tuple(params)).fetchall()
        return [dict(r) for r in rows]
