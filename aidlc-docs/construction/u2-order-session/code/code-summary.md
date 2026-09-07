# U2 — Code Summary (Order · Session · Realtime)

> Contract: `INTEGRATION_CONTRACT.md` **v0.2.0 (FROZEN)** — followed as a hard constraint.
> Owned paths only were modified: `backend/app/order/`, `backend/app/table_session/`,
> `backend/app/order_history/`, `backend/app/realtime/`.
> `main.py`, `INTEGRATION_CONTRACT.md`, `aidlc-state.md`, and U1/U3 paths were **not** touched.

## 1. Architecture

3-layer per module, with the core kept **framework-agnostic** (stdlib only) so it is
unit-testable without FastAPI/Pydantic (not installed in this environment):

```
router (FastAPI/Pydantic)  ->  service (pure Python)  ->  repository (sqlite3)
                                        |
                                        +-> realtime broker (asyncio, in-process)
```

- **Publish-after-commit**: services perform DB writes only and **return** the domain
  events. The router calls `conn.commit()` first, then `broker.publish(evt)`. Events are
  never emitted before a durable commit (rules R-TX / R-E).
- **Consumed U1 contracts** are declared as placeholder FastAPI dependencies + Ports in
  `order/deps.py`. U2 never imports from U1 paths; the Integration Lead wires the real
  U1 implementations via `app.dependency_overrides` (§14).
- **SSE keep-alive** uses an SSE **comment line** (`: keep-alive`), NOT a new event type
  (§8 event set stays closed).

## 2. Files created

### `backend/app/order/`
- `__init__.py` — package doc.
- `deps.py` — consumed-contract adapter: `TabletContext`, `AdminContext`, `MenuInfo`;
  Ports `MenuLookupPort`, `PasswordHasherPort`; placeholder deps `verify_tablet_token`,
  `verify_admin_token`, `get_connection`, `get_menu_lookup`, `get_password_hasher`.
- `errors.py` — `DomainError`/`ValidationError`(422)/`NotFoundError`(404)/`ConflictError`(409),
  mapped to contract error codes (§4).
- `repository.py` — `OrderRepository`: order/item CRUD, per-session sequence, session-scoped
  reads, totals.
- `service.py` — `OrderService`: `create_order`, `change_status`, `delete_order`,
  `list_session_orders`, `latest_orders`, `admin_tables_overview`, `admin_table_orders`.
- `schemas.py` — Pydantic request/response models (§5.3/§5.4).
- `wiring.py` — builds services sharing one connection (single-commit / R-TX).
- `http_errors.py` — `DomainError -> {error:{code,message}}` JSONResponse (§4 envelope).
- `router.py` — `tablet_router` (`/api/orders*`) + `admin_router` (`/api/admin/*`).
- `tests/support.py` + `tests/test_order_service.py`.

### `backend/app/table_session/`
- `__init__.py`, `repository.py` (`TableRepository`, `TableSessionRepository`),
  `service.py` (`TableSessionService`: `setup_table`, `ensure_active_session`,
  `get_active_session`, `end_session`, `list_tables`), `schemas.py`,
  `router.py` (`admin_router`: create table + end-session), `tests/…`.

### `backend/app/order_history/`
- `__init__.py`, `repository.py` (`OrderHistoryRepository`), `service.py`
  (`OrderHistoryService`: `archive_session`, `list_history`), `schemas.py`,
  `router.py` (`admin_router`: history query), `tests/…`.

### `backend/app/realtime/`
- `__init__.py`, `events.py` (§8 payload builders + type constants),
  `broker.py` (`EventBroker` + singleton `broker` + `get_broker`),
  `router.py` (`admin_router`: SSE `/api/admin/orders/stream`), `tests/…`.

## 3. Endpoints provided (routers to mount)

| Router symbol | Prefix | Endpoints |
|---|---|---|
| `app.order.router.tablet_router` | `/api/orders` | `POST ""`, `GET "/current"` |
| `app.order.router.admin_router` | `/api/admin` | `PATCH /orders/{id}/status`, `DELETE /orders/{id}`, `GET /tables`, `GET /tables/{n}/orders` |
| `app.table_session.router.admin_router` | `/api/admin` | `POST /tables`, `POST /tables/{n}/end-session` |
| `app.order_history.router.admin_router` | `/api/admin` | `GET /tables/{n}/history` |
| `app.realtime.router.admin_router` | `/api/admin` | `GET /orders/stream` (SSE) |

## 4. Design decisions vs. approved answers
- **Q1=A** order_no = per-session sequence (`COUNT(*)+1`). See Known Limitations.
- **Q3=A** status change accepts any of `PENDING|IN_PROGRESS|DONE` (no forced transition graph).
- **Q4=A** delete recomputes and returns/publishes `new_table_total`.
- **Q5=A** end-session archives every order to `order_history`, clears live orders,
  marks session `ENDED`, publishes `table_session.ended`.
- **Q6=A** dashboard overview includes up to 5 latest orders per table.
- **Q8=A** history date filter inclusive on both bounds (compared on `completed_at` date).
- **Q9=A** SSE has no replay / no Last-Event-ID; reconnect re-subscribes.
