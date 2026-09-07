# U2 — Functional Design Plan (Order · Session · Realtime)

> **Unit**: U2 (C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime)
> **Branch**: `unit/u2-order-session` · **Baseline**: `pre-construction-v0.1.0` (= 2639417)
> **Scope**: Functional Design ONLY. No product code, no Code Generation until reviewed/approved.
> **Constraints (do not violate)**: FROZEN `INTEGRATION_CONTRACT.md` v0.1.0 — DB schema (§3), types/contexts (§4), REST endpoints (§5), OrderStatus (§6), SSE (§7), event payloads (§8), owned paths (§2/§10). Consume U1 interfaces (§12). Contract changes → §15 CCR (propose, do not edit).
> **Depth**: Lightweight (per `aidlc-state.md`: Functional Design EXECUTE per-unit; NFR/Infra SKIP).

---

## Part 1 — Plan Checkboxes

- [x] Step 1: Analyze U2 unit context (done — components/methods/services/unit-of-work + contract read)
- [x] Step 2: This plan created
- [x] Step 3: Clarifying questions embedded below ([Answer]: tags)
- [x] Step 4: Plan stored at `aidlc-docs/construction/plans/u2-order-session-functional-design-plan.md`
- [x] Step 5: Collect + analyze answers (resolved — see Resolved Answers below; Q7 required CCR-001 → APPROVED & MERGED, contract v0.2.0)
- [x] Step 6: Generate artifacts:
  - [x] `aidlc-docs/construction/u2-order-session/functional-design/domain-entities.md`
  - [x] `aidlc-docs/construction/u2-order-session/functional-design/business-logic-model.md`
  - [x] `aidlc-docs/construction/u2-order-session/functional-design/business-rules.md`
  - [x] (no frontend-components.md — U2 is backend-only)
- [ ] Step 7: Present completion message (2-option)
- [ ] Step 8: Await explicit approval
- [ ] Step 9: Report state change to Integration Lead (do NOT edit aidlc-state.md directly)

## Resolved Answers (contract v0.2.0)
Q1=A, Q2=D, Q3=A, Q4=A, Q5=A, Q6=A, **Q7=A** (U2 consumes U1 `common.hash_password()` per contract v0.2.0 §4/§12; CCR-001 APPROVED & MERGED), Q8=A, Q9=A, Q10=A.

---

## Part 1 — Clarifying Questions

> Format: choose A/B/C… and fill `[Answer]:`. Each has a **recommended default** for the half-day MVP.
> If you're happy with all defaults, you can just reply "Accept all defaults".

### Q1 — `order_no` generation (C3, display order number)
Contract requires `orders.order_no: TEXT` (display) but does not fix its format.
- A. Per-session sequential shown as `#1, #2, …` within a table's current usage session (resets each session) **(recommended — simplest, matches "n번째 주문" UX)**
- B. Per-store daily sequence (e.g., `20260907-001`)
- C. Global monotonic id-based (e.g., `ORD-000123`)

[Answer]:

### Q2 — Order-create validation rules (C3, `POST /api/orders`)
Contract fixes: body is `{items:[{menu_id,qty}]}`; store/table come from TabletContext; 422 on empty/invalid items. Open details:
- Reject empty `items` (422); require each `qty >= 1` (422 otherwise); each `menu_id` must exist for the context store (422/404 otherwise); duplicate `menu_id` lines are merged (qty summed). Extra unknown body fields are **ignored** (not rejected). **(recommended default — pick D to accept all of these)**
- A. As above but **reject** unknown extra fields (422) instead of ignoring
- B. As above but **do not merge** duplicate menu_id lines (keep as separate order_items)
- C. As above but `qty` upper bound enforced (e.g., 1..99)
- D. Accept the recommended default exactly as written

[Answer]:

### Q3 — Order status transition policy (C3, `change_order_status`, US-A3)
- A. Allow setting to **any** of PENDING/IN_PROGRESS/DONE regardless of current value (admin discretion; invalid enum → 422) **(recommended — simplest, admin-controlled)**
- B. Enforce forward-only PENDING → IN_PROGRESS → DONE (reject backward → 409)

[Answer]:

