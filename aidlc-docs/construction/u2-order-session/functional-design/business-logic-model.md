# U2 — Business Logic Model (Order · Session · Realtime)

> **Unit**: U2 (C3 Order, C4 TableSession, C5 OrderHistory, C7 Realtime)
> **계약 기준**: `INTEGRATION_CONTRACT.md` **v0.2.0** (FROZEN). 엔드포인트(§5), 이벤트(§8), 식별정보 원칙(§4)을 하드 제약으로 준수.
> **범위**: 기술 비종속 비즈니스 흐름/오케스트레이션. 상세 규칙·검증은 `business-rules.md`, 데이터 정의는 `domain-entities.md` 참조.
> **답변 반영**: Q1=A, Q2=D, Q3=A, Q4=A, Q5=A, Q6=A, Q7=A, Q8=A, Q9=A, Q10=A.

---

## 0. 서비스 구성 (U2 내부, 3계층: Router → Service → Repository)

| 컴포넌트 | Service | 주요 협력 |
|---|---|---|
| C3 Order | `OrderService` | Menu(U1 조회), TableSessionService, RealtimeService, Order repo |
| C4 TableSession | `TableSessionService` | OrderHistoryService, RealtimeService, U1 `hash_password`, repos |
| C5 OrderHistory | `OrderHistoryService` | OrderHistory repo |
| C7 Realtime | `RealtimeService` | (메모리 pub/sub) |

식별정보 원칙(§4): 고객 API의 `store_id`/`table_no`는 **`verify_tablet_token`의 TabletContext만 신뢰**. body/query로 받지 않는다.

---

## 1. 주문 생성 (C3, `POST /api/orders`, US-C4) ⭐

**입력**: `TabletContext{store_id, table_no}` (Depends), body `{items:[{menu_id, qty}]}`.

```text
create_order(tablet, items):
  1. 검증(business-rules R-O1): items 비어있지 않음, 각 qty>=1
  2. 동일 menu_id 라인 병합(qty 합산)                        # Q2=D
  3. 각 menu_id를 U1 Menu 조회 → 유효성 + name/unit_price 스냅샷 확보
     └ 존재하지 않는 menu_id → 422 VALIDATION_ERROR (R-O2)
  4. total = Σ(unit_price * qty)                            # 정수(원)
  5. session = TableSessionService.get_or_start_session(store_id, table_no)  # 첫 주문이면 ACTIVE 시작
  6. order_no = 세션 내 다음 순번(#N)                        # Q1=A (R-O3)
  7. Order 저장(store_id/table_no ← TabletContext, session_id, order_no, status=PENDING, total, created_at)
     + OrderItem[] 저장(스냅샷 name/unit_price/qty)         # 단일 트랜잭션
  8. RealtimeService.publish(store_id, order.created{ order:{order_id=order.id, ...items} })  # §8
  9. return { order_no, session_id, total }                 # §5.3
```

- **order_id 일관성**: 8단계 payload의 `order.order_id`는 저장된 `orders.id`이며, 이후 PATCH/DELETE/관리자 상세와 동일 식별자(§8/§12).
- 실패(검증/조회) 시 저장·이벤트 없음. 세션은 저장 성공 후에만 확정(트랜잭션 경계는 rules R-TX1).

---

## 2. 현재 세션 주문 조회 (C3, `GET /api/orders/current`, US-C5)

```text
list_current_session_orders(tablet):
  1. session = 현재 ACTIVE 세션(store_id, table_no ← TabletContext)
     └ 없으면 빈 목록 []                                    # 첫 주문 전 / end-session 직후
  2. 해당 session_id의 orders 조회(시간순), 각 order에 items(name,qty,unit_price) 포함
  3. return [{order_no, created_at, status, total, items:[...]}]   # §5.3, 현재 세션만
```

- ENDED 세션/아카이브 주문은 제외(Q5=A: ACTIVE 세션 필터).

---

