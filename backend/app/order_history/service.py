"""OrderHistory service (C5) — framework-agnostic business logic.

Two responsibilities:
1. `archive_session()` — called by TableSession service when a usage session ends,
   inside the SAME DB transaction (R-TX). Snapshots every order of the session into
   `order_history` before the session's live orders are cleared.
2. `list_history()` — admin history query with optional inclusive date range (Q8=A).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from .repository import OrderHistoryRepository


class OrderHistoryService:
    def __init__(self, history_repo: OrderHistoryRepository) -> None:
        self.history_repo = history_repo

    def archive_session(
        self,
        *,
        store_id: int,
        table_no: int,
        session_id: int,
        orders: list[dict[str, Any]],
        completed_at: str,
    ) -> int:
        """Archive every order of a session. Returns number of records written.

        `orders` are the session orders (each with an `items` list) as returned by
        OrderRepository.list_orders_by_session. `ordered_at` preserves the original
        order creation time; `completed_at` is the session-end time (shared).
        """
        count = 0
        for o in orders:
            items = o.get("items", [])
            self.history_repo.insert_record(
                store_id=store_id,
                table_no=table_no,
                session_id=session_id,
                order_no=str(o["order_no"]),
                total=int(o["total"]),
                items_json=json.dumps(items, ensure_ascii=False),
                ordered_at=str(o["created_at"]),
                completed_at=completed_at,
            )
            count += 1
        return count

    def list_history(
        self,
        *,
        store_id: int,
        table_no: int,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        rows = self.history_repo.list_history(
            store_id=store_id, table_no=table_no, date_from=date_from, date_to=date_to
        )
        for r in rows:
            raw = r.pop("items_json", "[]")
            try:
                r["items"] = json.loads(raw)
            except (ValueError, TypeError):
                r["items"] = []
        return rows
