# U1 — Business Logic Model

> 기준: FROZEN Integration Contract v0.1.0. 기술 스택은 계약/요구사항에서 고정(FastAPI + SQLite). 아래는 **비즈니스 로직 흐름**이며 제품 코드가 아니다.
> 3계층 구조: **Router(API) → Service(비즈니스 규칙) → Repository(영속)**. 각 도메인 디렉터리(`persistence`, `auth`, `menu`, `common`)는 내부에 이 계층을 가진다.

---

## A. C0 Persistence

### A1. 연결 / 트랜잭션
- `get_connection()`: SQLite 연결 반환. 필수 PRAGMA: `foreign_keys = ON`. row → dict 매핑(row factory).
- `transaction()`: 단위 작업(Unit-of-Work) 컨텍스트. 성공 시 commit, 예외 시 rollback. 쓰기 작업(주문 생성·상태 변경 등 U2 포함)은 이 트랜잭션 경계를 재사용.
- Repository 공통 기반: `store_id` 스코프 헬퍼, 파라미터 바인딩(문자열 포매팅 금지 → SQL 인젝션 방지), 단건/다건 조회 유틸.

### A2. 스키마 초기화 `init_db()`
- 계약 §3의 **모든 테이블**을 `CREATE TABLE IF NOT EXISTS`로 생성(멱등). U1이 스키마 single-writer이므로 U2 소유 도메인 테이블(table_sessions/orders/order_items/order_history)도 여기서 생성.
- 인덱스(최소): `menus(store_id, display_order)`, `admin_users(store_id, username)`, `tables(store_id, table_no)` — 조회/유니크 보장.
- 앱 기동 시 1회 호출(호출 지점은 Integration Lead의 main.py startup — U1은 함수만 제공).

### A3. 시드 `seed_if_empty()`  (U1 단독 owner, 계약 §11)
- **초기화 방식**: DB가 "비어 있음"일 때만 시드. 비어 있음 판정 기준 = `stores` 테이블 0건.
- **데이터 구조/관계** (내용은 Construction에서 작성, 여기선 구조·관계·순서만):
  1. Store 1개 생성 → `store_id` 확보.
  2. AdminUser 1개(해당 store) — 비밀번호 **bcrypt** 해시로 저장.
  3. Tables 여러 개(해당 store, table_no 유니크) — 각 태블릿 비밀번호 bcrypt 해시.
  4. Categories(문자열) + Menus 여러 개(해당 store, 카테고리별, display_order 순차 부여).
  - FK 순서 보장: store → (admin_users, tables, menus). 한 트랜잭션으로 원자적 삽입.
- **재실행 중복 방지(dedup-on-rerun)**:
  - 1차 가드: `stores` 비어있지 않으면 **전체 스킵**(정상 경로).
  - 2차 가드(방어적): 개별 삽입도 자연키 기준 존재 확인 후 삽입(store name, (store_id,username), (store_id,table_no), (store_id,category,name)) — 부분 시드 상태에서도 중복 없음.
- **통합 보장(계약 §11)**: 시드 후 vertical slice가 즉시 동작하도록 최소 1 매장 / 1 관리자 / 여러 카테고리·메뉴 / 여러 테이블 포함.

---

## B. C1 Auth

### B1. 관리자 로그인  `POST /api/admin/login`  (계약 §5.1)
입력: `{store_id, username, password}` → 성공 `{access_token, expires_at}`.

흐름:
1. **시도 제한 선검사**: (store_id, username) 키가 잠금 상태면 즉시 **429 RATE_LIMITED**(자격 검증 안 함).
2. `admin_users`에서 (store_id, username) 조회. 없으면 실패 처리.
3. `bcrypt.verify(password, password_hash)`. 불일치면 실패 처리.
4. **실패 처리**: 실패 카운터 증가 → 연속 실패가 5회에 도달하면 10분 잠금 설정, 응답 **401 UNAUTHORIZED**(계정 존재 여부 노출 안 하도록 동일 메시지).
5. **성공 처리**: 실패 카운터 리셋 → AdminToken(JWT) 발급(claims: admin_user_id, store_id, username, typ=admin, exp=now+16h) → `expires_at`(ISO 8601) 동봉.

### B2. 태블릿 로그인  `POST /api/tablet/login`  (계약 §5.1)
입력: `{store_id, table_no, table_password}` → 성공 `{tablet_token, expires_at}`.

흐름:
1. `tables`에서 (store_id, table_no) 조회. 없으면 401.
2. `bcrypt.verify(table_password, password_hash)`. 불일치 401.
3. 성공 시 TabletToken(JWT) 발급(claims: store_id, table_no, typ=tablet, exp=now+16h) → `expires_at` 동봉.
- 태블릿 로그인은 **디바이스 자동 로그인 자격**이며 이용(주문) 세션과 무관(계약 §9). 시도 제한은 요구사항이 관리자 로그인(FR-A1) 중심이므로 태블릿은 미적용(Open: 필요 시 확장).

### B3. 토큰 검증 의존성 (U2·Menu가 소비)
- `verify_admin_token(Authorization: Bearer)` → JWT 디코드·서명검증·만료검증·`typ==admin` → `AdminContext{store_id, admin_user_id, username}`. 실패 시 401.
- `verify_tablet_token(Authorization: Bearer)` → JWT 디코드·검증·`typ==tablet` → `TabletContext{store_id, table_no}`. 실패 시 401.
- 두 함수는 FastAPI 의존성(Depends) 형태로 제공되어 U2/Menu 라우터가 재사용.

