# U3 — Frontend Functional Design Questions

> 대상 유닛: **U3 — Frontend** (F1 CustomerApp `/`, F2 AdminApp `/admin`, F3 Shared JS: `apiClient` · `sseClient` · format utils)
> 목적: FROZEN Integration Contract **v0.1.0** 을 위반하지 않는 범위에서 U3 프론트엔드의 상세 설계 결정을 확정합니다.
>
> **이미 계약/요구사항으로 확정되어 질문에서 제외한 사항**
> - 스택: Vanilla JS(빌드 도구 없음) · 정적 서빙 · `apiClient`(Bearer 자동 첨부, JSON 직렬화/역직렬화) · `sseClient`(native `EventSource` 대신 `fetch()` + `ReadableStream` 로 `text/event-stream` 파싱)
> - REST 경로/시그니처, `OrderStatus` 값(`PENDING`/`IN_PROGRESS`/`DONE`), SSE 엔드포인트·이벤트 페이로드
> - 신원 출처: `store_id`/`table_no` 는 항상 인증 컨텍스트(TabletContext)에서만 도출하며 요청 body 에 포함하지 않음 (§4 / §5.3)
> - 장바구니 = localStorage, 주문 성공 흐름 = 주문번호 표시 → 장바구니 비우기 → 메뉴로 리다이렉트
>
> **답변 방법**: 각 질문의 `[Answer]:` 태그 뒤에 **선택한 옵션의 letter 하나만** 적습니다 (예: `[Answer]: A`). 마지막 `Other` 를 고르면 letter 뒤에 원하는 방식을 자유롭게 덧붙입니다.
> 형식 근거: `.aidlc-rule-details/common/question-format-guide.md`

---

**A. 앱 구조 / 렌더링**

## Question 1

F1(고객) · F2(관리자) 각 앱의 **화면 구성 방식**을 어떻게 할까요?

A) 앱당 단일 HTML + JS 로 뷰 전환(SPA 유사) — 예: `customer/index.html` 하나에서 메뉴/장바구니/주문내역 뷰를 JS 로 교체 (단일 명령 정적 서빙에 가장 단순, 권장)

B) 화면별 개별 HTML 페이지(다중 파일) — 예: `menu.html`, `cart.html`, `history.html` 링크 이동

C) 단일 HTML + 해시 라우터(`#/menu`, `#/history`) — 새로고침·뒤로가기 지원

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2

화면을 그리는 **렌더링 구현 방식**은?

A) 템플릿 문자열 + `innerHTML` 로 섹션 렌더 (가장 단순; 서버·사용자 유래 문자열은 `escapeHtml()` 유틸로 이스케이프하여 XSS 방지)

B) `<template>` 엘리먼트 clone + DOM API 로 항목 렌더 (XSS·성능상 안전)

C) 작은 자체 render 헬퍼 함수(`el(tag, props, children)`) 도입

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3

프론트 **클라이언트 상태 관리** 방식은?

A) 모듈 스코프 plain 객체(`state`) + 변경 시 명시적 재렌더 호출 (MVP 에 충분, 권장)

B) 아주 작은 pub/sub 스토어(구독 → 자동 재렌더) 직접 구현

C) 별도 상태 관리 없이 DOM 자체를 상태로 사용

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

**B. 상태 관리 / 클라이언트 저장**

## Question 4

**인증 토큰 저장 위치**는? (관리자 JWT 16h / 태블릿 `tablet_token` 16h — 새로고침·자동 로그인 유지 필요)

A) 둘 다 `localStorage` (새로고침·앱 재실행에도 자동 로그인 유지 — 요구사항의 세션 유지/자동 로그인에 부합, 권장)

B) 관리자 JWT = `sessionStorage`, 태블릿 토큰 = `localStorage` (관리자는 탭 종료 시 만료)

C) 둘 다 `sessionStorage` (새로고침은 유지되나 탭 종료 시 만료)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5

**장바구니 localStorage 구조**는? (태블릿은 특정 store/table 에 고정이지만 방어적 설계 여부)

A) 단일 키(예: `to_cart`)에 `[{menu_id, name, unit_price, qty}]` 배열만 저장 (가장 단순)

B) `store_id`+`table_no` 로 키 스코프(예: `cart:{store}:{table}`) — 태블릿 재설정/다른 테이블 대비

C) 단일 키 + 저장 시점의 store/table 메타 포함, 현재 컨텍스트와 불일치하면 자동 초기화 (권장)

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 6

주문 확인 화면에 쓸 **메뉴명·단가 스냅샷** 확보 방식은? (계약상 서버로는 `items:[{menu_id, qty}]` 만 전송)

A) 클라이언트는 `{menu_id, qty}` 만 보관/전송하고, 이름·단가 표시는 메뉴 조회 결과로 매번 조인 (계약 최소 준수)

B) 장바구니에 `name`·`unit_price` 를 함께 보관해 주문 확인 화면에 즉시 표시 (전송은 여전히 `menu_id`/`qty` 만, 권장)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

---

**C. 고객(F1) UX**

## Question 7

메뉴 **카테고리 탐색 UI** 는?

A) 상단 가로 탭 바(카테고리 칩) — 선택 시 해당 카테고리 필터 (터치 태블릿 친화, 권장)

B) 좌측 세로 사이드바 카테고리 리스트

