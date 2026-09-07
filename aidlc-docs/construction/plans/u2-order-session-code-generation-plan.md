# U2 — Code Generation Plan (Order · Session · Realtime)

> **Unit**: U2 (C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime)
> **Contract**: `INTEGRATION_CONTRACT.md` **v0.2.0** (FROZEN) — hard constraint.
> **Owned paths (only these are modified)**: `backend/app/order/`, `backend/app/table_session/`, `backend/app/order_history/`, `backend/app/realtime/`.
> **Do NOT modify**: `main.py`, `INTEGRATION_CONTRACT.md`, `aidlc-state.md`, U1/U3 owned paths, `requirements.txt`.
> **Answers applied**: Q1=A, Q2=D, Q3=A, Q4=A, Q5=A, Q6=A, Q7=A, Q8=A, Q9=A, Q10=A.
> **This plan is the single source of truth for U2 Code Generation.**

## Architecture / DI approach (parallel-dev safe)
- 3-layer per module: **router (FastAPI) → service (framework-agnostic) → repository (sqlite3)**.
- **Consumed U1 contracts** (`verify_tablet_token`, `verify_admin_token`, `get_connection`, Menu lookup, `hash_password`) are declared as **placeholder FastAPI dependencies + Ports** in `order/deps.py` (a U2-internal consumed-contract adapter). Integration Lead wires the real U1 impls in `main.py` via `app.dependency_overrides` (contract §14 stub/mock rule). U2 does not import from U1 paths.
- **Core is framework-agnostic** (no fastapi/pydantic import in service/repository/broker/events) → unit-testable with stdlib only (FastAPI/pydantic not installed in this env).
- `RealtimeService` broker = in-process singleton (`realtime/broker.py`), shared by Order/TableSession services.
- Events published **after DB commit** (contract & rules R-TX1/2/3). SSE keep-alive via **comment line** (`: ping`) — no new event type (per user condition).

## Story traceability
US-C4(주문 생성), US-C5(현재 세션 조회), US-A2(SSE 모니터링·백엔드 + 테이블 상세), US-A3(상태 변경), US-A4(삭제), US-A5(세션/이력), US-A6(테이블 setup측).

---

## Steps

- [x] Step 1: Project structure setup — create `backend/app/{order,table_session,order_history,realtime}/` packages (+ `tests/` subdirs, `__init__.py`).
- [x] Step 2: Realtime core — `realtime/broker.py` (EventBroker singleton, store-scoped asyncio queues), `realtime/events.py` (§8 payload builders). [US-A2]
- [x] Step 3: Order consumed-contract adapter — `order/deps.py` (TabletContext/AdminContext/MenuInfo, Ports, placeholder deps).
- [x] Step 4: Order repository — `order/repository.py` (orders/order_items CRUD, session-scoped queries, totals). [US-C4/C5/A3/A4]
- [x] Step 5: TableSession repository — `table_session/repository.py` (tables config, table_sessions lifecycle). [US-A5/A6]
- [x] Step 6: OrderHistory repository — `order_history/repository.py` (archive insert, list + date filter). [US-A5]
- [x] Step 7: OrderHistory service — `order_history/service.py` (archive_session_orders, list_history w/ Q8 filter). [US-A5]
- [x] Step 8: TableSession service — `table_session/service.py` (setup via U1 hash_password, get_or_start_session, list_tables Q6, get_table_orders, end_session archive+event Q5). [US-A2/A5/A6]
- [x] Step 9: Order service — `order/service.py` (create_order Q1/Q2, list_current_session_orders, change_status Q3, delete_order Q4, event after commit). [US-C4/C5/A3/A4]
- [x] Step 10: Pydantic schemas — `*/schemas.py` (request/response per §5).
- [x] Step 11: Routers (FastAPI APIRouter) — `order/router.py`, `table_session/router.py`, `order_history/router.py`, `realtime/router.py` (SSE, §7). Each exports a router for main.py assembly.
- [x] Step 12: Unit tests (stdlib unittest, runnable w/o FastAPI) co-located in each module's `tests/`:
  - broker/events, order service (create/current/status/delete), table_session service (setup/session/list/end), order_history service (archive/filter).
- [x] Step 13: Run tests (`python -m pytest app`) and record results — **29 passed** (0.19s).
- [x] Step 14: Documentation — `aidlc-docs/construction/u2-order-session/code/` (code summary + integration/wiring notes for Integration Lead).
- [x] Step 15: Present completion message + required report (changed files, tests, results, consumed/provided contract interfaces, known limitations, contract-change status).

## Contract interfaces
- **Provided (by U2)**: §5.3 `POST /api/orders`, `GET /api/orders/current`; §5.4 `GET /api/admin/tables`, `GET /api/admin/tables/{table_no}/orders`, `PATCH /api/admin/orders/{order_id}/status`, `DELETE /api/admin/orders/{order_id}`, `POST /api/admin/tables`, `POST /api/admin/tables/{table_no}/end-session`, `GET /api/admin/tables/{table_no}/history`; §7 `GET /api/admin/orders/stream`; §8 events (provider).
- **Consumed (from U1)**: `verify_tablet_token`→TabletContext, `verify_admin_token`→AdminContext, `get_connection`, Menu lookup, `hash_password` (v0.2.0).
