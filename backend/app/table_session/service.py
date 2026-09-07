"""TableSession service (C4) — framework-agnostic business logic.

Covers: admin table setup (config + bcrypt password via U1 hasher), usage-session
lifecycle (ensure/get/end), and session-end archival.

Transaction & event discipline (R-TX / publish-after-commit):
- Service methods perform all DB writes on the injected repos (one shared connection)
  but DO NOT commit and DO NOT publish events.
- They return the domain events to publish. The router commits the connection first,
  then publishes the returned events via the broker. This guarantees events are only
  emitted after a durable commit.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from app.order.deps import AdminContext, PasswordHasherPort
from app.order.errors import ConflictError, NotFoundError, ValidationError
from app.order.repository import OrderRepository
from app.order_history.service import OrderHistoryService
from app.realtime import events
from app.realtime.events import Event

from .repository import TableRepository, TableSessionRepository


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TableSessionService:
    def __init__(
        self,
        *,
        table_repo: TableRepository,
        session_repo: TableSessionRepository,
        order_repo: OrderRepository,
        history_service: OrderHistoryService,
        password_hasher: Optional[PasswordHasherPort] = None,
        clock: Callable[[], str] = _utc_now_iso,
    ) -> None:
        self.table_repo = table_repo
        self.session_repo = session_repo
        self.order_repo = order_repo
        self.history_service = history_service
        self.password_hasher = password_hasher
        self.clock = clock

    # --- admin: table setup ---
    def setup_table(self, *, admin: AdminContext, table_no: int, password: str) -> dict[str, Any]:
        """Create a table config. bcrypt hashing delegated to U1 (contract v0.2.0 §4)."""
        if table_no is None or int(table_no) <= 0:
            raise ValidationError("table_no must be a positive integer")
        if not password or not password.strip():
            raise ValidationError("password is required")
        if self.password_hasher is None:
            raise ValidationError("password hasher is not configured")
        if self.table_repo.exists(admin.store_id, int(table_no)):
            raise ConflictError(f"table {table_no} already exists")
        password_hash = self.password_hasher.hash_password(password)
        table_id = self.table_repo.insert_table(
            store_id=admin.store_id, table_no=int(table_no), password_hash=password_hash
        )
        return {"id": table_id, "store_id": admin.store_id, "table_no": int(table_no)}

    def list_tables(self, *, store_id: int) -> list[int]:
        return self.table_repo.list_table_numbers(store_id)

    # --- usage session lifecycle ---
    def ensure_active_session(self, *, store_id: int, table_no: int) -> dict[str, Any]:
        """Return the ACTIVE session, creating one if none exists (first-order flow)."""
        session = self.session_repo.get_active_session(store_id, table_no)
        if session is None:
            session_id = self.session_repo.create_session(
                store_id=store_id, table_no=table_no, started_at=self.clock()
            )
            session = self.session_repo.get_session(session_id)
        return session  # type: ignore[return-value]

    def get_active_session(self, *, store_id: int, table_no: int) -> Optional[dict[str, Any]]:
        return self.session_repo.get_active_session(store_id, table_no)

    def end_session(self, *, store_id: int, table_no: int) -> tuple[dict[str, Any], list[Event]]:
        """End the active usage session: archive its orders, clear live orders, mark ENDED.

        Returns (summary, events_to_publish_after_commit).
        """
        session = self.session_repo.get_active_session(store_id, table_no)
        if session is None:
            raise NotFoundError(f"no active session for table {table_no}")
        session_id = int(session["id"])
        completed_at = self.clock()

        orders = self.order_repo.list_orders_by_session(session_id)
        archived = self.history_service.archive_session(
            store_id=store_id,
            table_no=table_no,
            session_id=session_id,
            orders=orders,
            completed_at=completed_at,
        )
        # Clear live orders (they now live in order_history).
        for o in orders:
            self.order_repo.delete_order(int(o["id"]))
        self.session_repo.end_session(session_id, completed_at)

        evt = events.table_session_ended_event(
            store_id=store_id,
            table_no=table_no,
            session_id=session_id,
            completed_at=completed_at,
        )
        summary = {
            "session_id": session_id,
            "table_no": table_no,
            "archived_orders": archived,
            "completed_at": completed_at,
        }
        return summary, [evt]
