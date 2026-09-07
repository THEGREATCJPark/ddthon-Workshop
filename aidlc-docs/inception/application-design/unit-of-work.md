# Unit of Work (유닛 정의 · 책임 · Owner)

> 배포 모델: **모듈형 모놀리스**(단일 FastAPI 앱, 로컬 단일 실행) — Q1=A.
> 분해 축: **백엔드 도메인 클러스터 + 프론트 단일 유닛** — Q3=A.
> 팀: **3명 · 1인 1유닛** — Q2=A.
> 이 문서는 유닛의 **경계 / owner / 책임 / provided·consumed interface 개요**만 정의한다.
> **상세 API·schema·event 계약과 제품 코드는 이 계획 승인 후 별도 Integration Contract 단계에서 작성**한다 (Q4=C).

---

## 유닛 개요

| 유닛 | Owner(1인) | 포함 컴포넌트 | 한 줄 책임 |
|---|---|---|---|
| **U1 — Foundation · Auth · Menu** | 담당자 1 | C0 Persistence, C1 Auth, C2 Menu | 데이터/시드 기반, 인증, 메뉴 도메인 + 지정 shared 파일 single-writer |
| **U2 — Order Pipeline · Session · Realtime** | 담당자 2 | C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime | 주문 파이프라인·세션 라이프사이클·실시간(SSE) |
| **U3 — Frontend** | 담당자 3 | F1 CustomerApp, F2 AdminApp, F3 Shared JS | 고객/관리자 UI + 공용 JS(F3 단독 소유) |

### 통합 역할 (Integration Lead)
유닛 오너십과 **별개의 역할**로 **Integration Lead**를 둔다. 이 역할은 특정 도메인 유닛에 속하지 않는 **composition root / 통합 계약**의 single-writer다.
- **owns (single-writer)**: `backend/app/main.py`(composition root — 라우터 등록·static mount·startup 조립), `INTEGRATION_CONTRACT.md`(REST/SSE API·공용 type·event payload의 authoritative 계약 문서).
- 실제로 Integration Lead가 **U1 담당자와 동일인일 수 있으나 ownership 역할은 구분**한다(도메인 유닛 owned path와 composition root/계약을 분리).
- 각 유닛은 **자신의 router/static artifact만 제공**하고 `main.py`를 직접 수정하지 않는다. main.py는 각 유닛이 제공한 artifact를 조립만 한다 → 도메인 유닛이 서로/entrypoint를 통해 순환 의존하지 않는다.

---

## U1 — Foundation · Auth · Menu

**책임 컴포넌트**: C0 Persistence, C1 Auth, C2 Menu

**핵심 책임**
- **C0 Persistence**: SQLite 연결/세션, 스키마 초기화, 트랜잭션, Repository 공통 기반.
- **Seed / Sample Data (단독 owner)**: `seed_if_empty` 구현 및 **샘플 데이터 정의·준비** — 샘플 매장 · 관리자 계정(bcrypt) · 카테고리 · 샘플 메뉴 · 테이블. *(실제 데이터 내용 작성/수집은 U1 Construction에서 수행. 별도 기능 유닛 없음.)*
- **C1 Auth**: 관리자 로그인(JWT 16h, bcrypt, 시도 제한), 태블릿 인증 토큰 발급/검증, `verify_admin_token`/`verify_tablet_token` 의존성(TabletContext/AdminContext 제공).
- **C2 Menu**: 메뉴/카테고리 조회·CRUD·노출 순서·검증.

**담당 Story**: US-C2(메뉴 API), US-A7(메뉴 관리), US-A1(관리자 인증), US-C1(태블릿 인증측), US-A6(태블릿 인증/토큰 발급측).

**Shared single-writer 책임 (U1 단독)**
- DB schema / migration / `seed_if_empty` 초기화
- 공용 schema/type 구현 모듈 (공통 베이스 모델·표준 응답/에러 포맷) *— 계약 문서(INTEGRATION_CONTRACT.md)는 Integration Lead가 소유*
- backend **dependency / lock** 파일 (requirements/pyproject + lock)
- *(참고) Application entrypoint(`main.py`)는 U1이 아니라 **Integration Lead**가 소유하는 composition root다. U1은 자신의 router artifact만 제공한다.*

