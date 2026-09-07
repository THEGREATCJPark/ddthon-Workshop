# AI-DLC State Tracking

## Project Information
- **Project Type**: Greenfield
- **Start Date**: 2026-09-07T04:43:51Z
- **Current Stage**: Integration Contract FROZEN (v0.1.0) — pre-Construction baseline ready; U1/U2/U3 parallel Construction not yet started
- **Team size**: 3 people (revised from 4), 1 unit per person + Integration Lead role (single-writer of main.py & INTEGRATION_CONTRACT.md)
- **Context**: Half-day (약 반나절) AI-DLC team practice, 4 people. Goal is a working MVP that
  exercises the full AI-DLC flow (Inception → Unit decomposition → parallel Construction →
  integration → Build/Test), NOT a production-grade product.

## Workspace State
- **Existing Code**: No
- **Reverse Engineering Needed**: No
- **Workspace Root**: /home/cik61/aidlc-workshop/table-order

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Source of Truth
- `requirements/table-order-requirements.md` (functional requirements)
- `requirements/constraints.md` (out-of-scope / exclusions)
- **Rule**: Functional requirements and constraints MUST NOT be altered or removed.

## Priority User Flow (MVP core)
메뉴 조회 → 장바구니 → 주문 생성 → 관리자에서 주문 확인 → 주문 상태 변경

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection
- [ ] Reverse Engineering (N/A - greenfield)
- [x] Requirements Analysis
- [x] User Stories
- [x] Workflow Planning
- [x] Application Design
- [x] Units Generation
- [x] Integration Contract (coordination, Q4=C) — FROZEN v0.1.0 (team-approved 2026-09-07; coordination/INTEGRATION_CONTRACT.md is the common baseline for U1/U2/U3)

### 🟢 CONSTRUCTION PHASE
- [ ] Functional Design — EXECUTE (per-unit, lightweight)
- [ ] NFR Requirements — SKIP (tech stack fixed; minimal NFRs inline)
- [ ] NFR Design — SKIP
- [ ] Infrastructure Design — SKIP (local run only)
- [ ] Code Generation — EXECUTE (per-unit)
- [ ] Build and Test — EXECUTE

## Execution Plan Summary
- **Stages to Execute (remaining)**: Application Design, Units Generation, Functional Design (per-unit), Code Generation (per-unit), Build and Test
- **Stages to Skip**: Reverse Engineering (greenfield), NFR Requirements, NFR Design, Infrastructure Design (half-day MVP / local-only / minimal NFR)
- **Next Stage**: Units Generation

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Property-Based Testing | No | Requirements Analysis |

**Note**: All three extensions opted OUT — full extension rule files are NOT loaded. Requirements-specified
security features (JWT auth, bcrypt password hashing, login attempt limiting) are still implemented as
functional requirements.

## Technical Decisions (from Requirements Analysis)
| Decision | Choice |
|---|---|
| Backend | Python + FastAPI |
| Frontend | Plain HTML + CSS + Vanilla JS (served as static files, no build tool) |
| Data store | SQLite (file-based, persistent) |
| Realtime (admin monitoring) | Server-Sent Events (SSE) as specified — no polling substitution |
| Seed data | Yes — sample store + admin account + categorized menu + a few tables |
| Run scope | Local run only (single command); no container/cloud deployment |
