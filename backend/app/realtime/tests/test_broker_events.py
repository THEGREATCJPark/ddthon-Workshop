"""Unit tests for the realtime broker (C7) and event payload contract (§8)."""
from __future__ import annotations

import asyncio
import unittest

from app.realtime import events
from app.realtime.broker import EventBroker


class EventPayloadTest(unittest.TestCase):
    def test_order_created_payload_has_order_id(self):
        evt = events.order_created_event(
            store_id=1, table_no=2, session_id=3, order_id=99, order_no="1",
            total=8000, created_at="2026-09-07T00:00:00+00:00",
            items=[{"name": "라떼", "qty": 1, "unit_price": 5000}],
        )
        self.assertEqual(evt.type, "order.created")
        self.assertEqual(evt.payload["order"]["order_id"], 99)
        self.assertEqual(evt.payload["order"]["status"], "PENDING")
        self.assertEqual(evt.payload["order"]["items"], [{"name": "라떼", "qty": 1, "unit_price": 5000}])

    def test_status_changed_payload_keys(self):
        evt = events.order_status_changed_event(
            store_id=1, table_no=2, order_id=99, order_no="1", status="DONE"
        )
        self.assertEqual(
            set(evt.payload.keys()), {"store_id", "table_no", "order_id", "order_no", "status"}
        )

    def test_deleted_payload_keys(self):
        evt = events.order_deleted_event(
            store_id=1, table_no=2, order_id=99, session_id=3, new_table_total=1000
        )
        self.assertEqual(
            set(evt.payload.keys()),
            {"store_id", "table_no", "order_id", "session_id", "new_table_total"},
        )

    def test_session_ended_payload_keys(self):
        evt = events.table_session_ended_event(
            store_id=1, table_no=2, session_id=3, completed_at="2026-09-07T00:00:00+00:00"
        )
        self.assertEqual(
            set(evt.payload.keys()), {"store_id", "table_no", "session_id", "completed_at"}
        )


class BrokerTest(unittest.TestCase):
    def test_publish_only_reaches_same_store_subscribers(self):
        async def scenario():
            broker = EventBroker()
            q_store1 = broker.subscribe(1)
            q_store2 = broker.subscribe(2)
            evt = events.table_session_ended_event(
                store_id=1, table_no=2, session_id=3, completed_at="t"
            )
            broker.publish(evt)
            self.assertEqual(q_store1.qsize(), 1)
            self.assertEqual(q_store2.qsize(), 0)
            received = await q_store1.get()
            self.assertIs(received, evt)

        asyncio.run(scenario())

    def test_unsubscribe_stops_delivery(self):
        async def scenario():
            broker = EventBroker()
            q = broker.subscribe(1)
            broker.unsubscribe(1, q)
            self.assertEqual(broker.subscriber_count(1), 0)
            broker.publish(events.table_session_ended_event(store_id=1, table_no=1, session_id=1, completed_at="t"))
            self.assertEqual(q.qsize(), 0)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