## 3. 주문 상태 변경 (C3, `PATCH /api/admin/orders/{order_id}/status`, US-A3) ⭐

**입력**: `AdminContext`, path `order_id`, body `{status}`.

```text
change_order_status(admin, order_id, status):
  1. status ∈ OrderStatus 검증(§6) 아니면 422                # R-O4
  2. order 로드(존재 + admin.store_id 소속) 아니면 404       # R-SEC1 (store 스코프)
  3. order.status = status (자유 전이 허용)                  # Q3=A
  4. 저장
  5. publish(store_id, order.status_changed{order_id, order_no, status})  # §8
  6. return 갱신된 order
```

- Q3=A: PENDING↔IN_PROGRESS↔DONE 자유 지정(전이 제약 없음). 잘못된 enum만 422.

---

## 4. 주문 삭제 (C3, `DELETE /api/admin/orders/{order_id}`, US-A4)

```text
delete_order(admin, order_id):
  1. order 로드(존재 + store 스코프) 아니면 404
  2. order + order_items 삭제
  3. new_table_total = 해당 세션 잔여 주문 total 합 재계산    # 삭제 후
  4. 세션은 ACTIVE 유지(비어도 종료 안 함)                    # Q4=A (R-S3)
  5. publish(store_id, order.deleted{order_id, session_id, new_table_total})  # §8
  6. return 204
```

---

## 5. 관리자 대시보드 테이블 목록 (C4, `GET /api/admin/tables`, US-A2)

```text
list_tables(admin):
  for each configured table (admin.store_id):
    session = 현재 ACTIVE 세션(있으면)
    current_total = Σ(active session orders.total) (없으면 0)      # Q6=A
    has_active_session = session is not None
    latest_orders = active session 주문 최신 3건                    # Q6=A
                    [{order_no, status, total, created_at}] (newest first)
  return [{table_no, current_total, has_active_session, latest_orders}]  # §5.4
```

- 설정된 모든 테이블이 포함(세션 없으면 total 0 / has_active_session=false / latest_orders=[]).

---

## 6. 관리자 테이블 주문 상세 (C3/C4, `GET /api/admin/tables/{table_no}/orders`, US-A2 연결)

```text
get_table_orders(admin, table_no):
  1. session = 현재 ACTIVE 세션(admin.store_id, table_no)
     └ 없으면 404 (활성 세션 없음)                            # §5.4
  2. return [{order_id, order_no, created_at, status, total, items:[{name,qty,unit_price}]}] (시간순)  # §5.4
```

- `order_id`는 §8/§5.4의 PATCH/DELETE와 **동일 식별자**(카드 클릭 → 상세 → 상태변경/삭제 연결).

---

## 7. 테이블 초기 설정 (C4, `POST /api/admin/tables`, US-A6)

```text
setup_table(admin, table_no, table_password):
  1. 검증: table_no 양의 정수, table_password 비어있지 않음     # R-T1
  2. (store_id, table_no) 중복 → 409 CONFLICT                  # R-T2
  3. password_hash = U1 common.hash_password(table_password)   # Q7=A / v0.2.0 §4
  4. TableConfig 저장(store_id ← AdminContext, table_no, password_hash)
  5. return 생성된 table config
```

- 태블릿 인증 세션 활성화는 U1 Auth 소관(U2는 config/hash 저장까지). 이용 세션과 무관(§9).
- **crypto 중복 구현 금지**: 반드시 U1 헬퍼 사용(계약 single-source 규칙).

---

## 8. 이용 세션 종료 / 이력화 (C4+C5, `POST /api/admin/tables/{table_no}/end-session`, US-A5)

```text
end_session(admin, table_no):
  1. session = 현재 ACTIVE 세션(store_id, table_no) 없으면 404
  2. completed_at = now (ISO8601 UTC)
  3. OrderHistoryService.archive_session_orders(session_id, completed_at):
       for each order in session:
         order_history insert {store_id, table_no, session_id, order_no, total,
                               items_json=JSON(items), ordered_at=order.created_at, completed_at}
  4. session.status='ENDED', session.ended_at=completed_at      # Q5=A 비파괴적
     (orders/order_items 행은 보존, ACTIVE 필터로 current에서 제외)
  5. publish(store_id, table_session.ended{session_id, completed_at})  # §8
  6. return {ended:true, session_id}
```

