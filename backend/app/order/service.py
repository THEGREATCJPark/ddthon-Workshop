"""Order service (C3) — framework-agnostic business logic.

Responsibilities: place orders (tablet), change status / delete (admin), and read
queries for tablet + admin dashboard.

Transaction & event discipline (R-TX / publish-after-commit): service methods write
via injected repos on one shared connection but DO NOT commit or publish. They return
the events to publish; the router commits, then publishes. Menu price/name is looked
up from U1 via MenuLookupPort (single source of truth) — never trusted from the client.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from app.order_history.service import OrderHistoryService  # noqa: F401  (documents C5 link)
from app.realtime import events
from app.realtime.events import Event
from app.table_session.service import TableSessionService

from .deps import MenuLookupPort, TabletContext
from .errors import NotFoundError, ValidationError
from .repository import OrderRepository

VALID_STATUSES = ("PENDING", "IN_PROGRESS", "DONE")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrderService:
    def __init__(
        self,
        *,
        order_repo: OrderRepository,
        session_service: TableSessionService,
        menu_lookup: MenuLookupPort,
        clock: Callable[[], str] = _utc_now_iso,
    ) -> None:
        self.order_repo = order_repo
        self.session_service = session_service
        self.menu_lookup = menu_lookup
        self.clock = clock

    # --- tablet: place order ---
    def create_order(
        self, *, tablet: TabletContext, items: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], list[Event]]:
        if not items:
            raise ValidationError("at least one item is required")

        resolved: list[dict[str, Any]] = []
        for raw in items:
            menu_id = raw.get("menu_id")
            qty = raw.get("qty")
            if menu_id is None or qty is None:
                raise ValidationError("each item requires menu_id and qty")
            if not isinstance(qty, int) or qty <= 0:
                raise ValidationError("qty must be a positive integer")
            menu = self.menu_lookup.get_menu(tablet.store_id, int(menu_id))
            if menu is None or menu.store_id != tablet.store_id:
                raise ValidationError(f"menu {menu_id} not found in store")
            resolved.append(
                {"menu_id": menu.id, "name": menu.name, "unit_price": menu.price, "qty": qty}
            )

        total = sum(it["unit_price"] * it["qty"] for it in resolved)
        session = self.session_service.ensure_active_session(
            store_id=tablet.store_id, table_no=tablet.table_no
        )
        session_id = int(session["id"])
        order_no = str(self.order_repo.next_order_seq(session_id))
        created_at = self.clock()

        order_id = self.order_repo.insert_order(
            store_id=tablet.store_id,
            table_no=tablet.table_no,
            session_id=session_id,
            order_no=order_no,
            status="PENDING",
            total=total,
            created_at=created_at,
        )
        for it in resolved:
            self.order_repo.insert_order_item(
                order_id=order_id,
                menu_id=it["menu_id"],
                name=it["name"],
                unit_price=it["unit_price"],
                qty=it["qty"],
            )

        evt = events.order_created_event(
            store_id=tablet.store_id,
            table_no=tablet.table_no,
            session_id=session_id,
            order_id=order_id,
            order_no=order_no,
            total=total,
            created_at=created_at,
            items=resolved,
        )
        order = {
            "id": order_id,
            "order_no": order_no,
            "session_id": session_id,
            "status": "PENDING",
            "total": total,
            "created_at": created_at,
            "items": resolved,
        }
        return order, [evt]

    # --- admin: status change ---
    def change_status(
        self, *, store_id: int, order_id: int, status: str
    ) -> tuple[dict[str, Any], list[Event]]:
        if status not in VALID_STATUSES:
            raise ValidationError(f"status must be one of {VALID_STATUSES}")
        order = self.order_repo.get_order(order_id)
        if order is None or int(order["store_id"]) != store_id:
            raise NotFoundError(f"order {order_id} not found")
        self.order_repo.update_status(order_id, status)
        evt = events.order_status_changed_event(
            store_id=store_id,
            table_no=int(order["table_no"]),
            order_id=order_id,
            order_no=str(order["order_no"]),
            status=status,
        )
        return {"id": order_id, "status": status}, [evt]

    # --- admin: delete ---
    def delete_order(self, *, store_id: int, order_id: int) -> tuple[dict[str, Any], list[Event]]:
        order = self.order_repo.get_order(order_id)
        if order is None or int(order["store_id"]) != store_id:
            raise NotFoundError(f"order {order_id} not found")
        session_id = int(order["session_id"])
        table_no = int(order["table_no"])
        self.order_repo.delete_order(order_id)
        new_total = self.order_repo.session_total(session_id)
        evt = events.order_deleted_event(
            store_id=store_id,
            table_no=table_no,
            order_id=order_id,
            session_id=session_id,
            new_table_total=new_total,
        )
        return {"id": order_id, "deleted": True, "new_table_total": new_total}, [evt]

    # --- reads ---
    def list_session_orders(self, *, store_id: int, table_no: int) -> dict[str, Any]:
        session = self.session_service.get_active_session(store_id=store_id, table_no=table_no)
        if session is None:
            return {"session_id": None, "orders": [], "total": 0}
        session_id = int(session["id"])
        orders = self.order_repo.list_orders_by_session(session_id)
        return {
            "session_id": session_id,
            "orders": orders,
            "total": self.order_repo.session_total(session_id),
        }

    def latest_orders(self, *, store_id: int, table_no: int, limit: int = 5) -> list[dict[str, Any]]:
        session = self.session_service.get_active_session(store_id=store_id, table_no=table_no)
        if session is None:
            return []
        return self.order_repo.latest_orders(int(session["id"]), limit)

    def admin_tables_overview(self, *, store_id: int) -> list[dict[str, Any]]:
        """Dashboard grid (§5.4 GET /api/admin/tables) — one row per configured table."""
        overview: list[dict[str, Any]] = []
        for table_no in self.session_service.list_tables(store_id=store_id):
            session = self.session_service.get_active_session(store_id=store_id, table_no=table_no)
            if session is None:
                overview.append(
                    {
                        "table_no": table_no,
                        "current_total": 0,
                        "has_active_session": False,
                        "latest_orders": [],
                    }
                )
            else:
                session_id = int(session["id"])
                overview.append(
                    {
                        "table_no": table_no,
                        "current_total": self.order_repo.session_total(session_id),
                        "has_active_session": True,
                        "latest_orders": self.order_repo.latest_orders(session_id, 5),
                    }
                )
        return overview

    def admin_table_orders(self, *, store_id: int, table_no: int) -> list[dict[str, Any]]:
        """§5.4 GET /api/admin/tables/{table_no}/orders — 404 if no active session.

        Returns order_id (same identifier used by PATCH/DELETE and order.created §8).
        """
        session = self.session_service.get_active_session(store_id=store_id, table_no=table_no)
        if session is None:
            raise NotFoundError(f"no active session for table {table_no}")
        orders = self.order_repo.list_orders_by_session(int(session["id"]))
        return [
            {
                "order_id": int(o["id"]),
                "order_no": str(o["order_no"]),
                "created_at": o["created_at"],
                "status": o["status"],
                "total": int(o["total"]),
                "items": o.get("items", []),
            }
            for o in orders
        ]
