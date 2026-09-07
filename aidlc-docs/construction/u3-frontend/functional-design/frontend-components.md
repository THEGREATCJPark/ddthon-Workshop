# U3 Frontend — Components

> U3 소유 경로: `frontend/customer/`, `frontend/admin/`, `frontend/shared/` (계약 §U3).
> 각 컴포넌트는 계약의 API/이벤트만 소비하며 새 요구사항을 만들지 않는다. `(Q#)` 는 설계 근거.

---

## F3 — Shared JS (`frontend/shared/`)

### `apiClient`
- `request(method, path, body?, { auth })` — 저장된 토큰을 `Authorization: Bearer` 로 자동 첨부, JSON 직렬화/역직렬화.
- 비2xx 응답은 `{ code, message }` 를 포함한 에러로 throw.
- 401 수신 시 역할별 핸들러 트리거(관리자=로그아웃, 고객=재인증). **자동 재발급 없음.** (Q20=D)

### `sseClient`
- `connect(url, token, { onEvent, onOpen, onError })` — native `EventSource` 대신 `fetch()` + `ReadableStream` 으로 `text/event-stream` 파싱 (계약 §7).
- 이벤트 프레임(`event:` / `data:`) 파싱 후 타입별 `onEvent` 디스패치.
- 끊김 시 **3초 고정 간격** 재연결. (Q17=A)

### format utils
- `formatCurrency(int)`, `formatDateTime(iso)`, `escapeHtml(str)`, `statusLabel(OrderStatus)`.

---

## F1 — CustomerApp (`frontend/customer/`, route `/`)

- 단일 `index.html` + 모듈 스코프 `state` + `render()` 로 뷰 전환. (Q1=A, Q3=A)
- 뷰: `auth`(재인증) · `menu` · `orderSuccess` · `orderHistory`  ← Q20=D 로 `auth` 뷰 추가.

| 컴포넌트/모듈 | 책임 | 소비 API / 저장소 | 근거 |
|---|---|---|---|
| `authView` | 유효 토큰이면 자동 진입, 만료/401 시 재인증 폼(store/table 프리필, 비밀번호 재입력) | `POST /api/tablet/login` | Q4, Q20=D |
| `menuView` (`renderMenu`) | 상단 카테고리 탭 + 카드 그리드, 이미지 폴백 | `GET /api/menus` | Q7, Q10 |
| `cart` (`add`/`updateQty`/`remove`/`clear`) | 하단 고정 바(요약→상세), localStorage 저장/스냅샷 | `localStorage(to_cart)` | Q5, Q6, Q8 |
| `submitOrder` | 주문 확정, 성공 화면 표시 후 5초 뒤 리다이렉트 | `POST /api/orders` | Q9 |
| `orderHistoryView` (`renderOrderHistory`) | 현재 세션 주문 내역 조회(뷰 전환) | `GET /api/orders/current` | Q11 |

## F2 — AdminApp (`frontend/admin/`, route `/admin`)

- 단일 `index.html` + `state` + `render()`; 뷰: `login` · `dashboard` · `menuAdmin`. (Q1=A, Q3=A)

| 컴포넌트/모듈 | 책임 | 소비 API / 이벤트 | 근거 |
|---|---|---|---|
| `loginView` (`login`) | 관리자 로그인, 401/만료 시 토큰 폐기 후 복귀 | `POST /api/admin/login` | Q4, Q20=D |
| `dashboard` (`initDashboard`, `renderTableGrid`) | 테이블 카드 그리드, 칩 다중 필터, 신규주문 하이라이트, SSE 구독 | `GET /api/admin/tables`, SSE `/api/admin/orders/stream` | Q12, Q14, Q17 |
| `tableDetail` (`openTableDetail`) | 카드 클릭 시 주문 상세 모달 | `GET /api/admin/tables/{table_no}/orders` | Q15 계열 |
| `changeStatus` | 3버튼 상태 변경(현재 상태 강조) | `PATCH /api/admin/orders/{order_id}/status` | Q13 |
| `deleteOrder` | 확인 모달 후 삭제, 총액 갱신 | `DELETE /api/admin/orders/{order_id}` → `order.deleted` | Q15 |
| `endSession` | 확인 모달 후 세션 종료, 카드 리셋 | `POST /api/admin/tables/{table_no}/end-session` → `table_session.ended` | Q15 |
| `historyView` (`openHistory`) | 프리셋+커스텀 날짜 이력 조회 모달 | `GET /api/admin/tables/{table_no}/history?date_from&date_to` | Q16 |
| `menuAdmin` (`list`/`create`/`update`/`delete`/`reorder`) | 메뉴 CRUD + 노출 순서 | `GET/POST/PATCH/DELETE /api/admin/menus`, `POST .../menus/reorder` | US-A7 |

## 공통 UI 요소

- `toast(type, text)` — 성공/실패 자동소멸 알림. (Q18=A)
- `confirmModal(text)` — 파괴적 동작 확인. (Q15=A)
- `placeholderImage` — 이미지 폴백. (Q10=A)
- 레이아웃: 고객 = 태블릿 가로 고정, 관리자 = 데스크톱. (Q19=A)
