# U1 — Build & Test Summary (minimal verification)

> Unit: **U1 (C0 Persistence, C1 Auth, C2 Menu)** · Contract **v0.1.0 (FROZEN)**.
> 범위: 시간 제약에 따른 **U1 최소 검증** — 새 기능/신규 테스트 대량 작성 없이 기존 U1 테스트 전체 재실행 + 핵심 계약 CT 확인.

## 실행 방법
```bash
cd backend
. .venv/bin/activate          # python3 -m venv .venv && pip install -r requirements.txt
python -m pytest -q
```

## 결과
- **전체 U1 테스트: 39 passed** (common 5 · persistence 4 · seed 4 · auth 12 · menu 14), 실패 0.
- **핵심 Contract Tests 재확인 (계약 §13)**:
  - **CT#1** `POST /api/tablet/login` — 유효 자격 시 `tablet_token` 발급 / 잘못된 비밀번호 401 ✅
  - **CT#2** `POST /api/admin/login` — JWT 발급 / 반복 실패 5회째 429 ✅
  - **CT#3** `GET /api/menus` (tablet Bearer) — 시드 메뉴가 `display_order` 순 반환 / 무인증 401 ✅
- CT#4~#10은 U2/U3/통합 범위(본 유닛 검증 대상 아님).

## 범위 밖 (미실행 사유)
- 통합(3유닛 e2e), SSE, 주문/세션/이력 경로: U2/U3 및 Integration Lead 조립(main.py) 이후 통합 단계에서 수행.
- 신규 기능/대량 테스트: 사용자 지시에 따라 추가하지 않음.

## Known Limitation (유지)
- 참조되지 않은 메뉴 삭제만 정상 지원. `order_items` 참조 중 메뉴 삭제는 `409 CONFLICT`(세부 정책 deferred, §3 FK as-is). 통합 blocker가 되면 CCR 재검토.

## 판정
- 실패 없음 → **U1 Build & Test 최소 검증 완료.**
