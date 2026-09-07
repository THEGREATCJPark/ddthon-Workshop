# Components (컴포넌트 정의)

> 아키텍처: 3계층(Router/API → Service → Repository) + SQLite, 도메인별 모듈. (Q1=A, Q2=A)
> 각 백엔드 도메인 컴포넌트는 내부적으로 Router / Service / Repository 하위 계층을 가진다.
> 상세 비즈니스 규칙·데이터 검증은 Functional Design(유닛별)에서 정의한다.

## 공통/기반 (Shared / Infrastructure)

### C0. Persistence (SQLite 기반)
- **목적**: DB 연결/세션 관리, 스키마 초기화, 시드 데이터 로딩, Repository 공통 기반.
- **책임**: SQLite 파일 연결, 테이블 생성, 트랜잭션, 시드(샘플 매장·관리자·메뉴·테이블) 주입.
- **인터페이스**: `get_connection()`, `init_db()`, `seed_if_empty()`.

### C7. Realtime (이벤트 브로커 + SSE)
- **목적**: 관리자 대시보드 실시간 갱신을 위한 인프로세스 pub/sub 및 SSE 스트리밍. (Q3=A)
- **책임**: 이벤트 토픽 관리(매장 단위), 구독자(관리자 SSE 연결) 관리, 이벤트 발행/브로드캐스트.
- **이벤트 유형**: `order.created`, `order.status_changed`, `order.deleted`, `table_session.ended`.
- **인터페이스**: `publish(store_id, event)`, `subscribe(store_id) -> async generator`, `sse_stream(store_id)`.

## 도메인 컴포넌트 (Backend)

### C1. Auth
- **목적**: 관리자 매장 인증(JWT 16h)과 테이블 태블릿 인증(자동 로그인 자격) 발급/검증.
- **책임**:
  - 관리자 로그인: 매장 식별자+사용자명+비밀번호 검증(bcrypt), JWT(16h) 발급, 로그인 시도 제한.
  - 태블릿 인증 세션: 테이블 번호+테이블 비밀번호로 태블릿 자동 로그인 토큰 발급/검증 (16h 유효, **테이블 이용 세션과 별개**).
  - 토큰 검증 의존성(FastAPI Depends)으로 보호 라우트 가드.
- **인터페이스**: `admin_login`, `verify_admin_token`, `tablet_login`, `verify_tablet_token`.

### C2. Menu
- **목적**: 메뉴 및 카테고리 관리/조회.
- **책임**: 카테고리별 조회, 등록/수정/삭제, 노출 순서 조정, 필수 필드·가격 범위 검증(상세는 Functional Design).
- **인터페이스**: `list_menus`, `create_menu`, `update_menu`, `delete_menu`, `reorder_menus`.

### C3. Order
- **목적**: 주문 생성/조회/상태변경/삭제.
- **책임**:
  - 주문 생성(장바구니 항목 검증, 총액 계산, 세션 연결, 저장, 이벤트 발행). **store_id/table_no는 요청 body가 아니라 `verify_tablet_token`으로 얻은 TabletContext에서 서버가 결정**한다(아래 식별정보 원칙 참조).
  - 현재 테이블 이용 세션 주문 조회(고객), 상태 변경(대기중/준비중/완료), 직권 삭제.
- **식별정보 원칙 (Source of Truth)**: 고객 보호 API에서 `store_id`/`table_no`의 신뢰 가능한 출처는 **인증 컨텍스트(TabletContext)뿐**이다. 클라이언트는 `tablet_token`을 `Authorization: Bearer`로만 전달하며, 주문 body나 조회 파라미터로 store/table 식별정보를 신뢰 입력으로 받지 않는다.
- **인터페이스**: `create_order`, `list_current_session_orders`, `change_order_status`, `delete_order`.

### C4. TableSession
- **목적**: 테이블 **이용(주문) 세션** 라이프사이클과 테이블 구성/초기 설정 관리.
- **책임**:
  - 테이블 초기 설정(번호·비밀번호 등록 → 태블릿 인증 활성화는 Auth와 협력).
  - 이용 세션 시작(첫 주문 시), 종료(이용 완료 → OrderHistory 이동 트리거, 현재 주문/총액 0 리셋).
  - 테이블별 현재 총 주문액 집계.
  - **주의**: 여기서의 세션 = 고객 이용 세션이며, Auth의 태블릿 인증 세션과 독립적.
- **인터페이스**: `setup_table`, `get_or_start_session`, `end_session`, `get_table_totals`, `list_tables`.

### C5. OrderHistory
- **목적**: 종료된 이용 세션의 과거 주문 이력 저장/조회.
- **책임**: 세션 종료 시 주문을 이력으로 이동(세션 ID 그룹화, 완료 시각 기록), 테이블별 역순 조회, 날짜 필터.
- **인터페이스**: `archive_session_orders`, `list_history`, `filter_history_by_date`.

## 프론트엔드 컴포넌트 (Static, Vanilla JS — Q5=A)

### F1. CustomerApp (`/`)
- **목적**: 고객 태블릿 UI.
- **책임**: 자동 로그인, 메뉴 조회(카드형/카테고리), 장바구니(localStorage), 주문 생성/성공 플로우, 현재 세션 주문 내역.

### F2. AdminApp (`/admin`)
- **목적**: 관리자 UI.
- **책임**: 로그인, SSE 실시간 대시보드(테이블 그리드/강조/필터), 주문 상세, 상태 변경/삭제, 테이블 세션 종료·과거 이력, 메뉴 관리.

### F3. Shared JS Utils
- **목적**: 프론트 공통 유틸.
- **책임**: `apiClient`(fetch 래퍼, Bearer 토큰 첨부 — Q4=A), `sseClient`(**fetch 기반 `text/event-stream` 스트리밍 리더**), 포맷 유틸.
- **SSE 클라이언트 방식**: 관리자 인증이 `Authorization: Bearer` 헤더(Q4=A 유지)이므로, native `EventSource`(헤더 설정 불가) 대신 **`fetch()` + `ReadableStream` 리더로 `text/event-stream`을 파싱**한다. 이렇게 하면 SSE 이벤트 스트림을 유지하면서 Authorization 헤더로 관리자 토큰을 전달할 수 있다. 엔드포인트(`GET /api/admin/orders/stream`)와 SSE 요구사항은 변경하지 않는다.