### Q4 — Order deletion & its effect on the session (C3, US-A4)
Contract: `DELETE /api/admin/orders/{order_id}` → recalc total + `order.deleted` (has `session_id`, `new_table_total`).
- A. Any order deletable regardless of status; recalc table total; **session stays ACTIVE even if it becomes the last/only order deleted** (empty active session is allowed) **(recommended — session lifecycle only ends via explicit end-session)**
- B. If deleting the last remaining order of a session, also auto-end/close the session

[Answer]:

### Q5 — `end_session` reset mechanics (C4, §3 note left to U2 FD)
On end-session: archive orders to `order_history`, then "현재 목록에서 제외 + 총액 0 리셋". Concretely:
- A. Mark `table_sessions.status='ENDED'` + set `ended_at`; **keep** `orders`/`order_items` rows in DB but exclude them from all "current" queries by joining on the ACTIVE session only (archive copies into `order_history`) **(recommended — non-destructive, safest for a demo, current lists filter by ACTIVE session)**
- B. Mark session ENDED **and physically delete** the session's `orders`/`order_items` rows after archiving into `order_history`

[Answer]:

### Q6 — `list_tables` dashboard shape (C4, `GET /api/admin/tables`)
Contract fields: `{table_no, current_total, has_active_session, latest_orders:[...]}`.
- `latest_orders` = most-recent **3** orders of the active session, each `{order_no, status, total, created_at}`, newest first; `current_total` = sum of active-session order totals (0 if none); every configured table appears (even with no active session). **(recommended default — pick A)**
- A. Accept recommended default
- B. Different preview count (specify N in notes)

[Answer]:

### Q7 — Table setup & password hashing ownership (C4, `POST /api/admin/tables`)
`tables.password_hash` is bcrypt. Hashing/auth utilities are U1's domain (C1/common).
- A. U2 **consumes a bcrypt hashing helper provided by U1** (e.g., `common` password-hash util) to hash `table_password` before storing; U2 does not implement its own crypto **(recommended — respects ownership; if U1 does not expose such a helper, U2 files a CCR/coordination note rather than duplicating crypto)**
- B. U2 hashes internally using the shared bcrypt library directly (no new util dependency on U1)

[Answer]:

### Q8 — Order history date filter semantics (C5, `GET .../history?date_from&date_to`)
- A. Filter by **`completed_at`** (session end date); both bounds **inclusive**; date-only `YYYY-MM-DD` interpreted as full-day UTC range; missing bound = open-ended; results reverse-chronological by `completed_at` **(recommended)**
- B. Filter by **`ordered_at`** (original order time) instead of `completed_at`

[Answer]:

### Q9 — Realtime broker & SSE stream behavior (C7)
- A. In-process pub/sub: one `asyncio.Queue` per admin SSE connection, keyed by `store_id` topic; broadcast only to same-store subscribers; **no event persistence / no replay / no Last-Event-ID** (reconnect just resubscribes to live events); periodic heartbeat comment (`: ping`) every ~15s to keep the connection alive; drop the queue on disconnect **(recommended — matches §7/§8 in-process, single-process assumption)**
- B. Same, but **no heartbeat** (rely purely on client reconnect)

[Answer]:

### Q10 — `get_or_start_session` concurrency (C4)
For the half-day local MVP (single-process, SQLite):
- A. Rely on single-process in-process guarding (simple `get-or-create` within one DB transaction); do not add distributed locking **(recommended — matches local-run scope)**
- B. Add explicit optimistic/row-lock handling for concurrent first-orders

[Answer]:

---

## Notes / Assumptions carried from the contract (not re-asked)
- Amounts are integer KRW; timestamps ISO 8601 UTC strings.
- `store_id`/`table_no` for customer APIs come **only** from `TabletContext` (never body/query).
- `order.created.order.order_id` is the same identifier used by `PATCH`/`DELETE` and `GET /api/admin/tables/{table_no}/orders`.
- `order_items` store snapshots (`name`, `unit_price`) captured at order time from U1 Menu lookup.
- `order_history.ordered_at` = snapshot of `orders.created_at` at archive time; `completed_at` = session end time.
- Table-usage session (C4) and tablet-auth session (U1) are independent; end-session never logs out the tablet.
- U2 consumes from U1: `get_connection`/repository base, `verify_tablet_token`→TabletContext, `verify_admin_token`→AdminContext, Menu price/validity lookup, common types/error format.
