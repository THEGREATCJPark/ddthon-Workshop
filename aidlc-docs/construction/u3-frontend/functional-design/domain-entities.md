# U3 Frontend — Domain Entities (Client-side)

> U3는 백엔드 도메인 엔티티를 소유하지 않는다. 여기서는 **프론트가 메모리/`localStorage`에서 다루는 클라이언트 측 데이터 구조**를 정의한다.
> 서버 계약 필드는 FROZEN Integration Contract v0.1.0(§3/§5/§8)을 그대로 따르며, 프론트는 이를 **표시/입력용으로만** 보관한다.
> 관련 답변: Q4(토큰=localStorage), Q5(cart 단일키+store/table 메타), Q6(cart에 name·unit_price 보관).

---

## 1. 인증/세션 상태

### CustomerAuthState (F1) — `localStorage`
```text
CustomerAuthState = {
  tablet_token: str,          # Bearer 로 사용
  expires_at: str,            # ISO 8601, 만료 판단용
  config: {                   # 재인증 화면 입력 프리필용 (table_password 는 저장하지 않음)
    store_id: int,
    table_no: int
  }
}
```
- 저장 키: `to_customer_auth`
- 자동 로그인: 앱 로드 시 `tablet_token` 이 유효(`now < expires_at`)하면 그대로 사용(16h 내 새로고침·재실행 유지).
- 만료/부재 또는 401 시: `tablet_token` **삭제** → 재인증 화면. `config.store_id`/`table_no` 는 프리필로만 사용하고 **`table_password` 저장·자동 재발급은 하지 않는다 (Q20=D)**.

### AdminAuthState (F2) — `localStorage`
```text
AdminAuthState = {
  access_token: str,          # JWT, Bearer 로 사용
  expires_at: str,            # ISO 8601 (16h)
  store_id: int,
  username: str
}
```
- 저장 키: `to_admin_auth`
- 401/만료 시 `access_token` 삭제 → 로그인 화면 전환 (Q20=D).

---

## 2. 장바구니 (F1) — `localStorage`

```text
CartItem = { menu_id: int, name: str, unit_price: int, qty: int }

Cart = {
  store_id: int,              # 저장 시점 TabletContext 스냅샷 (Q5=C)
  table_no: int,
  items: CartItem[]
}
```
- 저장 키: `to_cart` (단일 키, Q5=C)
- `name`/`unit_price`는 **표시·주문확인용 스냅샷**(Q6=B). 서버 전송 시엔 `{menu_id, qty}`만 사용.
- `store_id`/`table_no` 가 현재 TabletContext와 불일치하면 장바구니를 **자동 초기화**.
- 파생값 `total = Σ(unit_price × qty)` 는 저장하지 않고 렌더 시 계산.

---

## 3. 메뉴 (F1/F2 표시 모델)

```text
MenuItemView = {
  id: int, category: str, name: str, price: int,
  description: str | null, image_url: str | null, display_order: int
}
```
- 출처: `GET /api/menus`(고객) / `GET /api/admin/menus`(관리자). `display_order` 오름차순 정렬.
- 카테고리 목록은 `menus[].category` 의 distinct 집합에서 파생.

### 메뉴 관리 폼 모델 (F2)
```text
MenuFormModel = { category: str, name: str, price: int, description?: str, image_url?: str }
```

---

## 4. 고객 주문 내역 (F1) — 현재 세션

```text
CustomerOrderView = {
  order_no: str, created_at: str, status: OrderStatus, total: int,
  items: { name: str, qty: int, unit_price: int }[]
}
OrderStatus = "PENDING" | "IN_PROGRESS" | "DONE"     # 표시 라벨은 §business-rules 매핑
```
- 출처: `GET /api/orders/current`. 시간순.

---

## 5. 관리자 대시보드 (F2)

```text
AdminTableCard = {
  table_no: int, current_total: int, has_active_session: bool,
  latest_orders: OrderPreview[]         # 최신 n개 미리보기
}
OrderPreview = { order_no: str, total: int, item_summary: str }   # 축약 표시용(프론트 파생)

AdminOrderDetail = {
  order_id: int, order_no: str, created_at: str,
  status: OrderStatus, total: int,
  items: { name: str, qty: int, unit_price: int }[]
}
```
- `AdminTableCard` 출처: `GET /api/admin/tables`.
- `AdminOrderDetail` 출처: `GET /api/admin/tables/{table_no}/orders` (카드 클릭 시).
- `order_id` 는 `PATCH/DELETE /api/admin/orders/{order_id}` 및 `order.created` 이벤트의 `order_id`와 **동일 식별자**(계약 §5.4/§8).

### 과거 이력
```text
HistoryEntry = {
  session_id: int, order_no: str, ordered_at: str,
  total: int, items: {name,qty,unit_price}[], completed_at: str
}
```
- 출처: `GET /api/admin/tables/{table_no}/history?date_from&date_to`. 역순.

---

## 6. 클라이언트 UI 상태 (메모리, 비영속)

```text
CustomerUiState = {
  view: "auth" | "menu" | "orderSuccess" | "orderHistory",   # 단일 HTML 뷰전환 (Q1=A); auth=재인증 (Q20=D)
  activeCategory: str | "ALL",                       # 상단 탭 (Q7=A)
  cartExpanded: bool,                                # 하단 바 펼침 (Q8=A)
  lastOrderNo: str | null                            # 주문 성공 화면 표시용 (Q9=A)
}

AdminUiState = {
  view: "login" | "dashboard" | "menuAdmin",
  tables: Map<table_no, AdminTableCard>,
  tableFilter: Set<int>,                             # 다중 선택 칩 (Q14=B), empty=전체
  openTableDetail: table_no | null,                  # 상세 모달 (Q15=A 계열 모달)
  sse: { connected: bool, retryTimer: id | null },   # 고정 3초 재시도 (Q17=A)
  highlight: Map<table_no, until_ts>                 # 신규주문 강조 페이드 (Q12=A)
}

Toast = { id: int, type: "success" | "error" | "info", text: str, ttl_ms: int }   # Q18=A
```
