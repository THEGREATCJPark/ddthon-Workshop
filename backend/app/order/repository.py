"""Order repository (C3) — sqlite3 access for `orders` / `order_items` (schema §3).

Schema is OWNED by U1 (C0). This repo only reads/writes the contract tables and is
injected with a sqlite3.Connection (real one from U1 `get_connection` at integration,
in-memory one in unit tests). Framework-agnostic (stdlib sqlite3 only).
"""
from __future__ import annotations

import sqlite3
from typing import Any, Optional


class OrderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    # --- writes ---
    def insert_order(
        self,
        *,
        store_id: int,
        table_no: int,
        session_id: int,
        order_no: str,
        status: str,
        total: int,
        created_at: str,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO orders (store_id, table_no, session_id, order_no, status, total, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (store_id, table_no, session_id, order_no, status, total, created_at),
        )
        return int(cur.lastrowid)

    def insert_order_item(
        self, *, order_id: int, menu_id: int, name: str, unit_price: int, qty: int
    ) -> None:
        self.conn.execute(
            "INSERT INTO order_items (order_id, menu_id, name, unit_price, qty) "
            "VALUES (?, ?, ?, ?, ?)",
            (order_id, menu_id, name, unit_price, qty),
        )

    def update_status(self, order_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
        )

    def delete_order(self, order_id: int) -> None:
        self.conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        self.conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))

    # --- reads ---
    def next_order_seq(self, session_id: int) -> int:
        """Per-session sequential number (Q1=A). N-th order in the session -> N.

        NOTE: derived from current order count; see Known Limitations re: deletion.
        """
        row = self.conn.execute(
            "SELECT COUNT(*) AS c FROM orders WHERE session_id = ?", (session_id,)
        ).fetchone()
        return int(row["c"]) + 1

    def get_order(self, order_id: int) -> Optional[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_items(self, order_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT menu_id, name, unit_price, qty FROM order_items WHERE order_id = ? ORDER BY id",
            (order_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_orders_by_session(self, session_id: int) -> list[dict[str, Any]]:
        """Orders of a session, time order (oldest first), each with its items."""
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE session_id = ? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
        result = []
        for r in rows:
            o = dict(r)
            o["items"] = self.get_items(o["id"])
            result.append(o)
        return result

    def latest_orders(self, session_id: int, limit: int) -> list[dict[str, Any]]:
        """Most-recent N orders of a session (newest first) — dashboard preview (Q6=A)."""
        rows = self.conn.execute(
            "SELECT order_no, status, total, created_at FROM orders "
            "WHERE session_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def session_total(self, session_id: int) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS t FROM orders WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return int(row["t"])
