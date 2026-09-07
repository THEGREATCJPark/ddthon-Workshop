# Unit of Work Story Map (스토리 → 유닛 매핑)

> 승인본 `stories.md` 기준. **새 스토리 생성·기존 의미 변경 없음.**
> 여러 유닛에 걸치는 스토리는 **Primary(주 구현 유닛)** 와 **Spanning(협력 유닛)** 으로 표기.
> ⭐ = 핵심 vertical slice.

## 매핑 테이블 (12개 전부 배정)

| Story | 제목 | Primary 유닛 | Spanning(협력) | 비고 |
|---|---|---|---|---|
| US-C1 | 태블릿 자동 로그인 | U1 (Auth 발급/검증) | U3 (토큰 로컬 저장·자동 로그인 UI) | FR-C1 |
| US-C2 ⭐ | 메뉴 조회/탐색 | U1 (Menu API) | U3 (메뉴 화면) | FR-C2 |
| US-C3 ⭐ | 장바구니 관리 | U3 (localStorage) | — | FR-C3, 클라이언트 로컬(F3 유틸) |
| US-C4 ⭐ | 주문 생성 | U2 (Order 생성) | U3 (주문 UI/성공 플로우) | FR-C4, TabletContext = 식별 Source of Truth |
| US-C5 | 현재 세션 주문 내역 | U2 (현재 세션 조회) | U3 (내역 UI) | FR-C5 |
| US-A1 | 관리자 인증/세션 | U1 (Auth) | U3 (로그인 UI) | FR-A1 |
| US-A2 ⭐ | 실시간 주문 모니터링(SSE) | U2 (Realtime + 스트림) | U3 (SSE 대시보드 UI) | FR-A2, fetch text/event-stream |
| US-A3 ⭐ | 주문 상태 변경 | U2 (Order 상태) | U3 (상태 변경 UI) | FR-A4, 고객 실시간 푸시 없음(범위 밖) |
| US-A4 | 주문 삭제(직권) | U2 (Order 삭제 + 총액 재계산) | U3 (삭제 UI/확인) | FR-A3(삭제) |
| US-A5 | 이용 세션 시작/종료·과거 이력 | U2 (TableSession + OrderHistory) | U3 (세션 종료/이력 UI) | FR-A3(세션/이력) |
| US-A6 | 태블릿 초기 설정(인증/자동로그인 세션) | **U2 (테이블 setup)** | U1 (태블릿 인증/토큰), U3 (설정 UI) | FR-A3(초기설정), 이용 세션과 별개 |
| US-A7 | 메뉴 관리(CRUD/정렬) | U1 (Menu) | U3 (메뉴 관리 UI) | FR-A5 |

## 유닛별 담당 스토리 요약 (P=Primary, S=Spanning)
- **U1**: US-C1(P, 인증), US-C2(P, API), US-A1(P), US-A7(P), US-A6(S, 태블릿 인증/토큰).
- **U2**: US-C4(P), US-C5(P), US-A2(P, 백엔드), US-A3(P), US-A4(P), US-A5(P), US-A6(P, 테이블 setup).
- **U3**: US-C3(P, 장바구니) + 모든 스토리의 프론트 표현(S): US-C1~C5(고객 UI), US-A1~A7(관리자 UI).

## 배정 검증
- ✅ 12개 스토리 모두 **정확히 하나의 Primary 유닛**을 가짐(US-A6 포함 — Primary=U2 table setup, Spanning=U1 인증/토큰·U3 UI).
- ✅ 세션 개념 구분 유지: US-A5(이용/주문 세션, U2) vs US-A6(태블릿 인증 세션, U1+U2) — 별개 라이프사이클.
- ✅ US-A5는 세션/이력 스토리(메뉴 아님), 메뉴 관리는 US-A7 — 이전 초안 오류 수정 반영.
- ✅ 실시간 SSE는 US-A2 관리자 대시보드에 한정(US-A3 고객 화면 실시간 푸시 미추가).

## 핵심 vertical slice (⭐) 통합 경로
메뉴 조회(US-C2: U1 API + U3 UI) → 장바구니(US-C3: U3) → 주문 생성(US-C4: U2 + U3) → 관리자 주문 확인 SSE(US-A2: U2 + U3) → 상태 변경(US-A3: U2 + U3).
→ **3개 유닛 결과 통합 시 완성**.
