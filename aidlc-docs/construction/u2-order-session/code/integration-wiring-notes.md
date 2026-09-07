# U2 — Integration / Wiring Notes (for Integration Lead)

U2 is contract-complete but intentionally **not self-wired**. This is the checklist the
Integration Lead applies in `main.py` (Integration-Lead-owned; U2 did not modify it).

## 1. Mount routers

```python
from app.order import router as order_router
from app.table_session import router as table_session_router
from app.order_history import router as order_history_router
from app.realtime import router as realtime_router

app.include_router(order_router.tablet_router)
app.include_router(order_router.admin_router)
app.include_router(table_session_router.admin_router)
app.include_router(order_history_router.admin_router)
app.include_router(realtime_router.admin_router)
```

## 2. Override consumed U1 dependencies (§14 `app.dependency_overrides`)

U2's placeholders in `app/order/deps.py` raise `NotImplementedError` until overridden:

| Placeholder (U2) | Provide (U1) | Returns |
|---|---|---|
| `deps.verify_tablet_token` | U1 tablet JWT verifier | `TabletContext(store_id, table_no)` |
| `deps.verify_admin_token` | U1 admin JWT verifier | `AdminContext(store_id, admin_user_id, username)` |
| `deps.get_connection` | U1 DB connection provider | `sqlite3.Connection` (per-request) |
| `deps.get_menu_lookup` | adapter over U1 Menu read | object with `get_menu(store_id, menu_id) -> MenuInfo|None` |
| `deps.get_password_hasher` | wrapper over U1 `common.hash_password` | object with `hash_password(plaintext) -> str` |

The override return types only need to be **attribute-compatible** with U2's
`TabletContext`/`AdminContext`/`MenuInfo` (duck-typed). Example:

```python
from app.order import deps
app.dependency_overrides[deps.verify_admin_token] = u1_verify_admin_token
app.dependency_overrides[deps.get_connection] = u1_get_connection
app.dependency_overrides[deps.get_menu_lookup] = lambda: U1MenuLookupAdapter()
app.dependency_overrides[deps.get_password_hasher] = lambda: U1HasherAdapter()  # common.hash_password
```

## 3. Connection / transaction expectations
- `get_connection` should yield a per-request `sqlite3.Connection`. U2 sets
  `row_factory = sqlite3.Row` on it. U2 calls `conn.commit()` in the router after a
  successful service call; it does not close the connection (owner = provider).
- All repos in one request share the single connection (via `wiring.py`) so one commit
  is atomic across orders + history + session changes on end-session (R-TX).

## 4. Broker
- `app.realtime.broker.broker` is a process-wide singleton (single-process assumption,
  §7/§8). Both the mutating routes and the SSE route resolve it through `get_broker`.
  No wiring needed unless the deployment runs multiple worker processes (out of scope
  for the MVP; would require an out-of-process bus — that is a CCR, not a U2 change).

## 5. Error envelope
- Domain failures already return `{"error": {"code", "message"}}` (§4) with the correct
  status. If U1 auth deps raise `401 UNAUTHORIZED`/`403 FORBIDDEN`, keep them consistent
  with the same envelope at the app level (U1/Integration concern).

## 6. Suggested contract test hooks (from §13)
- #4 identity principle: `POST /api/orders` ignores any client store/table, using context.
- #5 `PATCH .../status` rejects non-`OrderStatus` with 422.
- #7 `order.created` payload contains `order.order_id`.
- #8 `GET /api/admin/tables/{n}/orders` returns `order_id` usable by `PATCH`/`DELETE`.
- #10 end-session → `table_session.ended` + empty `/current` + history entries carry both
  `ordered_at` and `completed_at`.
