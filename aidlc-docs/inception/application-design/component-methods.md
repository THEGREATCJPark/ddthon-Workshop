# Component Methods (메서드 시그니처)

> 상위 목적과 입출력 타입 중심. **상세 비즈니스 규칙/검증 로직은 Functional Design(유닛별)에서 정의**한다.
> 표기는 Python 타입 힌트 스타일(개념적). 실제 요청/응답은 Pydantic 모델로 구체화 예정.

## C1. Auth
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| admin_login | `admin_login(store_id: str, username: str, password: str) -> {access_token, expires_at}` | 관리자 인증, JWT(16h) 발급. bcrypt 검증 + 로그인 시도 제한 |
| verify_admin_token | `verify_admin_token(token: str) -> AdminContext` | JWT 검증, 만료 시 401 |
| tablet_login | `tablet_login(store_id: str, table_no: int, table_password: str) -> {tablet_token, expires_at}` | 태블릿 자동 로그인 자격(16h) 발급 |
| verify_tablet_token | `verify_tablet_token(token: str) -> TabletContext(store_id, table_no)` | 태블릿 토큰 검증. 반환된 TabletContext는 **고객 보호 API의 store_id/table_no 신뢰 출처(Source of Truth)** 로 사용 |

## C2. Menu
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| list_menus | `list_menus(store_id: str, category: str | None) -> list[Menu]` | 카테고리별/전체 조회(노출 순서 정렬) |
| create_menu | `create_menu(store_id, MenuCreate) -> Menu` | 메뉴 등록(필수 필드·가격 검증) |
| update_menu | `update_menu(menu_id, MenuUpdate) -> Menu` | 메뉴 수정 |
| delete_menu | `delete_menu(menu_id) -> None` | 메뉴 삭제 |
| reorder_menus | `reorder_menus(store_id, ordered_ids: list[int]) -> None` | 노출 순서 조정 |

## C3. Order
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| create_order | `create_order(tablet: TabletContext, items: list[{menu_id, qty}]) -> OrderResult{order_no, session_id, total}` | 주문 생성. **store_id/table_no는 요청 body가 아니라 인증 컨텍스트(TabletContext)에서 결정** — body는 `items`만. 검증→총액계산→세션 연결(없으면 시작)→저장(store/table은 TabletContext로 채움)→`order.created` 발행 |
| list_current_session_orders | `list_current_session_orders(tablet: TabletContext) -> list[Order]` | 현재 이용 세션 주문만, 시간순. **store_id/table_no는 TabletContext에서 결정**(쿼리 파라미터로 받지 않음) |
| change_order_status | `change_order_status(order_id, status: OrderStatus) -> Order` | 대기중/준비중/완료 전이 → `order.status_changed` 발행 |
| delete_order | `delete_order(order_id) -> None` | 직권 삭제 → 총액 재계산 → `order.deleted` 발행 |

- `OrderStatus = Enum('PENDING'|'IN_PROGRESS'|'DONE')` (대기중/준비중/완료)

## C4. TableSession
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| setup_table | `setup_table(store_id, table_no: int, table_password: str) -> Table` | 테이블 구성 등록(비밀번호 해싱), 태블릿 인증 활성화 준비 |
| list_tables | `list_tables(store_id) -> list[TableView{table_no, current_total, has_active_session, latest_orders}]` | 대시보드 그리드용 테이블 목록 |
| get_or_start_session | `get_or_start_session(store_id, table_no) -> TableSession` | 활성 이용 세션 반환, 없으면 새로 시작(첫 주문) |
| end_session | `end_session(store_id, table_no) -> None` | 이용 완료: OrderHistory 이동 트리거 + 현재 주문/총액 0 리셋 (태블릿 인증에는 영향 없음) |
| get_table_totals | `get_table_totals(store_id, table_no) -> {current_total}` | 테이블 현재 총액 |

## C5. OrderHistory
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| archive_session_orders | `archive_session_orders(session_id, completed_at) -> None` | 세션 주문을 이력으로 이동(그룹화·완료시각 기록) |
| list_history | `list_history(store_id, table_no) -> list[OrderHistory]` | 테이블별 과거 주문 역순 |
| filter_history_by_date | `filter_history_by_date(store_id, table_no, date_from, date_to) -> list[OrderHistory]` | 날짜 필터 조회 |

## C7. Realtime
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| publish | `publish(store_id: str, event: Event{type, payload}) -> None` | 이벤트 발행 |
| subscribe | `subscribe(store_id) -> AsyncGenerator[Event]` | 구독(관리자 연결당 큐) |
| sse_stream | `sse_stream(store_id, admin_context) -> EventSourceResponse` | SSE 응답 스트림 |

## C0. Persistence
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| init_db | `init_db() -> None` | 스키마 생성 |
| seed_if_empty | `seed_if_empty() -> None` | 시드 데이터 주입(비어있을 때만) |
| get_connection | `get_connection() -> Connection` | DB 연결/세션 |

## 프론트엔드 주요 함수(개념)
- **F3 apiClient**: `request(method, path, body?, {auth})` — Bearer 토큰 자동 첨부, JSON 처리.
- **F3 sseClient**: `connect(url, token, onEvent)` — **fetch 기반 `text/event-stream` 스트리밍 리더**(native EventSource 대신). `fetch(url, {headers:{Authorization:`Bearer ${token}`}})` 응답의 `ReadableStream`을 읽어 SSE 프레임을 파싱하고 이벤트 타입별 콜백 호출. 재연결 로직 포함.
- **F1 CustomerApp**: `renderMenu()`, `cart.add/remove/updateQty/clear()`(localStorage), `submitOrder()`, `renderOrderHistory()`.
- **F2 AdminApp**: `login()`, `initDashboard()`(SSE 구독), `renderTableGrid()`, `openTableDetail()`, `changeStatus()`, `deleteOrder()`, `endSession()`, `openHistory()`, `menuAdmin.*`.
