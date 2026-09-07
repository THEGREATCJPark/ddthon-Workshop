# Application Design (통합본)

> 본 문서는 `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`를 통합 요약한 것입니다.
> 상세는 각 문서를 참조하세요.

## 1. 설계 결정 요약
| 항목 | 결정 |
|---|---|
| 아키텍처 스타일 | 3계층: Router/API → Service → Repository + SQLite (Q1=A) |
| 컴포넌트 경계 | 도메인별 모듈: Auth, Menu, Order, TableSession, OrderHistory, Realtime + 기반 Persistence (Q2=A) |
| 실시간 | 인프로세스 이벤트 브로커(in-memory pub/sub) + FastAPI SSE (Q3=A) |
| 인증 전달 | JWT 응답 본문 발급 + `Authorization: Bearer` 헤더 (Q4=A) |
| 프론트엔드 | FastAPI 정적 서빙 2페이지(`/` 고객, `/admin` 관리자) + 공통 JS 유틸 (Q5=A) |

## 2. 컴포넌트 개요
- **C0 Persistence** — SQLite 연결/스키마/시드/Repository 기반.
- **C1 Auth** — 관리자 JWT(16h, bcrypt, 시도 제한) + 태블릿 인증 세션(자동 로그인, 이용 세션과 별개).
- **C2 Menu** — 메뉴/카테고리 CRUD·정렬·검증.
- **C3 Order** — 주문 생성/조회/상태변경/삭제 (오케스트레이션 허브).
- **C4 TableSession** — 테이블 초기 설정, **이용(주문) 세션** 시작/종료, 총액 집계.
- **C5 OrderHistory** — 세션 종료 시 과거 이력 이동/조회/날짜 필터.
- **C7 Realtime** — 매장 단위 이벤트 pub/sub + SSE 스트림.
- **F1 CustomerApp / F2 AdminApp / F3 Shared JS** — 프론트엔드.

## 3. 세션 개념 구분 (중요)
- **이용(주문) 세션** [C4]: 고객 첫 주문~이용 완료까지의 영업 라이프사이클. 종료 시 주문을 이력화하고 테이블 현재 상태를 리셋.
- **태블릿 인증 세션** [C1]: 디바이스 자동 로그인 자격(16h). 이용 세션의 시작/종료와 **독립적**.
- 두 세션은 서로 다른 개념·라이프사이클이며 하나가 다른 하나를 함께 시작/종료시키지 않는다.

## 4. 서비스 오케스트레이션 (핵심 흐름)
주문 생성: 태블릿 인증 검증 → 메뉴/단가 조회 → 총액 계산 → 이용 세션 확보(없으면 시작) → 저장 → `order.created` 발행 → 관리자 SSE push.
상태 변경/삭제: 저장 → 이벤트 발행(삭제 시 총액 재계산).
세션 종료: 이력 이동 → 현재 주문/총액 0 리셋 → `table_session.ended` 발행.

## 5. 의존성 요약
- 기반: 모든 도메인 → C0 Persistence.
- 오케스트레이션: C3 Order → C1/C2/C4/C7.
- C4 TableSession → C5 OrderHistory, C7 Realtime.
- 순환 의존 없음. (상세 매트릭스·데이터 흐름도는 `component-dependency.md`)

## 6. API 표면(개요, 상세는 Functional Design/Code Generation에서 확정)
- 고객: `POST /api/tablet/login`, `GET /api/menus`, `POST /api/orders`, `GET /api/orders/current`.
  - **식별정보 원칙**: `POST /api/orders`의 body는 `{items:[{menu_id, qty}]}` **만** 포함하고, store_id/table_no는 `Authorization: Bearer <tablet_token>`의 TabletContext에서 서버가 결정한다. `GET /api/orders/current`도 쿼리 파라미터 없이 TabletContext로 현재 이용 세션을 식별한다.
- 관리자: `POST /api/admin/login`, `GET /api/admin/tables`, `GET /api/admin/orders/stream`(SSE), `PATCH /api/admin/orders/{id}/status`, `DELETE /api/admin/orders/{id}`, `POST /api/admin/tables/{no}/end-session`, `GET /api/admin/tables/{no}/history`, `POST /api/admin/tables` (setup), 메뉴 CRUD `/api/admin/menus...`.
  - **SSE 소비 방식**: `GET /api/admin/orders/stream`은 `Authorization: Bearer` 헤더로 보호되며, 프론트는 native EventSource가 아닌 **fetch 기반 text/event-stream 스트리밍 리더**로 소비한다. 엔드포인트와 SSE 실시간 요구사항(2초 이내)은 변경 없음.

## 6-1. 최초 태블릿 설정 → 자동 로그인 흐름 (FR-C1 / US-A6, 범위 불변)
> 아래는 **기존 요구사항의 연결 관계를 명확히 한 것**이며 새로운 provisioning 기능을 추가하지 않는다.

1. **서버 테이블 등록/Setup (관리자, 1회)** — 관리자가 `POST /api/admin/tables`로 테이블 번호와 테이블 비밀번호를 등록한다(비밀번호는 해싱 저장). 이 시점에 테이블 config가 서버에 존재하게 된다. [US-A6]
2. **테이블 태블릿 최초 인증 (관리자가 태블릿에서 1회 수행)** — 태블릿에서 `POST /api/tablet/login`에 매장 식별자 + 테이블 번호 + 테이블 비밀번호를 보내 인증한다. 성공 시 서버가 **태블릿 인증 토큰(16h)** 을 발급한다(태블릿 인증 세션 = 디바이스 자동 로그인 자격, 이용 세션과 별개). [FR-C1, C1 Auth]
3. **로컬 저장** — 태블릿(F1)은 발급받은 tablet_token과 테이블 config(store_id/table_no)를 **localStorage에 저장**한다. [FR-C1]
4. **이후 자동 로그인 (새로고침/재진입)** — 앱 로드 시 저장된 tablet_token 존재 여부를 확인하고, 있으면 재입력 없이 그 토큰으로 보호 API를 호출한다(Authorization: Bearer). 토큰이 유효하면 메뉴 화면으로 즉시 진입한다. 만료/부재 시에만 2번의 최초 인증을 다시 수행한다. [FR-C1]

- 이 흐름에서 **이용(주문) 세션**은 별도로, 고객의 첫 주문 시 서버에서 시작된다(자동 로그인 여부와 무관). 태블릿 인증 세션과 이용 세션은 독립적이다.

## 7. 병렬 작업 준비
- 안정화 우선: C0 스키마 + API/이벤트 계약.
- 이후 Menu·프론트·OrderHistory 병렬 진행 가능. 유닛 경계는 Units Generation에서 확정.
