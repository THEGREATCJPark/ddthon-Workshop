# Services (서비스 계층 정의 및 오케스트레이션)

> 3계층 구조에서 Service는 Router와 Repository 사이에서 비즈니스 흐름을 오케스트레이션한다.
> 대부분 도메인 컴포넌트가 자체 Service를 가지며, 일부 흐름은 여러 컴포넌트를 협력시킨다.

## 도메인 서비스

### AuthService
- 관리자 인증(bcrypt 검증, JWT 발급, 로그인 시도 제한), 태블릿 인증 자격 발급/검증.
- 의존: Persistence(Store/AdminUser/Table repo).

### MenuService
- 메뉴 CRUD·정렬·검증. 의존: Persistence(Menu repo).

### OrderService (핵심 오케스트레이션)
- **식별정보 원칙**: 고객 API의 `store_id`/`table_no`는 **인증 컨텍스트(TabletContext)가 유일한 신뢰 출처**다. 요청 body는 `items`만 담고, store/table 식별정보를 신뢰 입력으로 받지 않는다.
- **주문 생성 흐름**:
  1. `Depends(verify_tablet_token)`로 얻은 **TabletContext(store_id, table_no)** 를 authoritative 값으로 확정 (body에는 items만)
  2. items의 menu 유효성·단가 조회(MenuService/Menu repo)
  3. 총액 계산
  4. 활성 이용 세션 확보(TableSessionService.get_or_start_session — 첫 주문이면 세션 시작)
  5. Order/OrderItem 저장 — store/table 식별정보는 **서버가 TabletContext에서 채움**(Order repo)
  6. `order.created` 이벤트 발행(RealtimeService)
- **현재 세션 조회**: `list_current_session_orders`도 동일 원칙 — TabletContext의 store_id/table_no로 현재 이용 세션 주문만 반환(쿼리 파라미터로 식별정보 미수신).
- **상태 변경/삭제**: 저장 후 `order.status_changed`/`order.deleted` 발행, 삭제 시 테이블 총액 재계산(TableSessionService).
- 의존: AuthService, MenuService, TableSessionService, RealtimeService, Persistence(Order repo).

### TableSessionService
- 테이블 초기 설정, 이용 세션 시작/종료, 총액 집계.
- **세션 종료 흐름**: 활성 세션 주문을 OrderHistoryService.archive_session_orders로 이동 → 현재 주문/총액 0 리셋 → `table_session.ended` 발행.
- 의존: OrderHistoryService, RealtimeService, Persistence(Table/TableSession/Order repo).

### OrderHistoryService
- 세션 주문 아카이빙, 과거 이력 조회·날짜 필터.
- 의존: Persistence(OrderHistory repo).

### RealtimeService
- 인프로세스 pub/sub 브로커. 매장 단위 토픽, 관리자 연결별 asyncio 큐 관리. 이벤트 발행 시 해당 매장 구독자에게 브로드캐스트. SSE 스트림 제공.
- 의존: 없음(메모리). 주의: 단일 프로세스 로컬 실행 전제.

## 서비스 상호작용 요약
```
[Customer] --create_order--> OrderService
    OrderService -> AuthService(verify tablet) 
    OrderService -> MenuService(price lookup)
    OrderService -> TableSessionService(get_or_start_session)
    OrderService -> Order repo(save)
    OrderService -> RealtimeService.publish(order.created)
                                   |
[Admin SSE] <==== sse_stream <==== RealtimeService (broadcast)

[Admin] --change_status/delete--> OrderService -> RealtimeService.publish(...)
[Admin] --end_session--> TableSessionService -> OrderHistoryService.archive + RealtimeService.publish(table_session.ended)
[Admin] --menu CRUD--> MenuService
[Admin] --history--> OrderHistoryService
```

## 인증/가드
- 관리자 보호 라우트: `Depends(verify_admin_token)`.
- 관리자 SSE 라우트(`GET /api/admin/orders/stream`): 동일하게 `Depends(verify_admin_token)`로 보호하며 `Authorization: Bearer`로 토큰 수신. 프론트는 native EventSource가 헤더를 못 넣으므로 **fetch 기반 text/event-stream 스트리밍**으로 소비(sseClient).
- 고객 주문/조회 라우트: `Depends(verify_tablet_token)`. 반환 TabletContext의 store_id/table_no만 신뢰(식별정보 원칙).
- 토큰 전달: `Authorization: Bearer <jwt|tablet_token>` (Q4=A).
