"""Unit tests for OrderService (C3) — stdlib unittest, in-memory sqlite3, fakes."""
from __future__ import annotations

import unittest

from app.order.deps import AdminContext, MenuInfo, TabletContext
from app.order.errors import NotFoundError, ValidationError
from app.order.repository import OrderRepository
from app.order.service import OrderService
from app.order.tests.support import FakeClock, FakeMenuLookup, make_conn
from app.order_history.repository import OrderHistoryRepository
from app.order_history.service import OrderHistoryService
from app.table_session.repository import TableRepository, TableSessionRepository
from app.table_session.service import TableSessionService

STORE = 1
TABLE = 5


def build_services(conn, menu_lookup, clock):
    session_service = TableSessionService(
        table_repo=TableRepository(conn),
        session_repo=TableSessionRepository(conn),
        order_repo=OrderRepository(conn),
        history_service=OrderHistoryService(OrderHistoryRepository(conn)),
        clock=clock,
    )
    order_service = OrderService(
        order_repo=OrderRepository(conn),
        session_service=session_service,
        menu_lookup=menu_lookup,
        clock=clock,
    )
    return order_service, session_service


class OrderServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.menus = FakeMenuLookup()
        self.menus.add(MenuInfo(id=10, store_id=STORE, name="아메리카노", price=4000))
        self.menus.add(MenuInfo(id=11, store_id=STORE, name="라떼", price=5000))
        self.order_service, self.session_service = build_services(
            self.conn, self.menus, FakeClock()
        )
        self.tablet = TabletContext(store_id=STORE, table_no=TABLE)
        self.admin = AdminContext(store_id=STORE, admin_user_id=1, username="owner")

    def tearDown(self):
        self.conn.close()

    def test_create_order_computes_total_and_snapshots_price(self):
        order, events = self.order_service.create_order(
            tablet=self.tablet, items=[{"menu_id": 10, "qty": 2}, {"menu_id": 11, "qty": 1}]
        )
        self.assertEqual(order["total"], 4000 * 2 + 5000)
        self.assertEqual(order["status"], "PENDING")
        self.assertEqual(order["order_no"], "1")
        # one order.created event, payload matches §8 (order.order_id present)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "order.created")
        self.assertEqual(events[0].payload["order"]["order_id"], order["id"])
        self.assertEqual(events[0].store_id, STORE)

    def test_order_no_is_sequential_within_session(self):
        o1, _ = self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])
        o2, _ = self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])
        self.assertEqual(o1["order_no"], "1")
        self.assertEqual(o2["order_no"], "2")
        self.assertEqual(o1["session_id"], o2["session_id"])

    def test_create_order_rejects_empty_items(self):
        with self.assertRaises(ValidationError):
            self.order_service.create_order(tablet=self.tablet, items=[])

    def test_create_order_rejects_unknown_menu(self):
        with self.assertRaises(ValidationError):
            self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 999, "qty": 1}])

    def test_create_order_rejects_nonpositive_qty(self):
        with self.assertRaises(ValidationError):
            self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 0}])

    def test_change_status_emits_event(self):
        order, _ = self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])
        updated, events = self.order_service.change_status(
            store_id=STORE, order_id=order["id"], status="IN_PROGRESS"
        )
        self.assertEqual(updated["status"], "IN_PROGRESS")
        self.assertEqual(events[0].type, "order.status_changed")
        self.assertEqual(events[0].payload["status"], "IN_PROGRESS")

    def test_change_status_invalid_value(self):
        order, _ = self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])
        with self.assertRaises(ValidationError):
            self.order_service.change_status(store_id=STORE, order_id=order["id"], status="BOGUS")

    def test_change_status_other_store_not_found(self):
        order, _ = self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])
        with self.assertRaises(NotFoundError):
            self.order_service.change_status(store_id=STORE + 1, order_id=order["id"], status="DONE")

    def test_delete_order_recomputes_table_total(self):
        o1, _ = self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])  # 4000
        o2, _ = self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 11, "qty": 1}])  # 5000
        result, events = self.order_service.delete_order(store_id=STORE, order_id=o1["id"])
        self.assertEqual(result["new_table_total"], 5000)
        self.assertEqual(events[0].type, "order.deleted")
        self.assertEqual(events[0].payload["new_table_total"], 5000)

    def test_admin_table_orders_identifier_consistency(self):
        # setup_table so it appears in overview; then place order
        order, _ = self.order_service.create_order(tablet=self.tablet, items=[{"menu_id": 10, "qty": 1}])
        rows = self.order_service.admin_table_orders(store_id=STORE, table_no=TABLE)
        self.assertEqual(len(rows), 1)
        # order_id returned == id usable by change_status/delete
        self.assertEqual(rows[0]["order_id"], order["id"])
        self.order_service.change_status(store_id=STORE, order_id=rows[0]["order_id"], status="DONE")

    def test_admin_table_orders_no_active_session_raises(self):
        with self.assertRaises(NotFoundError):
            self.order_service.admin_table_orders(store_id=STORE, table_no=99)

    def test_list_session_orders_empty_when_no_session(self):
        result = self.order_service.list_session_orders(store_id=STORE, table_no=77)
        self.assertEqual(result, {"session_id": None, "orders": [], "total": 0})


if __name__ == "__main__":
    unittest.main()
