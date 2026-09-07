# U2 — Business Rules & Validation (Order · Session · Realtime)

> **Unit**: U2 (C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime)
> **계약 기준**: `INTEGRATION_CONTRACT.md` **v0.2.0** (FROZEN). 에러 코드(§4), 엔드포인트(§5), OrderStatus(§6), SSE(§7), 이벤트(§8) 준수.
> **답변 반영**: Q1=A, Q2=D, Q3=A, Q4=A, Q5=A, Q6=A, Q7=A, Q8=A, Q9=A, Q10=A.
> 표준 에러 코드: `UNAUTHORIZED`(401), `FORBIDDEN`(403), `NOT_FOUND`(404), `VALIDATION_ERROR`(422), `CONFLICT`(409), `RATE_LIMITED`(429).

---

## A. 식별정보 & 보안 규칙

| ID | 규칙 | 위반 시 |
|---|---|---|
| R-SEC1 | 관리자 API의 대상 리소스는 **`AdminContext.store_id` 범위**로 제한. 타 매장 order/table 접근 금지. | 404 NOT_FOUND(존재 은닉) |
| R-SEC2 | 고객 API의 `store_id`/`table_no`는 **오직 `TabletContext`**(verify_tablet_token)에서 결정. body/query의 store/table 식별정보는 신뢰 입력이 아니다. | — (신뢰하지 않음) |
| R-SEC3 | 고객 API는 `verify_tablet_token`, 관리자 API/SSE는 `verify_admin_token` 가드 필수. 토큰 없음/만료 → 401. | 401 UNAUTHORIZED |
| R-SEC4 | 비밀번호 해싱은 **U1 `common.hash_password()`만** 사용(Q7=A, v0.2.0). U2 자체 crypto 구현 금지. | (계약 위반) |

---

## B. 주문 생성 규칙 (C3, `POST /api/orders`)

| ID | 규칙 | 위반 시 |
|---|---|---|
| R-O1 | `items`는 1개 이상. 빈 배열/누락 → 실패. | 422 VALIDATION_ERROR |
| R-O2 | 각 `menu_id`는 컨텍스트 store에 **존재하는 유효 메뉴**여야 함. | 422 VALIDATION_ERROR |
| R-O3 | 각 `qty`는 정수 `>= 1`. (상한 없음 — Q2=D는 상한 미적용 C안 제외) | 422 VALIDATION_ERROR |
| R-O4 | 동일 `menu_id` 라인은 **1줄로 병합**(qty 합산) 후 저장. (Q2=D) | — (정규화) |
| R-O5 | 알 수 없는 추가 body 필드는 **무시**(reject 아님). (Q2=D) | — (무시) |
| R-O6 | `name`/`unit_price`는 **주문 시점 U1 Menu 조회 스냅샷**으로 저장(이후 메뉴 변경 무관). | — |
| R-O7 | `total` = Σ(unit_price × qty), **정수(원)**. 부동소수 금지. | — |
| R-O8 | 저장 `store_id`/`table_no`는 TabletContext 값(R-SEC2). | — |

## C. 주문 번호 규칙 (C3)

| ID | 규칙 |
|---|---|
| R-N1 | `order_no`는 **해당 이용 세션 내 순번**(Q1=A): 세션의 N번째 주문 → `#N`(1부터). |
| R-N2 | 세션이 새로 시작되면 순번은 1부터 재시작(세션 스코프). |
| R-N3 | 아카이브 시 `order_no`는 그대로 `order_history.order_no`에 스냅샷. |

## D. 상태 전이 규칙 (C3, `PATCH .../status`)

| ID | 규칙 | 위반 시 |
|---|---|---|
| R-D1 | `status` ∈ {`PENDING`,`IN_PROGRESS`,`DONE`}(§6, 대소문자 정확). | 422 VALIDATION_ERROR |
| R-D2 | **자유 전이 허용**(Q3=A): 현재 값과 무관하게 세 값 중 하나로 설정 가능(뒤로 전이 포함). | — |
| R-D3 | 대상 order 미존재 또는 store 스코프 밖 → 404. | 404 NOT_FOUND |
| R-D4 | 상태 변경 성공 시 `order.status_changed` 발행(§8). | — |

## E. 주문 삭제 규칙 (C3, `DELETE .../{order_id}`)

| ID | 규칙 | 위반 시 |
|---|---|---|
| R-E1 | 대상 order 미존재/스코프 밖 → 404. | 404 NOT_FOUND |
| R-E2 | 상태와 무관하게 삭제 가능(PENDING/IN_PROGRESS/DONE 모두). | — |
| R-E3 | 삭제 후 해당 세션 총액 재계산 → `new_table_total`. | — |
| R-E4 | 세션이 비게 되어도 **ACTIVE 유지**(자동 종료 안 함, Q4=A). | — |
| R-E5 | 삭제 성공 시 `order.deleted{order_id, session_id, new_table_total}` 발행(§8). | — |

---

## F. 이용 세션 규칙 (C4)

| ID | 규칙 | 위반 시 |
|---|---|---|
| R-S1 | `(store_id, table_no)`당 ACTIVE 세션은 **최대 1개**. 첫 주문 시 생성(get_or_start_session). | — |
| R-S2 | 동시 첫 주문은 단일 프로세스 get-or-create(단일 트랜잭션)로 처리(Q10=A). 분산 락 미도입. | — |
| R-S3 | end-session은 **비파괴적**(Q5=A): `status='ENDED'` + `ended_at` 기록. orders/order_items 물리 삭제 안 함. | — |
| R-S4 | "현재" 조회(current orders, list_tables total/preview)는 **ACTIVE 세션만** 대상. ENDED는 제외. | — |
| R-S5 | 활성 세션 없는 테이블의 `end-session`/상세 조회 → 404. | 404 NOT_FOUND |
| R-S6 | 이용 세션 종료는 **태블릿 인증 세션과 무관**(§9). 로그아웃 유발 금지. | — |

