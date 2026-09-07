# Unit of Work Plan (유닛 분해 계획) — 3인 개정판

> 이 단계는 시스템을 **개발 작업 단위(Unit of Work)** 로 분해합니다.
> 목표: 반나절 실습에서 **3명이 병렬로 Construction**을 경험할 수 있도록, Application Design의 8개 컴포넌트와
> 12개 승인 스토리를 **명확한 경계·owner·의존·provided/consumed interface**를 가진 최소 유닛으로 묶는 것.
>
> **이 단계의 범위(중요)**: 유닛 **경계 / owner / dependency / provided·consumed interface** 까지만 정의합니다.
> Integration Contract의 **실제 API·schema·event 상세 계약**은 이 계획을 사람이 승인한 뒤 **별도 단계에서** 작성합니다.
> 이 단계에서는 제품 코드나 상세 계약을 생성하지 않습니다. (요청사항 6 반영)
>
> **아래 질문의 `[Answer]:` 태그에 직접 답을 적어 주세요.** 첫 번째 옵션이 권장안입니다.
> 답변을 모두 채운 뒤 "완료"라고 알려 주시면 계획을 확정하고 유닛 산출물을 생성합니다.

---

## 배경 요약 (결정에 참고)
- **팀**: **3명**(요청자 포함). 반나절. → handoff가 많은 6-유닛 구조 대신, **1인 1유닛**으로 책임이 명확한 최소 구성 우선.
- **런타임 형태**: 로컬 단일 프로세스 FastAPI 앱(단일 실행). 독립 배포 서비스로 쪼갤 이유 없음 → **모듈형 모놀리스**.
- **컴포넌트(8)**: C0 Persistence, C1 Auth, C2 Menu, C3 Order(허브), C4 TableSession, C5 OrderHistory, C7 Realtime + 프론트 F1 Customer / F2 Admin / F3 Shared JS.
- **핵심 vertical slice**: 메뉴 조회 → 장바구니 → 주문 생성 → 관리자 주문 확인(SSE) → 주문 상태 변경. (3인 결과 통합 시 완성되어야 함 — 요청사항 5)

### 검증된 Story ↔ Component 매핑 (승인본 stories.md 재확인)
> ⚠️ 이전 초안의 오류 수정: **US-A5는 "이용 세션/과거 이력"** 스토리이며 메뉴가 아님. **메뉴 관리 스토리는 US-A7**.

| Story | 내용 | 주요 Component |
|---|---|---|
| US-C1 | 태블릿 자동 로그인 | C1 Auth (+F1/F3 저장) |
| US-C2 ⭐ | 메뉴 조회/탐색 | C2 Menu (+F1) |
| US-C3 ⭐ | 장바구니 관리 | F1(localStorage) (+F3) |
| US-C4 ⭐ | 주문 생성 | C3 Order (+C4/C7, F1) |
| US-C5 | 현재 세션 주문 내역 | C3 Order (+C4, F1) |
| US-A1 | 관리자 인증/세션 | C1 Auth (+F2) |
| US-A2 ⭐ | 실시간 주문 모니터링(SSE) | C7 Realtime + C3 (+F2/F3) |
| US-A3 ⭐ | 주문 상태 변경 | C3 Order (+F2) |
| US-A4 | 주문 삭제(직권) | C3 Order + C4(총액 재계산) (+F2) |
| US-A5 | 이용 세션 시작/종료·과거 이력 | C4 TableSession + C5 OrderHistory (+F2) |
| US-A6 | 태블릿 초기 설정(인증/자동로그인 세션) | C4(setup_table) + C1 Auth (+F2) |
| US-A7 | 메뉴 관리(CRUD/정렬) | C2 Menu (+F2) |

---

## 권장 유닛 구성 (3인 · 1인 1유닛)

핵심 원칙:
- **1인 1유닛** — 각자 하나의 응집된 유닛을 온전히 소유(작은 유닛 사이를 오가지 않음). (요청사항 1)
- **Shared 영역 single-writer** — 여러 유닛이 동시에 소유하지 않도록 owner를 **정확히 1개** 지정. (요청사항 3)
- **주문 파이프라인 협력 컴포넌트는 같은 유닛**에 두어 백엔드 내부 handoff 최소화.