### B4. 시도 제한 모델
- 저장소: 인메모리 맵 `{(store_id, username): {fail_count, locked_until}}`(단일 프로세스 전제, 계약 §7·§8과 동일한 in-process 가정). 재시작 시 초기화.
- 정책: **(store_id, username) 기준 연속 5회 실패 시 10분 잠금**. 잠금 중 요청은 자격 검증 없이 429. **성공 로그인 시 카운터와 잠금을 리셋**.

### B5. JWT 서명 시크릿 (설정)
- 알고리즘 **HS256** 유지.
- 시크릿 출처: 환경변수 `TABLE_ORDER_JWT_SECRET`. **미설정 시 프로세스 기동 시점에 랜덤 시크릿을 1회 생성**하여 해당 프로세스 수명 동안 사용(재시작 시 이전 발급 토큰은 무효화됨 — 로컬 개발 편의). **Git에 포함되는 고정 시크릿 fallback은 사용하지 않는다.** 실제 시크릿 값은 문서/코드에 기재하지 않는다.

---

## C. C2 Menu

### C1. 고객 메뉴 조회  `GET /api/menus?category=`  (tablet, 계약 §5.2)
1. `verify_tablet_token` → TabletContext. store = **context.store_id**(요청값 아님).
2. `menus` where store_id=context.store_id (+ category 필터 옵션).
3. 정렬 `display_order ASC, id ASC` → 계약 필드 집합 반환.

### C2. 관리자 메뉴 조회  `GET /api/admin/menus?category=`  (admin, 계약 §5.2)
- `verify_admin_token` → AdminContext. store = AdminContext.store_id. 나머지 동일.

### C3. 메뉴 생성  `POST /api/admin/menus`  (admin)
입력: `{category, name, price, description?, image_url?}`.
1. 검증(§business-rules). 통과 못하면 422.
2. `display_order` = 해당 store 현재 최대값 + 1(맨 뒤 append).
3. store_id = AdminContext.store_id로 삽입 → 생성된 menu 반환.

### C4. 메뉴 수정  `PATCH /api/admin/menus/{menu_id}`  (admin)
1. (store_id=context, id=menu_id) 조회. 없으면 404 NOT_FOUND.
2. 제공된 부분 필드만 검증·갱신(store_id 변경 불가). 검증 실패 422.
3. 갱신된 menu 반환.

### C5. 메뉴 삭제  `DELETE /api/admin/menus/{menu_id}`  (admin)
1. (store_id=context, id) 조회. 없으면 404 NOT_FOUND.
2. **참조되지 않은 메뉴 삭제**는 정상 지원 → 204.
3. **FK 기준**: 계약 §3의 `order_items.menu_id FK->menus.id` 정의를 그대로 구현 기준으로 사용한다(nullable/ON DELETE 별도 부여 없음). **이미 `order_items`에서 참조 중인 메뉴 삭제의 세부 정책은 이번 Functional Design에서 새로 확정하지 않는다**(도메인 §7 — CCR deferred, Known limitation). 통합/Build·Test에서 blocker가 되면 CCR로 재검토.

### C6. 노출 순서 변경  `POST /api/admin/menus/reorder`  (admin)
입력: `{ordered_ids:[int]}`.
1. `ordered_ids`의 모든 id가 (store_id=context)에 존재하는지 검증. 아니면 422.
2. **재정렬 규칙(부분 목록 허용)**:
   1) `ordered_ids`에 포함된 메뉴를 **지정된 순서대로** 앞에 배치.
   2) `ordered_ids`에 없는 나머지 메뉴는 **기존 상대 순서(현재 display_order ASC, id ASC)를 유지**하며 그 뒤에 배치.
   3) 이렇게 만든 전체 순서로 `display_order`를 **0..N-1 연속 값으로 재번호화**(한 트랜잭션).
   → 204.

---

## D. Provided Interface — U2가 소비 (계약 §12)
> U2가 stub/mock 없이 통합 시 의존하는 U1 표면.

| 제공 | 형태 | U2 용도 |
|---|---|---|
| `get_connection()` / `transaction()` | 영속 기반 | 주문/세션/이력 쓰기 트랜잭션 |
| `init_db()` / `seed_if_empty()` | 초기화 | 스키마·초기데이터(주문 도메인 테이블 포함) |
| `verify_tablet_token → TabletContext` | Depends | 고객 주문 API 식별(Source of Truth) |
| `verify_admin_token → AdminContext` | Depends | 관리자 주문/세션/이력 API |
| **Menu 단가·유효성 조회** | Repository read | 주문 생성 시 `menu_id → {name, price}` 스냅샷 및 존재/店 검증 |
| 공용 type/context, ErrorResponse, 에러코드, 시간 헬퍼 | `common/` | 전 유닛 공통 |

- **Menu 조회 인터페이스 (신규 계약 아님, U1 내부 제공)**: `menu_repository.get_for_order(store_id, menu_id) -> {id, name, price} | None`, 및 벌크 `get_many_for_order(store_id, [menu_id]) -> {menu_id: {name, price}}`. U2는 이를 사용해 주문 시점 `name/unit_price`를 스냅샷하고, 존재하지 않거나 타 매장 메뉴면 주문 검증에서 거부(반환 None). *이는 U1이 U2에 제공하는 read 계약이며 REST 엔드포인트가 아니다.*

## E. Consumed Interface
- 없음(기반 유닛, 계약 §12).
