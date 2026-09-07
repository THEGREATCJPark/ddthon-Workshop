# U2 — Domain Entities (Order · Session · Realtime)

> **Unit**: U2 (C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime)
> **계약 기준**: `INTEGRATION_CONTRACT.md` **v0.2.0** (FROZEN) — 아래 엔티티/필드는 §3 스키마와 §8 이벤트 계약을 하드 제약으로 준수한다.
> **범위**: 기술 비종속(technology-agnostic) 도메인 모델. 저장 스키마는 U1(C0) 소유이며, 여기서는 U2가 소비/사용하는 관점의 도메인 개념을 정의한다.
> **답변 반영**: Q1=A, Q2=D, Q3=A, Q4=A, Q5=A, Q6=A, Q7=A, Q8=A, Q9=A, Q10=A.

---

## 1. 엔티티 개요 (U2 도메인)

| 엔티티 | 소유 컴포넌트 | 저장 테이블(§3) | 라이프사이클 |
|---|---|---|---|
| **TableConfig** | C4 TableSession | `tables` | 관리자 setup 시 생성, 영속(이용 세션과 무관) |
| **TableSession** | C4 TableSession | `table_sessions` | 첫 주문 시 ACTIVE 시작 → end-session 시 ENDED |
| **Order** | C3 Order | `orders` | 주문 생성 시 PENDING → 상태 전이 → (end-session 시 아카이브) |
| **OrderItem** | C3 Order | `order_items` | Order 생성 시 함께 저장(주문 시점 스냅샷) |
| **OrderHistoryRecord** | C5 OrderHistory | `order_history` | end-session 아카이브 시 생성(불변) |
| **DomainEvent** | C7 Realtime | (비영속, in-memory) | publish 시 생성 → 구독자 broadcast 후 소멸 |

> U2는 위 테이블에 대한 **읽기/쓰기 도메인 로직**을 담당한다. **스키마 정의/마이그레이션 자체는 U1(C0) single-writer.**

---

## 2. 엔티티 상세

### 2.1 TableConfig  (`tables`)
관리자가 초기 설정한 테이블 구성. 태블릿 인증(자동 로그인)의 대상이며, 이용 세션과 독립적(§9).

| 필드 | 타입 | 비고 |
|---|---|---|
| id | int (PK) | |
| store_id | int (FK stores) | |
| table_no | int | 매장 내 테이블 번호. `UNIQUE(store_id, table_no)` |
| password_hash | str | bcrypt. **U1 `common.hash_password()`로 생성**(계약 v0.2.0 §4/§12, Q7=A). U2는 crypto 직접 구현 안 함 |

- 생성: `setup_table` (C4). 검증 후 `hash_password(table_password)` → `password_hash` 저장.
- 소비: U1 `tablet_login`이 `verify_password`로 검증(U2는 검증에 관여하지 않음).

### 2.2 TableSession  (`table_sessions`)
"테이블 이용(주문) 세션" — 첫 주문부터 이용 완료까지의 영업 라이프사이클(§9).

| 필드 | 타입 | 비고 |
|---|---|---|
| id | int (PK) | `session_id`로 Order/History에서 참조 |
| store_id | int (FK stores) | |
| table_no | int | |
| status | str | `'ACTIVE'` \| `'ENDED'` |
| started_at | str (ISO8601 UTC) | 첫 주문 시각 |
| ended_at | str (ISO8601 UTC) \| null | end-session 시각 |

- **불변식**: 하나의 `(store_id, table_no)`에는 **최대 1개의 ACTIVE 세션**만 존재(Q10=A, 단일 프로세스 get-or-create).
- 시작: `get_or_start_session` — ACTIVE 세션 없으면 생성(Q4=A: 주문 삭제로 비어도 ACTIVE 유지).
- 종료: `end_session` — 상태 ENDED + `ended_at` 기록(Q5=A: 비파괴적, orders/order_items 행은 보존하되 current 쿼리에서 제외).

### 2.3 Order  (`orders`)
고객 주문 1건. 현재 세션에 그룹화된다.

| 필드 | 타입 | 비고 |
|---|---|---|
| id | int (PK) | **= 계약상 `order_id`**(§5.4 PATCH/DELETE, §8 `order.created.order.order_id`와 동일 식별자) |
| store_id | int (FK stores) | **TabletContext에서 서버가 채움**(body 미신뢰, §4/§5.3) |
| table_no | int | **TabletContext에서 서버가 채움** |
| session_id | int (FK table_sessions) | 소속 이용 세션 |
| order_no | str | 표시용. **세션별 순번**(`#1, #2 …`), 세션 내 1부터 증가(Q1=A) |
| status | OrderStatus | `PENDING`\|`IN_PROGRESS`\|`DONE`(§6). 생성 시 `PENDING` |
| total | int | 원 단위 정수 = Σ(item.unit_price × item.qty) |
| created_at | str (ISO8601 UTC) | 주문 생성 시각. 아카이브 시 `order_history.ordered_at`로 스냅샷 |

