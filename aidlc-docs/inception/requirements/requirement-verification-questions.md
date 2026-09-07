# 요구사항 확인 질문 (Requirements Verification Questions)

> **상태: 답변 완료 (2026-09-07)** — 결론 요약: `A / A / A / A / A / A / B / B / C`

아래 질문에 각 `[Answer]:` 태그 뒤에 **선택지 문자(A, B, C ...)** 를 입력해 답변해 주세요.

> 참고: 기능 요구사항(`table-order-requirements.md`)과 제외사항(`constraints.md`)은 **변경/삭제하지 않습니다.**

---

## Question 1
백엔드(서버)는 어떤 언어/프레임워크로 구현할까요?

A) Python + FastAPI (경량, SSE·JWT 구현 간단 — 반나절 실습에 권장)

B) Node.js + Express

C) Java + Spring Boot

D) Other (please describe after [Answer]: tag below)

[Answer]: A — SSE·JWT를 포함한 백엔드 요구사항을 반나절 내 구현하기에 가장 단순한 구성이므로 선택합니다.

---

## Question 2
고객용/관리자용 프론트엔드는 어떤 방식으로 구현할까요?

A) 순수 HTML + CSS + Vanilla JavaScript (빌드 도구 없이 서버가 정적 파일로 제공 — 반나절 실습에 권장)

B) React (Vite 등 빌드 도구 사용)

C) 서버 사이드 템플릿 (Jinja2 등)

D) Other (please describe after [Answer]: tag below)

[Answer]: A — 별도 프론트엔드 빌드 환경 없이 고객/관리자 핵심 흐름 구현과 통합에 집중하기 위해 선택합니다.

---

## Question 3
데이터 저장소는 무엇을 사용할까요? (매장/메뉴/주문/과거이력/세션 저장)

A) SQLite (파일 기반, 설치 불필요, 재시작해도 데이터 유지 — 반나절 실습에 권장)

B) In-memory (프로세스 메모리, 재시작 시 초기화 — 가장 빠르지만 데이터 휘발)

C) PostgreSQL 등 별도 DB 서버 (Docker 등 추가 설정 필요)

D) Other (please describe after [Answer]: tag below)

[Answer]: A — 별도 DB 인프라 없이 데이터 영속성을 확보하고 Build/Test와 데모를 반복하기 쉽기 때문입니다.

---

## Question 4
관리자 실시간 주문 모니터링(요구사항 3.2.2)은 SSE(Server-Sent Events)로 명시되어 있습니다. MVP에서 실시간 반영 방식을 어떻게 구현할까요?

A) 요구사항대로 SSE 구현 (신규 주문/상태 변경을 서버가 푸시, 2초 이내 반영 — 권장)

B) SSE 대신 짧은 주기 폴링(polling)으로 우선 구현하고, 시간이 남으면 SSE로 교체

C) Other (please describe after [Answer]: tag below)

[Answer]: A — SSE는 승인된 기능 요구사항에 명시된 방식이므로 구현 편의를 위해 polling으로 변경하지 않습니다.

---

## Question 5
실습 시작 시 바로 데모할 수 있도록 초기 시드(seed) 데이터를 자동 생성할까요?

A) 예 — 샘플 매장 1개 + 관리자 계정 + 카테고리별 샘플 메뉴 + 테이블 몇 개를 자동 시드 (데모/실습에 권장)

B) 아니오 — 빈 상태로 시작하고 관리자 화면에서 직접 등록

C) Other (please describe after [Answer]: tag below)

[Answer]: A — 초기 설정 작업을 줄이고 핵심 주문 Happy Path와 최종 데모를 즉시 검증할 수 있도록 합니다.

---

## Question 6
실행/배포 대상 범위는 어디까지 볼까요? (반나절 시간 제약 반영)

A) 로컬 실행만 (한 명령으로 서버 기동 후 브라우저 접속) — 클라우드/컨테이너 배포는 이번 범위에서 제외 (권장)

B) Docker Compose로 로컬 컨테이너 실행까지

C) 클라우드(AWS 등) 배포까지 포함

D) Other (please describe after [Answer]: tag below)

[Answer]: A — 이번 실습은 배포보다 Inception부터 Construction, 통합, Build/Test까지 완주하는 것이 우선입니다.

---

## Question 7: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — 모든 SECURITY 규칙을 blocking 제약으로 강제

B) No — SECURITY 규칙 전체 생략. 단, 요구사항의 bcrypt 해싱·JWT 등 명시된 보안 요건은 그대로 구현

X) Other (please describe after [Answer]: tag below)

[Answer]: B — production-grade 보안 확장은 생략하되 requirements에 명시된 JWT·bcrypt 등 보안 기능은 그대로 구현합니다.

---

## Question 8: Resiliency Extensions
Should the resiliency baseline be applied to this project?

A) Yes — 복원력 베이스라인을 설계 지침으로 적용

B) No — 복원력 베이스라인 생략

X) Other (please describe after [Answer]: tag below)

[Answer]: B — 반나절 로컬 MVP에 HA·복구성·복잡한 관측성까지 확대하지 않고 핵심 사용자 흐름 구현을 우선합니다.

---

## Question 9: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — 모든 PBT 규칙을 blocking 제약으로 강제

B) Partial — 순수 함수와 직렬화 round-trip 에 대해서만 PBT 적용

C) No — PBT 규칙 전체 생략

X) Other (please describe after [Answer]: tag below)

[Answer]: C — 테스트 개수나 고급 테스트 기법보다 핵심 business flow, API/Contract, Build/Test 검증을 우선합니다.
