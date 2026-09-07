# U3 Frontend — Business Logic Model (Client-side Workflows)

> U3의 클라이언트 측 로직/흐름을 정의한다. 백엔드 계약(FROZEN v0.1.0)의 API/이벤트를 소비만 하며, 새 요구사항을 추가하지 않는다.
> 결정 근거는 각 흐름에 `(Q#)` 로 표기.

---

## 1. 앱 셸 / 라우팅 (Q1=A, Q3=A)

- 앱당 **단일 HTML**(`frontend/customer/index.html`, `frontend/admin/index.html`) + 모듈 스코프 `state` 객체.
- `render()` 가 `state.view` 에 따라 해당 뷰만 그린다(뷰 전환 = 상태 변경 + `render()`).
- 렌더는 **템플릿 문자열 + `innerHTML`**(Q2=A). 사용자/서버 유래 문자열(메뉴명·설명 등)은 `escapeHtml()` 유틸로 이스케이프.
- 상태 변경 → 명시적 `render()` 호출(자동 반응성 없음).

---

## 2. F1 고객 — 자동 로그인 / 재인증 (Q4=A, Q20=D / FR-C1)

```
onLoad:
  auth = localStorage.get("to_customer_auth")
  if auth?.tablet_token and now < auth.expires_at:
      state.authed = true ; loadMenu()          # 유효 토큰 → 자동 로그인(16h 내)
  else:
      discard expired tablet_token
      state.view = "auth" ; render()             # 재인증 화면(관리자 초기설정 겸용)
      prefill(store_id, table_no) from auth?.config   # 입력 편의만; table_password 프리필·저장 안 함

authSubmit(store_id, table_no, table_password):
  res = POST /api/tablet/login → {tablet_token, expires_at}
  save "to_customer_auth" {tablet_token, expires_at, config:{store_id, table_no}}
  state.view = "menu" ; loadMenu()
```
- **자동 재발급 없음**: 만료/401 시 저장 자격으로 조용히 재로그인하지 않으며, 재인증 화면에서 사용자의 명시적 재로그인만 새 토큰을 발급한다(무한 루프 방지). (Q20=D)

## 3. F1 고객 — 메뉴 조회 (Q7=A / US-C2)

```
loadMenu:
  menus = GET /api/menus            # tablet Bearer, display_order 정렬
  categories = distinct(menus.category)
  render 상단 카테고리 탭(ALL + 각 카테고리)
  render 활성 카테고리의 카드 그리드(이미지/이름/가격/설명)
  이미지 로드 실패 → 공통 플레이스홀더로 교체 (Q10=A, img.onerror)
```

## 4. F1 고객 — 장바구니 (Q5=C, Q6=B, Q8=A / US-C3)

```
cart.load(): read "to_cart"; if store/table meta != current context → cart.clear()
cart.add(menu): items에 동일 menu_id 있으면 qty+1, 없으면 {menu_id,name,unit_price,qty:1} 추가; persist; render 하단 바
cart.updateQty(menu_id, delta): qty += delta; qty<=0 이면 항목 제거; persist
cart.remove(menu_id) / cart.clear(): persist
total = Σ(unit_price*qty)  # 렌더 시 계산, 하단 고정 바에 총액·개수 표시(탭하면 상세 펼침)
```
- 서버 전송은 **주문 확정 시에만**. 장바구니는 새로고침에도 유지(localStorage).

## 5. F1 고객 — 주문 생성 (Q9=A / US-C4)

```
submitOrder:
  if cart.items empty: toast("장바구니가 비어있습니다","error"); return
  body = { items: cart.items.map({menu_id, qty}) }        # store/table 미포함(계약 §5.3)
  try res = POST /api/orders                                # → {order_no, session_id, total}
     state.lastOrderNo = res.order_no
     cart.clear()
     state.view = "orderSuccess" ; render()                 # 주문번호 표시
     setTimeout(5000): state.view="menu"; render()          # 5초 후 자동 리다이렉트
  catch e:
     toast(errorMessage(e), "error")                        # 실패: 메시지 표시
     # 장바구니 유지 (clear 안 함)
```

## 6. F1 고객 — 현재 세션 주문 내역 (Q11=A / US-C5)

```
openOrderHistory: state.view="orderHistory"; orders = GET /api/orders/current; render(시간순)
  각 주문: order_no, 시각(포맷), items(name×qty), total, status 라벨
  (실시간 SSE 푸시는 고객 화면 범위 아님 — 진입/새로고침 시 조회)
```

