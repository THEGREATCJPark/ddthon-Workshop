"""Unit tests for TableSessionService (C4): setup, session lifecycle, end/archive."""
from __future__ import annotations

import unittest

from app.order.deps import AdminContext, MenuInfo, TabletContext
from app.order.errors import ConflictError, NotFoundError, ValidationError
from app.order.repository import OrderRepository
from app.order.service import OrderService
from app.order.tests.support import FakeClock, FakeHasher, FakeMenuLookup, make_conn
from app.order_history.repository import OrderHistoryRepository
from app.order_history.service import OrderHistoryService
from app.table_session.repository import TableRepository, TableSessionRepository
from app.table_session.service import TableSessionService

STORE = 1
TABLE = 3


class TableSessionServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.clock = FakeClock()
        self.history_service = OrderHistoryService(OrderHistoryRepository(self.conn))
        self.session_service = TableSessionService(
            table_repo=TableRepository(self.conn),
            session_repo=TableSessionRepository(self.conn),
            order_repo=OrderRepository(self.conn),
            history_service=self.history_service,
            password_hasher=FakeHasher(),
            clock=self.clock,
        )
        self.menus = FakeMenuLookup({10: MenuInfo(id=10, store_id=STORE, name="콜라", price=3000)})
        self.order_service = OrderService(
            order_repo=OrderRepository(self.conn),
            session_service=self.session_service,
            menu_lookup=self.menus,
            clock=self.clock,
        )
        self.admin = AdminContext(store_id=STORE, admin_user_id=1, username="owner")
        self.tablet = TabletContext(store_id=STORE, table_no=TABLE)

    def tearDown(self):
        self.conn.close()

    def test_setup_table_hashes_password(self):
        table = self.session_service.setup_table(admin=self.admin, table_no=TABLE, password="1234")
        row = TableRepository(self.conn).get_table(STORE, TABLE)
        self.assertEqual(row["password_hash"], "hashed::1234")
        self.assertEqual(table["table_no"], TABLE)

    def test_setup_table_duplicate_conflict(self):
        self.session_service.setup_table(admin=self.admin, table_no=TABLE, password="1234")
        with self.assertRaises(ConflictError):
            self.session_service.setup_table(admin=self.admin, table_no=TABLE, password="9999")

    def test_setup_table_requires_password(self):
        with self.assertRaises(ValidationError):
            self.session_service.setup_table(admin=self.admin, table_no=TABLE, password="  ")

    def test_ensure_active_session_reuses_existing(self):
        s1 = self.session_service.ensure_active_session(store_id=STORE, table_no=TABLE)
        s2 = self.session_service.ensure_active_session(store_id=STORE, table_no=TABLE)
        self.assertEqual(s1["id"], s2["id"])
        self.assertEqual(s1["status"], "ACTIVE")

    def test_end_session_archives_clears_and_ends(self):
        self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 2}])
        self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])

        summary, events = self.session_service.end_session(store_id=STORE, table_no=TABLE)

        self.assertEqual(summary["archived_orders"], 2)
        self.assertEqual(events[0].type, "table_session.ended")
        # live orders cleared
        self.assertEqual(OrderRepository(self.conn).list_orders_by_session(summary["session_id"]), [])
        # session marked ENDED
        session = TableSessionRepository(self.conn).get_session(summary["session_id"])
        self.assertEqual(session["status"], "ENDED")
        self.assertIsNotNone(session["ended_at"])
        # archived to history preserving order time and completion time
        history = self.history_service.list_history(store_id=STORE, table_no=TABLE)
        self.assertEqual(len(history), 2)
        self.assertIn("ordered_at", history[0])
        self.assertIn("completed_at", history[0])

    def test_end_session_no_active_raises(self):
        with self.assertRaises(NotFoundError):
            self.session_service.end_session(store_id=STORE, table_no=TABLE)

    def test_current_orders_empty_after_end_session(self):
        self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])
        self.session_service.end_session(store_id=STORE, table_no=TABLE)
        result = self.order_service.list_session_orders(store_id=STORE, table_no=TABLE)
        self.assertEqual(result["orders"], [])


if __name__ == "__main__":
    unittest.main()
