"""Unit tests for OrderHistory repository + service (C5): archive, list, date filter."""
from __future__ import annotations

import unittest

from app.order.tests.support import make_conn
from app.order_history.repository import OrderHistoryRepository
from app.order_history.service import OrderHistoryService

STORE = 1
TABLE = 2


class OrderHistoryTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.service = OrderHistoryService(OrderHistoryRepository(self.conn))

    def tearDown(self):
        self.conn.close()

    def _archive(self, *, order_no, total, ordered_at, completed_at, items):
        self.service.archive_session(
            store_id=STORE,
            table_no=TABLE,
            session_id=1,
            orders=[{"order_no": order_no, "total": total, "created_at": ordered_at, "items": items}],
            completed_at=completed_at,
        )

    def test_archive_and_list_roundtrip(self):
        self._archive(
            order_no="1",
            total=7000,
            ordered_at="2026-09-05T10:00:00+00:00",
            completed_at="2026-09-05T12:00:00+00:00",
            items=[{"name": "라떼", "qty": 1, "unit_price": 5000}],
        )
        rows = self.service.list_history(store_id=STORE, table_no=TABLE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["order_no"], "1")
        self.assertEqual(rows[0]["ordered_at"], "2026-09-05T10:00:00+00:00")
        self.assertEqual(rows[0]["completed_at"], "2026-09-05T12:00:00+00:00")
        self.assertEqual(rows[0]["items"], [{"name": "라떼", "qty": 1, "unit_price": 5000}])

    def test_list_is_reverse_chronological(self):
        self._archive(order_no="1", total=100, ordered_at="2026-09-01T09:00:00+00:00",
                      completed_at="2026-09-01T10:00:00+00:00", items=[])
        self._archive(order_no="2", total=200, ordered_at="2026-09-03T09:00:00+00:00",
                      completed_at="2026-09-03T10:00:00+00:00", items=[])
        rows = self.service.list_history(store_id=STORE, table_no=TABLE)
        self.assertEqual([r["order_no"] for r in rows], ["2", "1"])

    def test_date_filter_inclusive_bounds(self):
        for day in ("01", "02", "03"):
            self._archive(order_no=day, total=1, ordered_at=f"2026-09-{day}T09:00:00+00:00",
                          completed_at=f"2026-09-{day}T10:00:00+00:00", items=[])
        rows = self.service.list_history(
            store_id=STORE, table_no=TABLE, date_from="2026-09-01", date_to="2026-09-02"
        )
        # inclusive on both ends -> days 01 and 02
        self.assertEqual({r["order_no"] for r in rows}, {"01", "02"})

    def test_history_scoped_by_table(self):
        self._archive(order_no="1", total=1, ordered_at="2026-09-01T09:00:00+00:00",
                      completed_at="2026-09-01T10:00:00+00:00", items=[])
        rows = self.service.list_history(store_id=STORE, table_no=999)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