---

## 7. F2 관리자 — 로그인 (US-A1)

```
login(store_id, username, password):
  res = POST /api/admin/login → {access_token, expires_at}
  save "to_admin_auth" {token, expires_at, store_id, username}
  state.view="dashboard"; initDashboard()
  429 → toast("로그인 시도가 제한되었습니다","error")
```

## 8. F2 관리자 — 실시간 대시보드 (Q12=A, Q14=B, Q17=A / US-A2)

```
initDashboard:
  tables = GET /api/admin/tables → state.tables
  renderTableGrid(filter=state.tableFilter)   # 칩 다중선택, empty=전체
  sseConnect()

sseConnect (F3 sseClient, fetch+Bearer):
  onEvent(order.created):      upsert table card; recompute; highlight(table_no) ; renderTableGrid()
  onEvent(order.status_changed): if detail open for that table → update row; refresh card
  onEvent(order.deleted):      update new_table_total; refresh card/detail
  onEvent(table_session.ended): reset table card(총액 0, orders 비움); if detail open → close
  onError/onClose: schedule reconnect after 3s (고정 간격)   # Q17=A

highlight(table_no): state.highlight[table_no]=now+N; 카드에 하이라이트 클래스 → CSS 트랜지션으로 페이드아웃  # Q12=A
```
- 신규 주문 반영은 SSE 수신 즉시(요구 NFR-1: 2초 이내).

## 9. F2 관리자 — 테이블 상세 / 상태변경 / 삭제 (Q13=A, Q15=A / US-A2·A3·A4)

```
openTableDetail(table_no): orders = GET /api/admin/tables/{table_no}/orders; state.openTableDetail=table_no; renderDetailModal
changeStatus(order_id, status): PATCH /api/admin/orders/{order_id}/status {status} → refresh detail+card; toast 성공  # 버튼 3개 중 선택
deleteOrder(order_id):
  confirmModal("주문을 삭제할까요?")  → 확인 시                      # 커스텀 모달
      DELETE /api/admin/orders/{order_id} → (order.deleted 이벤트로 총액 갱신) refresh; toast 성공
```

## 10. F2 관리자 — 세션 종료 / 과거 이력 (Q15=A, Q16=B / US-A5)

```
endSession(table_no):
  confirmModal("이용 완료 처리할까요? 현재 주문이 이력으로 이동합니다.") → 확인 시
      POST /api/admin/tables/{table_no}/end-session → (table_session.ended 이벤트) reset card; toast

openHistory(table_no):
  range = 기본 프리셋(오늘)                                          # Q16=B 프리셋+커스텀
  data = GET /api/admin/tables/{table_no}/history?date_from&date_to
  renderHistoryModal(역순): order_no, ordered_at(원 주문시각), items, total, completed_at
  프리셋(오늘/어제/최근7일) 또는 커스텀 from/to 변경 시 재조회
  "닫기" → 대시보드 복귀
```

## 11. F2 관리자 — 메뉴 관리 (US-A7)

```
menuAdmin.list(category?): GET /api/admin/menus → 카테고리별 표시
menuAdmin.create(form): 검증 통과 시 POST /api/admin/menus → 목록 갱신; toast
menuAdmin.update(id, patch): PATCH /api/admin/menus/{id}
menuAdmin.delete(id): confirmModal → DELETE /api/admin/menus/{id} (204)
menuAdmin.reorder(ordered_ids): POST /api/admin/menus/reorder {ordered_ids} (204)
```

---

## 12. 횡단 관심사

- **apiClient (F3)**: `request(method, path, body?, {auth})` — 저장된 토큰을 `Authorization: Bearer` 로 자동 첨부, JSON 직렬화/역직렬화, 비2xx는 `{code,message}` 포함 에러 throw.
- **401 처리 (Q20=D)**: 관리자 → `access_token` 폐기 + 로그인 화면; 고객 → 만료 `tablet_token` 폐기 + 재인증 화면(`store_id`/`table_no` 프리필). 자동 재발급·`table_password` 저장 없음.
- **피드백 (Q18=A)**: 성공/실패는 토스트(자동 소멸). 파괴적 동작(삭제/세션 종료)은 커스텀 확인 모달(Q15=A).
- **반응형 (Q19=A)**: 고객 = 태블릿 가로 고정 레이아웃, 관리자 = 데스크톱 그리드 기준.
- **SSE 인증**: native `EventSource` 대신 `fetch()+ReadableStream` 리더로 `text/event-stream` 파싱(계약 §7).
