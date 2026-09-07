# User Stories 생성 계획 (Story Generation Plan)

> **상태: 답변 완료 & 승인 대기 → Part 2 생성 완료** — 결론: `D / A / A / A / A`

## A. 방법론 / 접근 (Methodology)
product owner 관점에서 요구사항(`requirements.md`)을 사용자 중심 스토리로 변환.
- INVEST 원칙 준수, 각 스토리에 인수 조건 포함, 페르소나 매핑
- 반나절 실습 범위에 맞게 핵심 흐름 스토리 우선, 과도한 세분화 지양

## B. 실행 체크리스트 (Part 2)
- [x] `personas.md` 생성 — 사용자 아키타입과 특성
- [x] `stories.md` 생성 — INVEST 기반 사용자 스토리
- [x] 각 스토리에 인수 조건(Given/When/Then) 포함
- [x] 각 스토리를 관련 페르소나에 매핑
- [x] 핵심 우선 흐름 스토리를 우선순위로 표시
- [x] 스토리를 요구사항 FR-ID와 트레이스 연결

## C. 명확화 질문 (답변 반영)

### Question 1 — 스토리 구성(Breakdown) 방식
[Answer]: **D** — 하이브리드(페르소나로 크게 나누고 그 안에서 여정 순서로 정렬). Customer/Admin 경계를 유지하면서 핵심 주문 흐름 순서까지 쉽게 확인.

### Question 2 — 인수 조건 형식
[Answer]: **A** — Given/When/Then(Gherkin). 이후 API/통합 테스트와 핵심 흐름 검증에 직접 활용.

### Question 3 — 스토리 세분화 수준
[Answer]: **A** — 기능 단위의 중간 크기 스토리. 추적 가능성 유지 + 과도한 분할 회피.

### Question 4 — 페르소나 범위
[Answer]: **A** — 2개(고객 + 매장 관리자). 요구사항의 주요 사용자 유형과 일치.

### Question 5 — 범위 확인
[Answer]: **A** — MVP 핵심 기능(요구사항 4장 + 3장 관리자 기능)에 집중, constraints 제외 항목은 스토리화하지 않음.