**Provided interface (개요)**: DB/Repository 기반, Auth 검증 의존성(TabletContext/AdminContext), Menu 조회/관리 API, 공용 type, 시드된 초기 데이터.
**Consumed interface (개요)**: 없음(기반 유닛).

---

## U2 — Order Pipeline · Session · Realtime

**책임 컴포넌트**: C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime

**핵심 책임**
- **C3 Order**: 주문 생성(식별정보는 TabletContext가 Source of Truth), 현재 세션 주문 조회, 상태 변경(대기중/준비중/완료), 직권 삭제.
- **C4 TableSession**: 테이블 setup(`setup_table`), 이용(주문) 세션 시작/종료, 총액 집계, 세션 종료 시 이력 이동 트리거.
- **C5 OrderHistory**: 세션 주문 아카이빙, 과거 이력 조회·날짜 필터.
- **C7 Realtime**: 인프로세스 pub/sub 브로커 + SSE 스트림. **event provider / implementation owner** — 이벤트(`order.created`, `order.status_changed`, `order.deleted`, `table_session.ended`)를 발행·구현한다. *(event payload schema의 authoritative 계약은 Integration Lead의 `INTEGRATION_CONTRACT.md`에 있으며, U2는 스키마 변경이 필요하면 **Contract Change Request**를 제출한다.)*

**담당 Story**: US-C4(주문 생성), US-C5(현재 세션 조회), US-A2(SSE 실시간 모니터링·백엔드), US-A3(상태 변경), US-A4(삭제), US-A5(세션/이력), US-A6(테이블 setup측).

**Provided interface (개요)**: 주문 API(생성/조회/상태/삭제), 세션·이력 API, SSE 스트림 endpoint + 이벤트 발행(provider). *이벤트 payload schema는 Integration Lead의 계약 문서를 따르며, 변경은 Contract Change Request로 요청.*
**Consumed interface (개요)**: U1 — Persistence/Repository 기반, `verify_tablet_token`/`verify_admin_token`(TabletContext/AdminContext), Menu 단가 조회, 공용 type.

---

## U3 — Frontend (Customer · Admin · Shared JS)

**책임 컴포넌트**: F1 CustomerApp(`/`), F2 AdminApp(`/admin`), **F3 Shared JS**

**핵심 책임**
- **F1 CustomerApp**: 자동 로그인, 메뉴 조회/탐색, 장바구니(localStorage), 주문 생성 플로우, 현재 세션 주문 내역.
- **F2 AdminApp**: 관리자 로그인, SSE 실시간 대시보드(테이블 그리드/강조/필터), 주문 상세, 상태 변경/삭제, 세션 종료·과거 이력, 메뉴 관리 UI.
- **F3 Shared JS (U3 단독 소유)**: `apiClient`(Bearer 자동 첨부), `sseClient`(fetch 기반 text/event-stream 스트리밍 리더), 포맷 유틸. **Customer·Admin이 함께 사용하지만 쓰기(owner)는 U3 하나** — 동시 수정 방지.

**담당 Story**: 고객 UI(US-C1~C5), 관리자 UI(US-A1~A7, US-A2 대시보드 포함).

**Provided interface (개요)**: 정적 서빙되는 고객/관리자 UI.
**Consumed interface (개요)**: U1 — 인증/메뉴 API; U2 — 주문/세션/이력 API + SSE 스트림 + 이벤트 페이로드 계약.

---

## Shared 영역 Single-Writer 요약 (요청사항 3)

| Shared 영역 | 단독 Owner |
|---|---|
| DB schema / migration / `seed_if_empty` | **U1** |
| 공용 schema/type 구현 모듈 (공통 베이스) | **U1** |
| dependency / lock (backend) | **U1** |
| **F3 Shared JS (apiClient, sseClient, 포맷)** | **U3** |
| **Application entrypoint (`main.py`, composition root)** | **Integration Lead** |
| **`INTEGRATION_CONTRACT.md` (REST/SSE API · 공용 type · event payload 계약)** | **Integration Lead** |

