# U2 — Handoff (Order · Session · Realtime)

> **Status: APPROVED, code frozen at 29 passed.** No further features / refactor / test
> expansion. **Not merged to main** (handoff only).

## 1. Branch & baseline
- Branch: `unit/u2-order-session`
- Baseline: `pre-construction-v0.1.0` (commit `2639417`)
- Contract followed: `INTEGRATION_CONTRACT.md` **v0.2.0 (FROZEN)**

## 2. Test status (frozen)
- `python -m pytest app` → **29 passed** (framework-agnostic core: stdlib `unittest` +
  in-memory sqlite3 + fakes for U1 ports).
- FastAPI/Pydantic layer: `py_compile` OK only (libs not installed here) → runtime
  verified by Integration Lead at Build & Test.

## 3. What U2 delivers
- Code: `backend/app/{order,table_session,order_history,realtime}/` only.
- See `code-summary.md` for the file-by-file map and endpoint→router table.
- See `integration-wiring-notes.md` for the exact `main.py` steps:
  1. mount 5 routers, 2. override 5 U1-provided dependencies via
  `app.dependency_overrides`, 3. connection/commit expectations, 4. broker singleton note.

## 4. Not done by U2 (owned by Integration Lead)
- `main.py` router mounting + `dependency_overrides` wiring.
- Merge to `main` (explicitly held back).
- `INTEGRATION_CONTRACT.md` / `aidlc-state.md` edits (single-writer = Integration Lead).

## 5. aidlc-state change to REPORT (not applied by U2)
Integration Lead to record, when appropriate:
- U2 Construction: Functional Design ✅ approved, Code Generation ✅ approved (29 passed).
- No new CCR from Code Generation (CCR-001 already merged into v0.2.0).

## 6. Known Limitations (retained, no fix this stage)
- **order_no reuse (Q1=A)**: per-session `COUNT(*)+1` can reuse a number after a delete —
  accepted for MVP by explicit decision (time constraint).
- **Single-process broker**: in-process pub/sub assumes one worker (contract §7/§8);
  multi-worker deploy would need an out-of-process bus (CCR, not a U2 change).
- FastAPI/Pydantic layer not runtime-executed in this environment.

## 7. Contract change status
- **None** from Code Generation. Contract untouched by U2.