### 2.4 OrderItem  (`order_items`)
주문 항목. **주문 시점 스냅샷**(메뉴 변경/삭제에 영향받지 않음).

| 필드 | 타입 | 비고 |
|---|---|---|
| id | int (PK) | |
| order_id | int (FK orders) | |
| menu_id | int (FK menus) | 원본 메뉴 참조(스냅샷 원천) |
| name | str | **주문 시점 메뉴명 스냅샷**(U1 Menu 조회 결과) |
| unit_price | int | **주문 시점 단가 스냅샷**(U1 Menu 조회 결과, 원 단위) |
| qty | int | ≥ 1 (Q2=D). 동일 menu_id는 생성 시 1줄로 병합(qty 합산) |

### 2.5 OrderHistoryRecord  (`order_history`)
종료된 이용 세션의 주문 아카이브. **불변**.

| 필드 | 타입 | 비고 |
|---|---|---|
| id | int (PK) | |
| store_id | int | |
| table_no | int | |
| session_id | int | 그룹화 키(한 세션의 여러 주문) |
| order_no | str | 원 주문의 order_no 스냅샷 |
| total | int | 원 주문 총액 스냅샷 |
| items_json | str (JSON) | `[{name, qty, unit_price}]` 주문 항목 스냅샷 |
| ordered_at | str (ISO8601 UTC) | **원 주문 시각**(= `orders.created_at` 스냅샷) |
| completed_at | str (ISO8601 UTC) | 이용 완료(end-session) 시각 |

- 1 세션의 각 Order → 1 OrderHistoryRecord (order 단위 아카이브, session_id로 그룹).

### 2.6 DomainEvent  (비영속, C7)
in-process pub/sub 이벤트. payload는 계약 §8을 그대로 따른다(권위 스키마 = Integration Lead).

| type | payload 요약(§8) |
|---|---|
| `order.created` | `{store_id, table_no, session_id, order:{order_id, order_no, status:"PENDING", total, created_at, items:[{name,qty,unit_price}]}}` |
| `order.status_changed` | `{store_id, table_no, order_id, order_no, status}` |
| `order.deleted` | `{store_id, table_no, order_id, session_id, new_table_total}` |
| `table_session.ended` | `{store_id, table_no, session_id, completed_at}` |

- **비영속·no replay**(Q9=A): 이벤트는 저장하지 않으며 재연결 시 재전송하지 않는다.

---

## 3. 엔티티 관계 (ERD, 텍스트)

```text
stores(1) ──< tables            (TableConfig)
stores(1) ──< table_sessions(1) ──< orders(1) ──< order_items
                     │                  
                     └── (end_session archive) ──> order_history   [session_id로 그룹]

menus(1) ──< order_items        (menu_id 참조; name/unit_price는 스냅샷)
```

관계 요약:
- `TableSession 1 : N Order`  (session_id)
- `Order 1 : N OrderItem`  (order_id)
- `OrderItem N : 1 Menu`  (menu_id; 스냅샷 보존이라 메뉴 삭제와 무관)
- `TableSession 1 : N OrderHistoryRecord`  (아카이브 후, session_id 그룹)
- `TableConfig`는 이용 세션과 **관계상 독립**(같은 table_no로 논리 연결되나 라이프사이클 비연동, §9)

---

## 4. 값 객체 / 열거형

- **OrderStatus** = `PENDING` | `IN_PROGRESS` | `DONE` (§6, 문자열 고정, 대소문자 포함). 한글 라벨 매핑은 프론트(U3) 책임.
- **SessionStatus** = `ACTIVE` | `ENDED` (§3 `table_sessions.status`).
- **Money**: 정수(원). 부동소수 금지(§3).
- **Timestamp**: ISO 8601 UTC 문자열(§3).
- **OrderNo**: 세션 범위 표시 문자열(Q1=A). 저장은 `orders.order_no: TEXT`.

---

## 5. U2가 소비하는 U1 인터페이스 (계약 v0.2.0 §12)
- Persistence/Repository 기반, `get_connection`.
- `verify_tablet_token` → `TabletContext{store_id, table_no}` (고객 API 식별정보 신뢰 출처).
- `verify_admin_token` → `AdminContext{store_id, admin_user_id, username}` (관리자 API).
- Menu 단가/유효성 조회(주문 생성 시 스냅샷 원천).
- **`hash_password(plaintext)->str`** (테이블 setup 비밀번호 해싱; Q7=A, v0.2.0).
- 공용 type / 표준 에러 포맷(`ErrorResponse`).