- **event contract 역할 구분**: **U2 = event provider / implementation owner**; **Integration Lead = `INTEGRATION_CONTRACT.md`의 authoritative single-writer**; U2는 event schema 변경 필요 시 **Contract Change Request**를 제출한다. (event payload 상세는 Units 승인 후 Integration Contract 단계에서 확정)
- **entrypoint 역할 구분**: `main.py`는 도메인 유닛 owned path가 아니라 **Integration Lead가 single-writer로 관리하는 shared composition root**다. Integration Lead가 U1 담당자와 동일인일 수 있으나 ownership 역할은 분리한다. 각 유닛은 자신의 router/static artifact만 제공한다.
- 프론트는 vanilla JS(빌드 없음)로 별도 lock 파일이 없다.

---

## Seed / Sample Data 책임 (요청사항 4)
- **U1(C0 Persistence)** 이 `seed_if_empty` 구현 및 다음 샘플 데이터의 **정의·준비**를 단독 책임: 샘플 매장 · 관리자 계정 · 카테고리 · 샘플 메뉴 · 테이블.
- 실제 데이터 **내용은 U1 Construction 단계**에서 작성. 별도 유닛/기능을 신설하지 않는다.

---

## 코드 조직 전략 (Greenfield, Q6=A)

단일 리포 + 유닛별 owned path 분리:

```text
table-order/
├── backend/
│   ├── app/
│   │   ├── main.py                 # composition root (Integration Lead owns: 라우터 등록/static mount/startup 조립)
│   │   ├── common/                 # 공용 schema/type 구현 모듈 (U1 owns)
│   │   ├── persistence/            # C0 (U1)
│   │   ├── auth/                    # C1 (U1)
│   │   ├── menu/                    # C2 (U1)
│   │   ├── order/                   # C3 (U2)
│   │   ├── table_session/           # C4 (U2)
│   │   ├── order_history/           # C5 (U2)
│   │   └── realtime/                # C7 (U2)
│   ├── requirements.txt / lock      # deps/lock (U1 owns)
│   └── seed/                        # sample data 정의 (U1 owns)
├── frontend/                        # U3 owns 전체
│   ├── customer/                    # F1
│   ├── admin/                       # F2
│   └── shared/                      # F3 (U3 단독)
└── (실행: 단일 명령으로 FastAPI 앱 기동, static + API 동시 서빙)
```

- 각 도메인 디렉터리는 내부에 router/service/repository 하위 구조(3계층)를 가진다.
- **owned path 경계**: U1=`persistence,auth,menu,common,requirements,seed`; U2=`order,table_session,order_history,realtime`; U3=`frontend/*`; **Integration Lead=`main.py`(composition root), `INTEGRATION_CONTRACT.md`**. 유닛 간 파일 쓰기 겹침 없음(각 유닛은 자신의 router artifact만 제공, main.py는 조립만).

---

## 개발 순서 / 병렬화 (Q4=C)

1. **(이 계획 승인 후) 별도 Integration Contract 단계** — **Integration Lead**가 `INTEGRATION_CONTRACT.md`(DB schema, 공용 type, REST/SSE API, event payload)를 single-writer로 확정하고 팀이 승인한다. *(U1 구현 완료를 다른 유닛의 선행 조건으로 두지 않는다.)*
2. 계약 승인 후 **U1 · U2 · U3가 동시에 Construction 시작**(병렬).
3. U1은 계약과 무관하게 **지정된 shared 파일(DB schema, seed, 공용 type 구현 모듈, deps/lock)의 single-writer 역할**을 유지하고, Integration Lead는 **`main.py`(composition root)와 계약 문서**의 single-writer 역할을 유지한다. event schema 변경은 U2의 Contract Change Request → Integration Lead 반영으로 처리한다.
4. 통합 시 핵심 vertical slice(메뉴 조회 → 장바구니 → 주문 생성 → 관리자 SSE 확인 → 상태 변경)가 완성되는지 검증.