C) 전체 메뉴를 카테고리 섹션으로 나열 + 상단 앵커 점프

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8

**장바구니 표시 위치/형태**는?

A) 하단 고정 바(총액·개수 요약) → 탭하면 상세 펼침 (태블릿 가로/세로 모두 무난, 권장)

B) 우측 고정 패널(메뉴와 2단 레이아웃)

C) 별도 장바구니 화면/모달로 전환

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9

**주문 성공 후 화면 흐름**은? (계약: 주문번호 표시 → 장바구니 비우기 → 메뉴로 리다이렉트)

A) 성공 화면에 주문번호 표시 후 **5초 뒤 자동 리다이렉트** (요구사항 명시값, 권장)

B) 성공 화면 표시 후 **3초** 뒤 자동 리다이렉트

C) 자동 리다이렉트 없이 사용자가 "확인" 을 누를 때 메뉴로 이동

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10

메뉴 **이미지가 없거나 로드 실패**할 때 처리는?

A) 공통 플레이스홀더 이미지로 교체 (`img.onerror`, 권장)

B) 색상 블록 + 메뉴명 텍스트로 대체(이미지 없이 카드 유지)

C) 이미지 영역 자체를 숨기고 텍스트 카드로 표시

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11

현재 세션 **주문 내역 조회 화면** 진입 방식은?

A) 메뉴 화면 상단/하단의 "주문 내역" 탭·버튼으로 뷰 전환 (메뉴를 기본 화면으로 유지, 권장)

B) 장바구니 영역과 함께 별도 모달로 표시

C) 전용 화면으로 이동(뒤로 가기로 메뉴 복귀)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

**D. 관리자(F2) UX**

## Question 12

**신규 주문 도착 시 강조** 방식은? (요구사항: 색상 변경/애니메이션, SSE 2초 이내 반영)

A) 해당 테이블 카드 배경 하이라이트 후 수 초간 서서히 페이드 아웃 (권장)

B) 카드 테두리 깜빡임(펄스) 애니메이션 + "NEW" 배지

C) 강조 + 해당 카드를 그리드 최상단으로 정렬

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 13

관리자 **주문 상태 변경 UI** 는? (값: 대기중 / 준비중 / 완료)

A) 상태 버튼 3개 노출, 현재 상태 강조(원하는 상태 직접 선택) (권장)

B) 드롭다운(`select`)으로 상태 선택

C) "다음 단계로" 토글 버튼(대기중 → 준비중 → 완료 순차 전이)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14

**테이블별 필터** UI 는? (US-A2)

A) 드롭다운 단일 선택(전체 / 특정 테이블)

B) 테이블 번호 버튼(칩) 토글 — 다중 선택 가능 (권장)

C) "전체" + 개별 테이블 칩(단일 선택)

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 15

주문 삭제·세션 종료 등 **확인 팝업** 구현은?

A) 커스텀 모달 다이얼로그(디자인 일관 · 확인/취소) (권장)

B) 브라우저 native `confirm()` (구현 최소)

C) 카드 내 인라인 확인(한 번 더 누르면 확정)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 16

**과거 이력 조회**의 날짜 필터 UI 는? (US-A5, `date_from`/`date_to`)

A) from/to 날짜 입력 2개(`<input type="date">`)

B) 프리셋(오늘 / 어제 / 최근 7일) + 커스텀 범위 (권장)

C) 필터 없이 전체 로드 후 클라이언트에서 좁히기

D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

**E. 실시간 / 피드백 / 디바이스**

## Question 17

`sseClient` **재연결 정책**은? (연결 끊김 시)

A) 고정 간격(예: 3초) 재시도 (권장)

B) 지수 백오프(1s → 2s → 4s … 상한)

C) 1회 실패 시 자동 재시도 없이 "새로고침" 안내 배너 표시

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 18

**에러/성공 피드백** 표시 방식은? (주문 실패, 저장 성공 등)

A) 토스트(스낵바) 알림 — 일정 시간 후 자동 소멸 (권장)

B) 화면 내 인라인 메시지 영역

C) 브라우저 `alert()` (구현 최소)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 19

**대상 화면/반응형** 범위는?

A) 고객 = 태블릿 가로 기준 고정 레이아웃, 관리자 = 데스크톱 기준 (MVP 단순화, 권장)

B) 고객·관리자 모두 반응형(모바일 ~ 데스크톱 유연)

C) 데스크톱 우선 + 태블릿 최소 대응

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 20

`apiClient` 호출 중 **토큰 만료(401)** 응답 처리는?

A) 관리자 = 즉시 로그인 화면 전환 / 고객 태블릿 = 저장된 자격으로 `tablet_login` 재발급 1회 시도 후 실패 시 안내 (권장)

B) 401 이면 무조건 로그인 화면으로 전환(고객·관리자 공통)

C) 에러 메시지만 표시하고 사용자가 수동 조치

D) Other (please describe after [Answer]: tag below)

[Answer]: D — 401 발생 시 관리자 토큰은 삭제하고 로그인 화면으로 전환한다. 고객 태블릿은 만료된 tablet_token을 삭제하고 최초 인증/재인증 화면으로 전환한다. 저장된 store_id/table_no는 입력 편의를 위해 사용할 수 있지만 table_password를 localStorage에 새로 저장하거나 자동 재로그인을 시도하지 않는다.