| 유닛 | Owner | 포함 컴포넌트 | 담당 Story |
|---|---|---|---|
| **U1 — Foundation · Auth · Menu** | 1인 | C0 Persistence, C1 Auth, C2 Menu | US-C2(메뉴 API), US-A7, US-C1(인증측), US-A1, US-A6(인증/토큰측) |
| **U2 — Order Pipeline · Session · Realtime** | 1인 | C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime | US-C4, US-C5, US-A3, US-A4, US-A5, US-A6(테이블 setup측), US-A2(SSE 백엔드) |
| **U3 — Frontend (Customer · Admin · Shared JS)** | 1인 | F1 CustomerApp, F2 AdminApp, **F3 Shared JS** | US-C1·C2·C3·C4·C5(고객 UI), US-A1~A7(관리자 UI), US-A2(대시보드 UI) |

### Shared 영역 single-writer 지정 (요청사항 3)
| Shared 영역 | 단일 Owner |
|---|---|
| DB schema / migration / `seed_if_empty` 초기화 | **U1** |
| 공용 schema/type (공통 베이스 모델·응답 포맷) | **U1** |
| Application entrypoint (FastAPI app, static mount, startup DB init) | **U1** |
| dependency / lock 파일 (backend requirements/pyproject + lock) | **U1** |
| **Shared JS (F3: apiClient, sseClient, 포맷 유틸)** | **U3** |

- **F3는 U3만 소유**합니다. Customer FE와 Admin FE가 **동시에 F3를 쓰지만 쓰기(owner)는 U3 하나**입니다. Admin은 F3를 consumed interface로 사용할 뿐 수정하지 않습니다. (요청사항 3 핵심)
- 프론트는 vanilla JS(빌드 없음)이라 별도 lock 파일이 없습니다. backend 의존성/lock만 U1이 단독 소유.
- **event payload contract**(order.created 등)는 Realtime을 소유한 **U2**가 정의·제공(provided). U1의 "공용 type"은 공통 베이스에 한정하며 도메인/이벤트 스키마와 충돌하지 않습니다.

### Seed / Sample Data 책임 (요청사항 4)
- **U1(C0 Persistence)** 이 자동 seed 요구사항의 **정의·준비·`seed_if_empty` 구현**을 단독 책임합니다. 대상: **샘플 매장 · 관리자 계정 · 카테고리 · 샘플 메뉴 · 테이블**.
- 별도 기능 유닛을 새로 만들지 않습니다. 실제 샘플 데이터 **내용 작성/수집은 U1의 Construction**에서 수행(이 단계에서는 책임만 명시).

### 핵심 vertical slice 통합 관점 (요청사항 5)
메뉴 조회(U1 API + U3 UI) → 장바구니(U3) → 주문 생성(U2 + U3) → 관리자 주문 확인 SSE(U2 + U3) → 상태 변경(U2 + U3).
→ 3개 유닛 결과를 통합해야 슬라이스가 완성됨. U1 계약이 먼저 안정화되면 U2·U3가 병렬 진행 가능.

---

## 결정 질문 (Decision Questions)

### Q1. 배포/유닛 모델
**분류: Technical Considerations**
A. **모듈형 모놀리스 (권장)** — 단일 FastAPI 앱 안에서 유닛을 논리 모듈로 분리(로컬 단일 실행·반나절 MVP 적합).
B. 유닛별 독립 서비스(별도 프로세스/배포).
C. 기타

[Answer]: A — 로컬 단일 실행과 반나절 MVP에 맞게 모듈형 모놀리스로 유지합니다.

---

### Q2. 유닛 개수/구성 — 3인 병렬 구성
**분류: Team Alignment / Story Grouping**
A. **위 표의 3개 유닛 (권장)** — U1 Foundation·Auth·Menu / U2 Order·Session·Realtime / U3 Frontend(전체). 1인 1유닛, handoff 최소.
B. 4개 유닛 — U3를 Customer FE / Admin FE로 분리(단, 이 경우 F3 owner를 한쪽으로 명시 지정 필요, 한 명이 2개 유닛을 겸함).
C. 2개 유닛 — Backend 전체 / Frontend 전체(3인에는 backend 부하가 큼).
D. 기타(직접 구성 제시)

[Answer]: A — 현재 3명이 각각 하나의 명확한 책임 영역을 소유하고 handoff를 최소화하기에 적절합니다.

---

