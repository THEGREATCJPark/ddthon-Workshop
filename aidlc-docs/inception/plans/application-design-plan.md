# Application Design 계획 (Application Design Plan)

> Part 1(계획) 문서입니다. 아래 **설계 결정 질문**에 답변해 주시면, 승인 후 컴포넌트/메서드/서비스/의존성 설계 산출물을 생성합니다.
> 각 `[Answer]:` 태그 뒤에 선택지 문자를 입력하고, 마치면 "완료"라고 알려주세요.
>
> 범위 참고: 상위 수준 컴포넌트 식별과 서비스 계층 설계까지. 상세 비즈니스 로직/데이터 검증은 이후 Functional Design(유닛별)에서 다룹니다.

> **상태: 답변 완료** — 결론: `A / A / A / A / A`

## A. 실행 체크리스트 (승인 후 생성)
- [x] `components.md` — 컴포넌트 정의·책임·인터페이스
- [x] `component-methods.md` — 컴포넌트별 메서드 시그니처(상위 목적, 입출력 타입)
- [x] `services.md` — 서비스 정의·책임·오케스트레이션
- [x] `component-dependency.md` — 의존성 매트릭스·통신 패턴·데이터 흐름
- [x] `application-design.md` — 위 문서 통합본
- [x] 설계 완전성/일관성 검증

## 답변 요약
- Q1=A 3계층(Router→Service→Repository)+SQLite
- Q2=A 도메인별 모듈(Auth, Menu, Order, TableSession, OrderHistory, Realtime)
- Q3=A 인프로세스 이벤트 브로커(in-memory pub/sub) + FastAPI SSE
- Q4=A JWT 응답 본문 발급 + Authorization: Bearer 헤더
- Q5=A FastAPI 정적 서빙 2페이지(`/` 고객, `/admin` 관리자) + 공통 JS 유틸

## B. 설계 결정 질문 (Clarifying Questions)

### Question 1 — 백엔드 계층 구조(아키텍처 스타일)
FastAPI 백엔드를 어떤 계층 구조로 설계할까요?

A) 3계층 (Router/API → Service → Repository) + SQLite. 관심사 분리 명확, 테스트 용이 — 반나절에도 적정, 권장

B) 2계층 (Router → DB 직접 접근). 가장 단순하지만 로직/데이터 접근이 섞임

C) 도메인 주도(DDD)식 세분화 계층. 견고하지만 반나절엔 과함

D) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 2 — 컴포넌트(모듈) 경계
백엔드 도메인 컴포넌트를 어떻게 나눌까요?

A) 도메인별 모듈: Auth(관리자 인증), Menu, Cart(클라이언트 위주라 서버는 최소), Order, TableSession, OrderHistory, Realtime(SSE). 병렬 작업 분할에 유리 — 권장

B) 사용자 유형별 모듈: Customer 모듈 / Admin 모듈 2개로 크게 분리

C) 단일 모듈(모놀리식 한 덩어리)

D) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 3 — 실시간(SSE) 전달 메커니즘
관리자 대시보드 SSE 실시간 반영을 어떤 방식으로 설계할까요?

A) 인프로세스 이벤트 브로커(in-memory pub/sub) + FastAPI SSE 스트리밍. 주문 생성/상태변경/삭제 시 이벤트 발행 → 구독 중인 관리자에게 푸시. 단일 프로세스 로컬 실행에 적합 — 권장

B) 관리자 클라이언트가 주기적으로 조회하는 방식(폴링)으로 SSE를 흉내

C) 외부 메시지 브로커(Redis Pub/Sub 등) 사용

D) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 4 — 인증 토큰/세션 전달 방식
관리자 JWT(16시간)와 태블릿 인증을 클라이언트에 어떻게 전달·보관할까요?

A) JWT를 응답 본문으로 발급하고 클라이언트가 저장 후 Authorization: Bearer 헤더로 전송 — 구현 단순, 권장

B) HttpOnly 쿠키에 JWT 저장(자동 전송) — 조금 더 안전하나 CORS/설정 부가

C) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 5 — 프론트엔드 구성
고객/관리자 Vanilla JS 프론트엔드를 어떻게 구성할까요?

A) FastAPI가 정적 파일로 서빙하는 2개 페이지 앱: `/`(고객), `/admin`(관리자). 공통 JS 유틸(api client, SSE) 공유 — 권장

B) 완전히 분리된 2개 정적 사이트(별도 디렉터리, 중복 허용)

C) Other (please describe after [Answer]: tag below)

[Answer]: 