- 이후 같은 테이블 첫 주문 시 새 ACTIVE 세션 시작(get_or_start_session).
- **태블릿 로그아웃 유발 안 함**(§9 독립성).

---

## 9. 과거 이력 조회 (C5, `GET /api/admin/tables/{table_no}/history`, US-A5)

```text
list_history(admin, table_no, date_from?, date_to?):
  1. base = order_history(store_id, table_no)
  2. 날짜 필터(있으면): completed_at 기준, 양끝 inclusive        # Q8=A
     date-only 'YYYY-MM-DD' → 해당 일 전체 UTC 범위
     한쪽만 있으면 open-ended
  3. completed_at 역순 정렬
  4. return [{session_id, order_no, ordered_at, total, items, completed_at}]  # §5.4
```

---

## 10. Realtime pub/sub & SSE (C7, `GET /api/admin/orders/stream`, US-A2) ⭐

```text
publish(store_id, event):
  store_id 토픽 구독자(관리자 SSE 연결)들의 asyncio.Queue에 event push  # 동일 store만

subscribe(store_id) -> async generator:
  연결별 asyncio.Queue 생성 → 등록 → 큐에서 event yield → 종료 시 등록 해제

sse_stream(store_id, admin_context):   # Depends(verify_admin_token)
  Content-Type: text/event-stream
  loop:
    event 수신 → 프레임 출력  "event: <type>\n" + "data: <JSON>\n\n"    # §7 형식
    idle ~15s → heartbeat 주석 ": ping\n\n" 전송                        # Q9=A keep-alive
  연결 종료(클라이언트 disconnect) → 구독 해제, 큐 폐기
```

- **store 스코프 브로드캐스트**: 인증된 관리자의 `store_id` 이벤트만 수신(§7).
- **no replay / no Last-Event-ID**(Q9=A): 재연결은 클라이언트(F3 sseClient) 책임, 서버는 이벤트 미보관.
- 인증: `Authorization: Bearer <jwt>` (native EventSource 미사용, fetch 스트리밍 소비 — 클라이언트는 U3).

---

## 11. 서비스 상호작용 요약

```text
[고객] POST /api/orders ─▶ OrderService
   ├─ U1 verify_tablet_token → TabletContext (store/table 신뢰 출처)
   ├─ U1 Menu 조회(단가/유효성 스냅샷)
   ├─ TableSessionService.get_or_start_session
   ├─ Order repo 저장(트랜잭션)
   └─ RealtimeService.publish(order.created) ─▶ [관리자 SSE broadcast]

[관리자] PATCH/DELETE ─▶ OrderService ─▶ publish(order.status_changed / order.deleted)
[관리자] end-session  ─▶ TableSessionService ─▶ OrderHistoryService.archive + publish(table_session.ended)
[관리자] GET tables / tables/{no}/orders / history ─▶ TableSession/Order/History 조회
[관리자] SSE stream ◀─ RealtimeService (verify_admin_token, store 스코프)
```

---

## 12. 트랜잭션 & 오류 처리 개요
- 주문 생성: Order + OrderItem 저장은 **단일 트랜잭션**. 이벤트 publish는 커밋 성공 후(R-TX1).
- end-session: 아카이브 insert + 세션 ENDED는 단일 트랜잭션. publish는 커밋 후.
- 표준 에러(§4): 401/403/404/409/422. 상세 매핑은 `business-rules.md`.
- Realtime 실패는 주문 저장 트랜잭션을 롤백시키지 않는다(주문은 확정, 이벤트 전달은 best-effort; NFR-1 2초 이내는 정상 경로 목표).