## G. 테이블 설정 규칙 (C4, `POST /api/admin/tables`)

| ID | 규칙 | 위반 시 |
|---|---|---|
| R-T1 | `table_no` 양의 정수, `table_password` 비어있지 않음. | 422 VALIDATION_ERROR |
| R-T2 | `(store_id, table_no)` 중복 등록 불가. | 409 CONFLICT |
| R-T3 | `password_hash`는 U1 `hash_password(table_password)` 결과 저장(R-SEC4). | — |
| R-T4 | store_id는 AdminContext에서 결정(body 미신뢰). | — |

## H. 대시보드 목록 규칙 (C4, `GET /api/admin/tables`)

| ID | 규칙 |
|---|---|
| R-H1 | store의 **모든 설정된 테이블**을 반환(활성 세션 없어도 포함). |
| R-H2 | `current_total` = ACTIVE 세션 주문 total 합(없으면 0). |
| R-H3 | `latest_orders` = ACTIVE 세션 최신 **3건**(Q6=A), newest-first, 각 `{order_no,status,total,created_at}`. |
| R-H4 | `has_active_session` = ACTIVE 세션 존재 여부(bool). |

---

## I. 이력 규칙 (C5)

| ID | 규칙 |
|---|---|
| R-I1 | 아카이브는 order 단위 레코드 생성, `session_id`로 그룹. **불변**(수정/삭제 API 없음). |
| R-I2 | `ordered_at` = 원 `orders.created_at` 스냅샷. `completed_at` = end-session 시각. 둘 다 응답 포함(§5.4). |
| R-I3 | `items_json` = `[{name, qty, unit_price}]` 주문 항목 스냅샷 JSON. |
| R-I4 | 날짜 필터(Q8=A): **`completed_at` 기준**, `date_from`/`date_to` **양끝 inclusive**. date-only는 해당 일 전체 UTC 범위. 한쪽만 있으면 open-ended. |
| R-I5 | 정렬: `completed_at` **역순**(최신 먼저). |

---

## J. Realtime / SSE 규칙 (C7)

| ID | 규칙 |
|---|---|
| R-J1 | 이벤트는 **발행 매장(store_id) 구독자에게만** 브로드캐스트(§7 스코프). |
| R-J2 | payload는 계약 §8 스키마(키/타입) **정확히** 준수. 특히 `order.created.order.order_id` 포함. 스키마 변경 필요 시 **CCR**(임의 변경 금지). |
| R-J3 | SSE 프레임 형식(§7): `event: <type>\n` + `data: <JSON>\n` + 빈 줄. |
| R-J4 | 인증: `verify_admin_token`(Bearer). 헤더 없는 요청 → 401. `text/event-stream` 유지. |
| R-J5 | **no persistence / no replay / no Last-Event-ID**(Q9=A). 재연결은 클라이언트 책임. |
| R-J6 | idle ~15초마다 heartbeat 주석(`: ping`) 전송(Q9=A). 연결 종료 시 구독/큐 해제. |
| R-J7 | Realtime 전달 실패가 주문/세션 트랜잭션을 롤백시키지 않음(best-effort). |

---

## K. 트랜잭션 & 이벤트 순서 규칙

| ID | 규칙 |
|---|---|
| R-TX1 | 주문 생성: Order+OrderItem 저장은 단일 트랜잭션, **커밋 성공 후** `order.created` 발행. |
| R-TX2 | end-session: 아카이브 insert + 세션 ENDED는 단일 트랜잭션, **커밋 후** `table_session.ended` 발행. |
| R-TX3 | 상태변경/삭제: 저장 커밋 후 각각 `order.status_changed`/`order.deleted` 발행. |

---

## L. 계약 준수 체크리스트 (self-check, §13 최소 contract test 대응)
- [x] `POST /api/orders` body는 `{items:[...]}`, store/table은 TabletContext 결정(test #4).
- [x] `PATCH .../status`는 OrderStatus 값만 허용, 그 외 422(test #5).
- [x] SSE는 Bearer 없으면 401, 있으면 `text/event-stream`(test #6).
- [x] 각 이벤트 payload가 §8 키/타입 일치, `order.created.order.order_id` 존재(test #7).
- [x] `GET /api/admin/tables/{table_no}/orders`가 `order_id` 포함, PATCH/DELETE와 동일 식별자(test #8).
- [x] end-session 후 current 빈 목록 + history에 `ordered_at`+`completed_at` 포함(test #10).

## M. 확장(Extension) 준수 요약
- Security Baseline / Resiliency Baseline / Property-Based Testing: **모두 Disabled**(aidlc-state.md Extension Configuration) → 해당 확장 규칙 **N/A**.
- 단, 요구사항 명시 보안(bcrypt 해싱=U1 헬퍼 소비, JWT/토큰 가드)은 기능 요구로 준수(R-SEC*, R-T3).

## N. 추가 계약 변경 필요 여부
- 본 Functional Design은 **계약 v0.2.0 범위 내에서 완결**되며, 추가 CCR이 필요한 항목은 **없음**.
- 향후 event/endpoint/schema 변경이 필요해지면 임의 수정하지 않고 **CCR**로 제출한다(§15).
