# INTEGRATION CONTRACT — 테이블오더 MVP

> **Authoritative single-writer**: **Integration Lead**. 이 문서만 U1/U2/U3 병렬 Construction의 공통 계약 기준(Source of Truth for integration)이다.
> 이 문서는 **승인된 Requirements / User Stories / Application Design / Units Plan을 연결**하기 위한 계약이며, **새 요구사항을 추가하지 않는다**.
> 상세 비즈니스 규칙/검증은 각 Unit의 Functional Design에서 정의하되, **여기 명시된 경계·시그니처·계약을 위반하지 않는다**.
> 계약 변경은 아래 **§15 Contract Change Request** 절차로만 수행한다.

---

## 1. Contract Version / Baseline

| 항목 | 값 |
|---|---|
| Contract Version | **v0.2.0** (CCR-001: shared password hashing capability) |
| Baseline commit SHA | **1926164** (`chore(workshop): prepare AI-DLC v1.0.1`) |
| Status | **FROZEN (v0.2.0)** — CCR-001 승인 반영 (2026-09-07). DB schema/API/event 변경 없음 |
| Frozen at | 2026-09-07 (team-approved) |
| Derived from | requirements.md, stories.md, application-design/* , unit-of-work*.md |

> **FROZEN 규칙**: 이 시점부터 계약 변경은 **§15 Contract Change Request 절차로만** 가능하다. U1/U2/U3는 이 v0.1.0 계약을 고정 기준으로 병렬 Construction을 진행한다.

- 이 계약이 팀 승인되면 Status를 `FROZEN (v0.1.0)`으로 바꾸고, 그 시점 커밋 SHA를 baseline으로 고정한다.
- 이후 변경은 §15 절차로 minor(하위호환) / major(호환깨짐) 버전을 증가시킨다.

---

## 2. Units, Dependencies & Owned Paths

| 유닛/역할 | 포함 | Owned paths (single-writer) |
|---|---|---|
| **U1 — Foundation·Auth·Menu** | C0 Persistence, C1 Auth, C2 Menu | `backend/app/persistence/`, `backend/app/auth/`, `backend/app/menu/`, `backend/app/common/`, `backend/requirements.txt`(+lock), `backend/seed/` |
| **U2 — Order·Session·Realtime** | C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime | `backend/app/order/`, `backend/app/table_session/`, `backend/app/order_history/`, `backend/app/realtime/` |
| **U3 — Frontend** | F1 Customer, F2 Admin, F3 Shared JS | `frontend/customer/`, `frontend/admin/`, `frontend/shared/` |
| **Integration Lead** | composition root + 계약 | `backend/app/main.py`, `coordination/INTEGRATION_CONTRACT.md` |

**의존 방향 (순환 없음)**: `U2 → U1`, `U3 → U1`, `U3 → U2`. U1은 아무 유닛에도 의존하지 않음.
**entrypoint 규칙**: 각 유닛은 자신의 `router`(FastAPI `APIRouter`) / static artifact만 제공하고, `main.py`는 Integration Lead가 이를 **조립(include_router/mount)만** 한다. 도메인 유닛은 `main.py`를 수정하지 않는다.

---

## 3. Shared DB Schema & 주요 Entity

- **엔진**: SQLite(파일 기반, 영속). **Schema single-writer = U1 (C0)**.
- 아래는 통합에 필요한 **최소 계약 스키마**다. 컬럼 추가/변경은 §15 CCR로만.

```text
stores(
  id            INTEGER PK,
  name          TEXT NOT NULL
)

admin_users(
  id            INTEGER PK,
  store_id      INTEGER FK->stores.id,
  username      TEXT NOT NULL,
  password_hash TEXT NOT NULL,              -- bcrypt
  UNIQUE(store_id, username)
)

tables(                                     -- 테이블 config(초기 설정 결과)
  id            INTEGER PK,
  store_id      INTEGER FK->stores.id,
  table_no      INTEGER NOT NULL,
  password_hash TEXT NOT NULL,              -- bcrypt (태블릿 인증용)
  UNIQUE(store_id, table_no)
)

menus(
  id            INTEGER PK,
  store_id      INTEGER FK->stores.id,
  category      TEXT NOT NULL,
  name          TEXT NOT NULL,
  price         INTEGER NOT NULL,           -- 원 단위 정수
  description   TEXT,
  image_url     TEXT,
  display_order INTEGER NOT NULL DEFAULT 0
)

table_sessions(                             -- "이용(주문) 세션" 라이프사이클
  id            INTEGER PK,
  store_id      INTEGER FK->stores.id,
  table_no      INTEGER NOT NULL,
  status        TEXT NOT NULL,              -- 'ACTIVE' | 'ENDED'
  started_at    TEXT NOT NULL,             -- ISO 8601
  ended_at      TEXT                        -- ISO 8601, 종료 시
)

orders(
  id            INTEGER PK,
  store_id      INTEGER FK->stores.id,
  table_no      INTEGER NOT NULL,
  session_id    INTEGER FK->table_sessions.id,
  order_no      TEXT NOT NULL,              -- 표시용 주문 번호
  status        TEXT NOT NULL,              -- OrderStatus (§6)
  total         INTEGER NOT NULL,
  created_at    TEXT NOT NULL
)

order_items(
  id            INTEGER PK,
  order_id      INTEGER FK->orders.id,
  menu_id       INTEGER FK->menus.id,
  name          TEXT NOT NULL,              -- 주문 시점 스냅샷
  unit_price    INTEGER NOT NULL,           -- 주문 시점 스냅샷
  qty           INTEGER NOT NULL
)

order_history(                              -- 종료된 세션의 아카이브
  id            INTEGER PK,
  store_id      INTEGER,
  table_no      INTEGER,
  session_id    INTEGER,                    -- 그룹화 키
  order_no      TEXT,
  total         INTEGER,
  items_json    TEXT,                       -- 주문 항목 스냅샷(JSON)
  ordered_at    TEXT,                        -- 원 주문 생성 시각(ISO 8601, archive 시 orders.created_at을 snapshot)
  completed_at  TEXT                         -- 이용 완료 시각(ISO 8601)
)
```

- **금액은 정수(원)** 로 통일한다(부동소수 금지).
- **timestamp는 ISO 8601 문자열(UTC)**.
- 아카이빙 시 `orders`/`order_items`의 해당 세션 레코드는 `order_history`로 이동/요약되고 현재 목록에서 제외된다(상세 이동 방식은 U2 Functional Design).

---

## 4. 공용 Type / Context (U1 `common/` 소유)

```text
AdminContext   = { store_id: int, admin_user_id: int, username: str }
TabletContext  = { store_id: int, table_no: int }

# 표준 응답 포맷
Success        = <endpoint별 body> (아래 §5)
ErrorResponse  = { "error": { "code": str, "message": str } }

# U1 Auth가 제공하는 bcrypt password hashing capability
app.auth.security.hash_password(plaintext: str) -> str
```

- **TabletContext는 고객 보호 API의 store_id/table_no에 대한 유일한 신뢰 출처(Source of Truth)**. 요청 body/query로 store/table 식별정보를 신뢰 입력으로 받지 않는다.
- 표준 에러 코드(최소): `UNAUTHORIZED`(401), `FORBIDDEN`(403), `NOT_FOUND`(404), `VALIDATION_ERROR`(422), `RATE_LIMITED`(429), `CONFLICT`(409).

---

## 5. REST API Endpoints

표기: **auth** = `none` | `tablet`(Bearer tablet_token) | `admin`(Bearer JWT). 식별정보 원칙(§4) 적용.

### 5.1 인증 (C1 / U1)

| Method | Path | auth | Request body | Success (200) | Errors |
|---|---|---|---|---|---|
| POST | `/api/tablet/login` | none | `{store_id:int, table_no:int, table_password:str}` | `{tablet_token:str, expires_at:str}` | 401 자격 불일치 |
| POST | `/api/admin/login` | none | `{store_id:int, username:str, password:str}` | `{access_token:str, expires_at:str}` | 401 자격 불일치, 429 시도 제한 |

### 5.2 메뉴 (C2 / U1)

| Method | Path | auth | Request | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/menus?category={opt}` | tablet | query `category?` | `[{id,category,name,price,description,image_url,display_order}]` (노출 순서 정렬, store=context) | 401 |
| GET | `/api/admin/menus?category={opt}` | admin | query `category?` | 위와 동일(관리자, store=AdminContext) | 401 |
| POST | `/api/admin/menus` | admin | `{category,name,price,description?,image_url?}` | 생성된 menu | 401, 422 검증 |
| PATCH | `/api/admin/menus/{menu_id}` | admin | 부분 필드 | 수정된 menu | 401, 404, 422 |
| DELETE | `/api/admin/menus/{menu_id}` | admin | – | `204` | 401, 404 |
| POST | `/api/admin/menus/reorder` | admin | `{ordered_ids:[int]}` | `204` | 401, 422 |

### 5.3 주문 — 고객 (C3 / U2)

| Method | Path | auth | Request body | Success | Errors |
|---|---|---|---|---|---|
| POST | `/api/orders` | tablet | **`{items:[{menu_id:int, qty:int}]}`** (store/table 미포함) | `{order_no:str, session_id:int, total:int}` | 401, 422 빈/유효하지 않은 items |
| GET | `/api/orders/current` | tablet | – (context로 현재 세션 식별) | `[{order_no,created_at,status,total,items:[{name,qty,unit_price}]}]` (시간순, 현재 세션만) | 401 |

- **store_id/table_no는 TabletContext에서 서버가 채움**. body/query로 받지 않는다.

### 5.4 주문/테이블 — 관리자 (C3·C4·C5 / U2)

| Method | Path | auth | Request | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/admin/tables` | admin | – | `[{table_no, current_total, has_active_session, latest_orders:[...]}]` | 401 |
| GET | `/api/admin/tables/{table_no}/orders` | admin | – | `[{order_id:int, order_no:str, created_at:str, status:OrderStatus, total:int, items:[{name,qty,unit_price}]}]` (현재 이용 세션 주문, 시간순) | 401, 404 활성 세션 없음 |
| GET | `/api/admin/orders/stream` | admin | SSE (§7) | `text/event-stream` | 401 |
| PATCH | `/api/admin/orders/{order_id}/status` | admin | `{status: OrderStatus}` | 갱신된 order | 401, 404, 422 |
| DELETE | `/api/admin/orders/{order_id}` | admin | – | `204` (총액 재계산 + event) | 401, 404 |
| POST | `/api/admin/tables` | admin | `{table_no:int, table_password:str}` | 생성된 table config | 401, 409 중복, 422 |
| POST | `/api/admin/tables/{table_no}/end-session` | admin | – | `{ended:true, session_id:int}` (이력 이동 + 리셋 + event) | 401, 404 활성 세션 없음 |
| GET | `/api/admin/tables/{table_no}/history?date_from={opt}&date_to={opt}` | admin | query 날짜 필터 | `[{session_id, order_no, ordered_at, total, items, completed_at}]` (역순) | 401 |

> `GET /api/admin/tables/{table_no}/orders`는 US-A2의 "테이블 카드 클릭 → 해당 테이블 전체 주문 상세"를 연결하기 위한 인터페이스다(새 기능 아님). `order_id`는 §5.4의 `PATCH`/`DELETE` 및 `order.created`(§8) payload의 `order_id`와 **동일 식별자**다.
> 여기 명시된 path/method/auth는 계약이다. request/response 필드의 **상세 검증 규칙**은 각 Unit Functional Design에서 확정하되 필드 집합·타입은 위를 따른다.

---

## 6. OrderStatus 값 (계약 enum)

```text
OrderStatus = "PENDING" | "IN_PROGRESS" | "DONE"
  PENDING     = 대기중
  IN_PROGRESS = 준비중
  DONE        = 완료
```
- 전이: 관리자만 변경(US-A3). 값 문자열은 위 3개로 고정(대소문자 포함). 표시 라벨(한글)은 프론트가 매핑.

---

## 7. SSE Endpoint & fetch 기반 Bearer 인증

- **Endpoint**: `GET /api/admin/orders/stream`, 응답 `Content-Type: text/event-stream`, **auth: admin Bearer**(`Depends(verify_admin_token)`).
- **클라이언트 소비 방식(F3 sseClient)**: native `EventSource` 미사용(헤더 설정 불가). **`fetch(url, {headers:{Authorization: "Bearer <jwt>"}})`** 로 요청하고 응답 `body`의 `ReadableStream`을 읽어 SSE 프레임을 파싱한다. 재연결 로직 포함.
- **프레임 형식**:
  ```text
  event: <event_type>
  data: <JSON payload>

  ```
  (이벤트당 `event:` 1줄 + `data:` 1줄 + 빈 줄 종료)
- 스트림은 **인증된 관리자의 store_id 범위 이벤트만** 브로드캐스트한다.
- SSE 실시간 요구사항(NFR-1): 신규 주문/상태 변경이 **2초 이내** 반영.

---

## 8. Event Type & Payload Schema

- **event provider / implementation owner = U2 (C7 Realtime)**. **payload schema의 authoritative 계약 = 이 문서(Integration Lead)**. U2가 스키마 변경이 필요하면 §15 CCR 제출.
- 인프로세스 pub/sub(단일 프로세스 전제) → 관리자 SSE로 push.

```text
order.created:
  { "store_id":int, "table_no":int, "session_id":int,
    "order": { "order_id":int, "order_no":str, "status":"PENDING", "total":int, "created_at":str,
               "items":[{"name":str,"qty":int,"unit_price":int}] } }
  # order_id는 PATCH/DELETE /api/admin/orders/{order_id} 및
  # GET /api/admin/tables/{table_no}/orders 의 order_id와 동일 식별자다.

order.status_changed:
  { "store_id":int, "table_no":int, "order_id":int, "order_no":str, "status":OrderStatus }

order.deleted:
  { "store_id":int, "table_no":int, "order_id":int, "session_id":int, "new_table_total":int }

table_session.ended:
  { "store_id":int, "table_no":int, "session_id":int, "completed_at":str }
```

---

## 9. 세션 구분 (계약상 두 개념)

| 구분 | 테이블 이용(주문) 세션 | 태블릿 인증 세션 |
|---|---|---|
| 소유 | C4 TableSession (U2), `table_sessions` 테이블 | C1 Auth (U1), tablet_token(JWT류, 16h) |
| 의미 | 첫 주문~이용 완료까지 영업 라이프사이클 | 디바이스 자동 로그인 자격 |
| 시작 | 해당 테이블 첫 주문 시 | 관리자 초기 설정 후 태블릿 최초 로그인 시 |
| 종료 | 관리자 `end-session`(이력화·총액 리셋) | 토큰 만료(16h) |
| **독립성** | **서로 시작/종료를 연동하지 않는다.** end-session은 태블릿 로그아웃을 유발하지 않는다. | |

---

## 10. Shared State / File Ownership (single-writer)

| Shared 대상 | Owner |
|---|---|
| DB schema / migration / `seed_if_empty` | **U1** |
| 공용 type/context 구현 모듈 (`common/`) | **U1** |
| backend dependency / lock | **U1** |
| Application entrypoint `main.py` (composition root) | **Integration Lead** |
| `INTEGRATION_CONTRACT.md` (본 계약) | **Integration Lead** |
| F3 Shared JS (`apiClient`, `sseClient`, 포맷) | **U3** |

- 도메인 유닛은 자신의 owned path만 쓰고, 위 shared 대상은 지정 owner만 수정한다.
- event payload schema는 계약(§8)에 따르며 owner는 Integration Lead(구현 provider는 U2).

---

## 11. Seed / Sample Data Ownership

- **Owner: U1 (C0 Persistence)** — `seed_if_empty` 구현 및 샘플 데이터 정의/준비 단독 책임.
- 대상: **샘플 매장 · 관리자 계정(bcrypt) · 카테고리 · 샘플 메뉴 · 테이블(비밀번호 포함)**.
- 실제 데이터 내용은 U1 Construction에서 작성. 통합 계약 관점의 최소 보장: **시드 후 vertical slice가 즉시 동작**할 수 있도록 최소 1개 매장/1개 관리자/여러 카테고리·메뉴/여러 테이블을 포함.

---

## 12. 각 Unit의 Provided / Consumed Interface

### U1 provides
- Persistence/Repository 기반, `init_db`/`seed_if_empty`/`get_connection`.
- Auth: `POST /api/tablet/login`, `POST /api/admin/login`; 의존성 `verify_tablet_token → TabletContext`, `verify_admin_token → AdminContext`.
- Menu: 고객 조회 + 관리자 CRUD/reorder (§5.2).
- 공용 type/context(`common/`).
- bcrypt password hashing capability: `app.auth.security.hash_password(plaintext: str) -> str`.
- **consumes**: 없음.

### U2 provides
- 주문 API(고객·관리자, §5.3/5.4) — 관리자 테이블 주문 상세 `GET /api/admin/tables/{table_no}/orders`(US-A2 연결) 포함, 세션·이력 API(이력에 원 주문 시각 `ordered_at` 보존), SSE 스트림(§7), 이벤트 발행(§8).
- **order_id 일관성**: `order.created`(§8) payload의 `order_id`는 관리자 주문 상세·`PATCH`/`DELETE /api/admin/orders/{order_id}`에서 동일 식별자로 사용된다.
- **consumes (from U1)**: Persistence/Repository, `verify_tablet_token`/`verify_admin_token`, Menu 단가/유효성 조회, 공용 type, table setup용 password hashing capability(`PasswordHasherPort`를 통해 소비).

### U3 provides
- 정적 서빙 UI(고객 `/`, 관리자 `/admin`), F3 Shared JS(단독).
- **consumes**: U1(인증/메뉴 API), U2(주문/세션/이력 API + SSE + 이벤트 payload). 모든 백엔드 호출은 `Authorization: Bearer` 사용.

---

## 13. 최소 Contract / Integration Tests

병렬 개발이 계약을 지키는지 확인하는 **최소 세트**(상세 케이스는 Build and Test 단계에서 확장):

**Contract-level (유닛 경계 검증)**
1. `POST /api/tablet/login` → 유효 자격 시 `tablet_token` 발급, 잘못된 비밀번호 시 401.
2. `POST /api/admin/login` → JWT 발급, 반복 실패 시 429.
3. `GET /api/menus` (tablet Bearer) → 시드 메뉴가 노출 순서대로 반환, 무인증 시 401.
4. `POST /api/orders`의 식별정보 원칙 검증:
   - 정상 request body는 `{items:[...]}` 형태다.
   - 저장되는 `store_id`/`table_no`는 **반드시 `verify_tablet_token`의 TabletContext에서 결정**된다.
   - 클라이언트가 제공한 store/table 값을 신뢰하지 않는다.
   - *(추가 필드를 reject할지 ignore할지는 Functional Design의 validation 결정으로 남긴다 — 계약으로 강제하지 않음.)*
5. `PATCH /api/admin/orders/{id}/status` → OrderStatus 값만 허용(그 외 422).
6. SSE `GET /api/admin/orders/stream` → Bearer 헤더 없는 fetch는 401, 있으면 `text/event-stream` 유지.
7. 각 event payload가 §8 스키마 키/타입과 일치(특히 `order.created.order.order_id` 존재).
8. `GET /api/admin/tables/{table_no}/orders`가 현재 세션 주문을 `order_id` 포함해 반환하고, 그 `order_id`로 `PATCH`/`DELETE`가 동작(식별자 일관성).

**Integration-level (핵심 vertical slice, 3유닛 통합)**
9. 메뉴 조회(U1) → 장바구니(U3, 로컬) → `POST /api/orders`(U2) → `order.created` 발행 → 관리자 SSE 수신(U2+U3) → 카드 클릭 시 `GET /api/admin/tables/{table_no}/orders`로 상세 조회 → `PATCH .../status`(U2) → 관리자 대시보드 반영 → `GET /api/orders/current`(U3)에서 상태 갱신 확인.
10. end-session → `table_session.ended` 발행 + `GET /api/orders/current` 빈 목록 + `GET .../history`에 아카이브 표시(각 항목이 `ordered_at`[원 주문 시각]과 `completed_at`[이용 완료 시각]을 모두 포함).

---

## 14. Merge Order

병렬 개발이되 **머지 순서**는 소비 의존을 따른다(개발 자체는 계약 기준으로 동시 진행):

```text
0) Integration Lead: INTEGRATION_CONTRACT.md FROZEN + main.py composition-root 스켈레톤 준비
1) U1  : common/ 공용 type/context 구현 + persistence + schema + seed + auth + menu (provides contexts/menu/auth)
2) U2  : order + table_session + order_history + realtime (consumes U1)
3) U3  : frontend customer + admin + shared JS (consumes U1, U2)
4) Integration Lead: main.py에 각 유닛 router include + static mount 조립
5) 통합 검증: §13 vertical slice e2e
```

- Integration Lead는 계약 문서(§4)에 **공용 type/context의 계약(시그니처)** 을 정의할 수 있으나, `backend/app/common/`의 **실제 파일 구현은 U1만** 수행한다(§10 single-writer 유지). Integration Lead는 `common/`을 scaffold하거나 수정하지 않는다.
- 각 유닛은 머지 전 상대 계약을 **stub/mock**으로 대체해 독립 진행 가능.
- main.py 조립은 유닛이 제공한 `router`/static artifact를 등록만 한다(유닛은 main.py를 수정하지 않음).

---

## 15. Contract Change Request (CCR) 절차

1. **제출**: 변경이 필요한 유닛(예: U2의 event schema 변경)이 CCR을 Integration Lead에게 제출.
   - 포함: 대상 섹션, 현재 계약, 제안 변경, 사유, 영향 받는 유닛(provided/consumed).
2. **검토**: Integration Lead가 승인된 Requirements/Design 범위 내인지 확인(**새 요구사항 추가는 거부**).
3. **반영**: 승인 시 Integration Lead가 **본 문서만** 수정하고 버전 증가.
   - 하위호환 = **minor**(v0.**x**.0), 호환 깨짐 = **major**(v**x**.0.0).
4. **통지**: 변경 요약을 팀에 공유하고, 영향 유닛이 계약 재확인 후 진행.
5. 도메인 유닛은 **계약 문서를 직접 수정하지 않는다**(single-writer 원칙).

---

### 적용된 CCR

- **CCR-001 (APPROVED, 2026-09-07)**: U1의 기존 `app.auth.security.hash_password`를 U2 table setup이 `PasswordHasherPort`로 소비하도록 provided/consumed interface에 명시했다. U1 제품 코드, DB schema, REST API, SSE/event 의미는 변경하지 않으며 U3 영향은 없다.

### 상태: FROZEN (v0.2.0)
이 계약은 CCR-001을 반영하여 **FROZEN (v0.2.0)** 이다. 이후 변경은 §15 CCR 절차로만 수행한다.
