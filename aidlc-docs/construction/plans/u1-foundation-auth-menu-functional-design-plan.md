# U1 — Foundation · Auth · Menu · Functional Design Plan

> Unit: **U1 (C0 Persistence, C1 Auth, C2 Menu)** · Branch `unit/u1-foundation` · Baseline SHA `2639417` (tag `pre-construction-v0.1.0`).
> 기준 계약: **INTEGRATION_CONTRACT.md FROZEN v0.1.0** (수정 불가 — 변경 필요 시 §15 CCR).
> 이 단계 산출물은 **기술 비종속 비즈니스 로직 설계 문서만** 생성한다. **제품 코드는 생성하지 않는다.**

## 범위 경계 (self-check)
- **작성 대상(U1 owned)**: `backend/app/persistence/`, `backend/app/auth/`, `backend/app/menu/`, `backend/app/common/`, `backend/requirements.txt`(+lock), `backend/seed/` — *이번 단계에서는 설계만, 실제 파일 미생성.*
- **수정 금지**: `backend/app/order/`, `backend/app/table_session/`, `backend/app/order_history/`, `backend/app/realtime/`, `frontend/`, `backend/app/main.py`, `coordination/INTEGRATION_CONTRACT.md`, authoritative `aidlc-docs/aidlc-state.md`.

## 담당 Story (참조)
- US-C1 (태블릿 자동 로그인 — 인증 발급/검증측), US-C2 (메뉴 조회 API), US-A1 (관리자 인증), US-A7 (메뉴 관리 CRUD/정렬), US-A6 (Spanning: 태블릿 인증/토큰 발급측).

## 계획 체크리스트
- [x] 1. Unit 컨텍스트/경계 분석 (unit-of-work.md, story-map, FROZEN 계약 §3/§4/§5/§11/§12)
- [x] 2. 도메인 엔티티 모델 정의 (`domain-entities.md`) — 계약 §3 스키마를 U1 관점으로 상세화
- [x] 3. 비즈니스 로직 모델 정의 (`business-logic-model.md`) — Persistence/Seed/Auth/Menu 흐름
- [x] 4. 비즈니스 규칙/검증/에러 처리 정의 (`business-rules.md`)
- [x] 5. U2가 소비하는 U1 provided interface 명세
- [x] 6. U1 unit/contract 테스트 관점 정의
- [x] 7. Open questions / 결정사항(기본값) 명시
- [ ] 8. 사용자 검토·승인 (대기)

## 결정사항 및 Open Questions
> 검토 요청 2라운드 반영본. **CCR은 진행하지 않는다**(계약 안정성 우선 — U2/U3가 FROZEN v0.1.0 기준 병렬 진행, 핵심 slice blocker 아님). Q-U1-3의 FK CCR 제안은 **withdrawn/deferred**. 나머지는 계약 위반 없는 U1 재량 결정.

| # | 항목 | 결정 (검토 반영본) | 상태 |
|---|---|---|---|
| Q-U1-1 | JWT 서명 알고리즘/시크릿 출처 | HS256, 시크릿은 환경변수 `TABLE_ORDER_JWT_SECRET`; **미설정 시 프로세스 기동 시 랜덤 시크릿 생성**(고정 fallback 금지, 재시작 시 기존 토큰 무효). 시크릿 값 문서/코드 미기재 | 검토 반영 완료 |
| Q-U1-2 | 로그인 시도 제한 (FR-A1) | **(store_id, username) 기준 연속 5회 실패 시 10분 잠금**, 인메모리(재시작 시 초기화), **성공 시 카운터·잠금 리셋** | 검토 반영 완료 |
| Q-U1-3 | 참조 중인 메뉴 삭제 / FK | 계약 §3 FK 정의를 **그대로** 사용. 참조되지 않은 메뉴 삭제는 정상 지원. **참조 중인 메뉴 삭제 세부 정책은 이번 단계에서 미확정(deferred)**. 이전 nullable+SET NULL CCR 제안은 **withdrawn/deferred** | Known limitation (CCR 미진행) |
| Q-U1-4 | reorder 부분 목록 의미 | 포함 id를 지정 순서로 앞배치 → 미포함은 기존 상대순서 유지하며 뒤배치 → 전체를 0..N-1 연속값으로 재번호화. 외부 id는 422 | 검토 반영 완료 |
| Q-U1-5 | 토큰 타입 구분 | admin/tablet 토큰에 `typ` claim(`admin`/`tablet`) 부여, 교차 사용 차단 | 유지 |

## 계약 준수 확인 (Compliance)
- §3 DB Schema: U1이 **모든 테이블(U2 소유 도메인 테이블 포함)의 스키마 single-writer** → init_db가 계약 §3 스키마 전체를 생성. **컬럼·FK 정의 변경 없음(계약 §3 그대로 구현).** FK 삭제 CCR은 withdrawn/deferred → Known limitation. ✅
- **Known limitation**: 참조 중인 메뉴 삭제 세부 정책은 통합 blocker가 되지 않는 한 deferred (CCR 미진행).
- §4 공용 Type/Context: AdminContext/TabletContext/ErrorResponse/에러코드 계약대로 `common/`에 구현 설계. ✅
- §5 Auth/Menu API: path/method/auth/body/response 필드 집합·타입 계약 준수. ✅
- 16h 토큰, bcrypt, 로그인 시도 제한: FR-A1 및 계약 준수. ✅
- OrderStatus / event / SSE: **U1 미소유 — 불변, 참조만.** ✅
- Extensions(Security/Resiliency/PBT): 모두 opt-out → 전용 규칙 미적용(N/A). 계약 명시 보안기능(JWT/bcrypt/시도제한)은 기능 요구사항으로 구현. ✅