### Q3. 유닛 분해 축
**분류: Business Domain / Story Grouping**
A. **백엔드는 도메인 클러스터 + 프론트는 단일 유닛 (권장)** — 백엔드를 Foundation/Auth/Menu(U1) 와 Order/Session/Realtime(U2)로, 프론트 전체를 U3로. (F3 single-writer 확보에 유리)
B. 순수 사용자 유형 기준 — Customer 전체 / Admin 전체(풀스택 수직).
C. 계층 기준(Router/Service/Repository 수평 분할).
D. 기타

[Answer]: A — 백엔드 도메인 경계를 유지하면서 프론트 shared 영역의 single-writer도 명확하게 할 수 있습니다.

---

### Q4. 선행(Foundation) 안정화 순서
**분류: Dependencies**
A. **U1 먼저 안정화 (권장)** — DB 스키마 + 공용 type + Auth verify + Menu API 계약을 먼저 확정하고, U2·U3는 그 계약 기준으로 병렬 진행. (통합 리스크 최소)
B. 세 유닛 동시 착수, 계약은 진행하며 조정.
C. 기타

[Answer]: C — U1 구현 완료를 다른 Unit의 선행 조건으로 두지는 않습니다. Units Plan 승인 후 별도 Integration Contract 단계에서 DB schema, 공용 type, REST/SSE API, event payload 등 병렬 개발에 필요한 공통 계약을 먼저 팀이 확정합니다. 그 계약이 승인된 뒤 U1/U2/U3가 동시에 Construction을 시작합니다. U1은 DB schema, seed, entrypoint 등 지정된 shared 파일의 single-writer 역할을 유지합니다.

---

### Q5. F3 Shared JS single-writer owner
**분류: Dependencies / Team Alignment**
A. **U3 (Frontend 단일 유닛)이 F3 소유 (권장)** — 프론트가 한 유닛이므로 F3(apiClient/sseClient)를 자연히 단독 소유. Customer·Admin은 같은 유닛 내에서 사용.
B. Q2에서 프론트를 2개 유닛으로 나눌 경우: **Customer FE 유닛이 F3 소유**, Admin은 consumed.
C. Q2에서 프론트를 2개 유닛으로 나눌 경우: **Admin FE 유닛이 F3 소유**(sseClient가 관리자 핵심), Customer는 consumed.
D. 기타

[Answer]: A — F3 Shared JS는 U3가 단독 소유하여 Customer/Admin 간 공용 프론트 코드의 동시 수정을 방지합니다.

---

### Q6. 코드 조직/디렉터리 구조 (Greenfield)
**분류: Code Organization**
A. **단일 리포 + 도메인별 모듈 디렉터리 (권장)** — `backend/app/{persistence,auth,menu,order,table_session,order_history,realtime}/`(각 router/service/repository) + `frontend/{customer,admin,shared}/` 정적 파일. 단일 FastAPI 앱이 API·정적 파일을 함께 서빙(entrypoint는 U1 단독 소유).
B. 계층별 디렉터리(`routers/`, `services/`, `repositories/` 최상위 분리).
C. 기타

[Answer]: A — Application Design의 도메인 경계와 일치하고 Unit별 owned path를 명확히 구분하기 쉽습니다.

---

## 계획 실행 체크리스트 (Part 2에서 수행)
- [x] `aidlc-docs/inception/application-design/unit-of-work.md` 생성 (유닛 정의·책임 + Shared single-writer owner + Seed 책임 + Greenfield 코드 조직 전략)
- [x] `aidlc-docs/inception/application-design/unit-of-work-dependency.md` 생성 (유닛 의존성 매트릭스 + provided/consumed interface 개요, 상세 계약은 별도 단계)
- [x] `aidlc-docs/inception/application-design/unit-of-work-story-map.md` 생성 (스토리 → 유닛 매핑, 12개 스토리 전부 배정 및 spanning 표기)
- [x] 유닛 경계·의존성 검증 (순환 의존 없음)
- [x] 모든 스토리가 유닛에 배정되었는지 검증
- [x] Shared 영역 single-writer owner가 각 1개인지 검증 (특히 F3)

---

## 승인
질문에 답한 뒤 **"완료"** 라고 알려 주세요. 답변에 모호함이 없으면 위 체크리스트를 실행해 유닛 산출물을 생성합니다.
(이 단계에서는 제품 코드·상세 Integration Contract를 생성하지 않습니다.)
