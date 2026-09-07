# U1 — Foundation · Auth · Menu · Code Generation Plan (PART 1)

> Unit: **U1 (C0 Persistence, C1 Auth, C2 Menu)** · Branch `unit/u1-foundation` · Baseline SHA `2639417`.
> 기준: **FROZEN Integration Contract v0.1.0** + 승인된 U1 Functional Design(`../u1-foundation-auth-menu/functional-design/`).
> 이 계획은 U1 Code Generation의 **단일 진실 원천(single source of truth)**이다. 승인 후 PART 2에서 이 순서대로만 생성한다.

## Unit Context
- **Project type**: Greenfield / 모듈형 모놀리스(단일 FastAPI 앱). Workspace root: `/home/cik61/aidlc-workshop/table-order`.
- **구현 스토리**: US-C2(메뉴 조회 API), US-A7(메뉴 관리 CRUD/정렬), US-A1(관리자 인증), US-C1(태블릿 인증/토큰 발급측), US-A6(Spanning: 태블릿 인증/토큰).
- **Depends on**: 없음(기반 유닛).
- **Provides (U2/U3/IL 소비)**: `init_db`/`seed_if_empty`/`get_connection`/`transaction`, `verify_admin_token→AdminContext`, `verify_tablet_token→TabletContext`, Menu 조회/관리 API 라우터, Menu 단가 스냅샷 조회(`get_for_order`), 공용 type/errors.
- **Owned DB entities (직접 조작)**: `stores`, `admin_users`, `tables`, `menus`. **스키마 single-writer로 §3 전체 테이블 생성**(U2 도메인 테이블 포함) — 단 CRUD 로직은 U2.

## 준수/경계 (self-check)
- **Owned paths만 생성**: `backend/app/common/`, `backend/app/persistence/`, `backend/app/auth/`, `backend/app/menu/`, `backend/seed/`, `backend/requirements.txt`.
- **생성 금지**: `backend/app/main.py`(Integration Lead 소유 — U1은 router artifact만 제공), `backend/app/order|table_session|order_history|realtime/`, `frontend/`, `coordination/*`, `aidlc-docs/aidlc-state.md`.
- **테스트 위치**: 각 U1 모듈 디렉터리에 co-locate(`test_*.py`) — 별도 shared `tests/` 디렉터리를 만들지 않아 U2/U3 경로와 겹치지 않음. 테스트는 U1 라우터만 포함한 **로컬 app fixture**로 검증(composition root main.py 미사용).
- FROZEN 계약 준수: §3 스키마(FK 정의 그대로), §4 context/error, §5 Auth/Menu API, 16h JWT, bcrypt, 로그인 5회→10분 잠금. OrderStatus/event/SSE 불변(참조 안 함).
- **Known limitation 유지**: 참조 중인 메뉴 삭제 세부 정책 미확정(deferred). 참조되지 않은 메뉴 삭제만 정상 지원.

## Application code 위치
```text
backend/
├── requirements.txt                      # deps(+lock 역할, 핀 고정) — U1 owns
├── app/
│   ├── common/    __init__ context errors config timeutil
│   ├── persistence/  __init__ db schema repository
│   ├── auth/      __init__ security rate_limit repository service dependencies router
│   └── menu/      __init__ repository service router
└── seed/          __init__ sample_data seeder
```
- `main.py`는 **생성하지 않음**. 각 라우터(`auth.router`, `menu.router`)와 `init_db`/`seed_if_empty`/`verify_*`를 IL이 조립하도록 export만 제공.

---

## 생성 단계 (번호·체크박스 — PART 2에서 실행)

- [x] **Step 1 — 프로젝트 구조 + 의존성 (greenfield setup)**
  - `backend/` 디렉터리·패키지 `__init__.py` 생성, `backend/requirements.txt`(fastapi, uvicorn[standard], pydantic, bcrypt, PyJWT — 버전 핀). SQLite는 표준 라이브러리.
  - *Story: 공통 기반.*

- [x] **Step 2 — Common (공용 type/error/config) + 단위 테스트**
  - `common/context.py`(AdminContext, TabletContext), `common/errors.py`(AppError 계열 + 에러코드 UNAUTHORIZED/FORBIDDEN/NOT_FOUND/VALIDATION_ERROR/RATE_LIMITED/CONFLICT, ErrorResponse 직렬화, FastAPI exception handler 함수 — 등록은 IL), `common/timeutil.py`(`now_iso`), `common/config.py`(JWT secret 소싱[env `TABLE_ORDER_JWT_SECRET` 없으면 프로세스 기동 시 랜덤 생성, 고정 fallback 금지], 토큰 TTL 16h, 로그인 제한 5회/10분, DB 경로).
  - `common/test_errors.py`, `common/test_config.py`: 에러→ErrorResponse 매핑, secret 소싱(env 우선, 미설정 시 랜덤·비어있지 않음), 값이 문서/코드에 노출되지 않음.
  - *계약 §4.*

- [x] **Step 3 — Persistence (C0) + 단위 테스트**
  - `persistence/schema.py`: 계약 §3 **전체 테이블 DDL**(stores, admin_users, tables, menus, table_sessions, orders, order_items, order_history) — FK 정의는 §3 그대로, 금액 INTEGER, timestamp TEXT. 인덱스(menus(store_id,display_order), admin_users(store_id,username), tables(store_id,table_no)).
  - `persistence/db.py`: `get_connection`(PRAGMA foreign_keys=ON, row factory), `transaction`(commit/rollback 컨텍스트), `init_db`(CREATE IF NOT EXISTS, 멱등).
  - `persistence/repository.py`: 파라미터 바인딩 기반 공통 helper(store 스코프, 단건/다건).
  - `persistence/test_db.py`: init_db 멱등(2회 실행), FK ON, transaction rollback.
  - *C0.*

- [x] **Step 4 — Seed (C0, 단독 owner) + 단위 테스트**
  - `seed/sample_data.py`: 샘플 매장 1·관리자 1(평문→bcrypt는 seeder에서)·카테고리·샘플 메뉴 다수·테이블 다수(비밀번호 평문 상수는 넣지 않고, 개발용 기본값을 상수/설명으로 문서화하되 해시만 저장). *실제 데이터 내용 작성.*
  - `seed/seeder.py`: `seed_if_empty`(stores 0건일 때만; 2차 방어 자연키 dedup; FK 순서 store→admin/tables/menus; 단일 트랜잭션).
  - `seed/test_seeder.py`: 빈 DB 시드 성공, 재실행 시 중복 0, 최소 보장(1매장/1관리자/다수 메뉴·테이블).
  - *계약 §11.*

- [x] **Step 5 — Auth 보안 primitive (C1) + 단위 테스트**
  - `auth/security.py`: bcrypt `hash_password`/`verify_password`, JWT `encode`/`decode`(HS256, `typ` claim, 16h exp, secret from config), `expires_at` ISO 생성.
  - `auth/rate_limit.py`: 인메모리 시도 추적 `{(store_id,username):{fail_count,locked_until}}`, `is_locked`/`register_failure`(5회 도달 시 10분 잠금)/`reset`.
  - `auth/test_security.py`, `auth/test_rate_limit.py`: bcrypt round-trip, JWT 발급→검증→만료 401·typ 교차 차단, 5회 실패→잠금·성공 시 리셋.
  - *C1, FR-A1.*

- [x] **Step 6 — Auth repository/service/dependencies/router (C1) + 단위/계약 테스트**
  - `auth/repository.py`: (store_id,username) admin 조회, (store_id,table_no) table 조회.
  - `auth/service.py`: 관리자 로그인(잠금 선검사→bcrypt→실패 카운트/401 또는 429→성공 시 토큰·리셋), 태블릿 로그인(자격 검증→tablet_token).
  - `auth/dependencies.py`: `verify_admin_token→AdminContext`, `verify_tablet_token→TabletContext`(Bearer 파싱·검증·typ 강제·401).
  - `auth/router.py`: `POST /api/tablet/login`, `POST /api/admin/login`(계약 §5.1 body/response).
  - `auth/test_router.py`: CT#1(태블릿 로그인 성공/오답 401), CT#2(관리자 JWT 발급/반복 실패 429).
  - *US-A1, US-C1, US-A6(인증측).*

- [x] **Step 7 — Menu repository/service/router (C2) + 단위/계약 테스트**
  - `menu/repository.py`: store 스코프 list/get/create/update/delete/reorder, **`get_for_order(store_id, menu_id)`/`get_many_for_order`**(U2용 단가·존재 조회).
  - `menu/service.py`: 검증(category/name 필수·비어있지 않음, price 정수≥0), display_order append, reorder(포함 id 지정순서→미포함 상대순서 유지→0..N-1 재번호화), 삭제(참조되지 않은 경우 정상 지원; 세부 참조 정책 deferred).
  - `menu/router.py`: 계약 §5.2 전체(`GET /api/menus`, `GET/POST/PATCH/DELETE /api/admin/menus`, `POST /api/admin/menus/reorder`), auth 의존성 연결.
  - `menu/test_router.py`: CT#3(tablet Bearer 메뉴 display_order 정렬·무인증 401), 생성 검증(422), PATCH 404/부분갱신, DELETE 204/404, reorder 순서·422, store 스코프 격리.
  - *US-C2, US-A7.*

- [x] **Step 8 — Code 요약 문서(markdown)**
  - `aidlc-docs/construction/u1-foundation-auth-menu/code/` 아래 생성 파일 목록·모듈 책임·U2/IL provided interface·실행/테스트 방법(로컬 app fixture) 요약.

- [x] **Step 9 — 배포/실행 아티팩트(최소)**
  - `backend/requirements.txt` 확정. U1 단독 실행은 없음(앱 기동은 IL의 main.py) → README성 실행 노트는 code/ 요약에 포함. 별도 Dockerfile/CI 없음(로컬 half-day MVP).

## Story Traceability
| Story | Step |
|---|---|
| US-A1 관리자 인증 | 5, 6 |
| US-C1 태블릿 인증(발급/검증측) | 5, 6 |
| US-A6 태블릿 인증/토큰(Spanning) | 5, 6 |
| US-C2 메뉴 조회 | 7 |
| US-A7 메뉴 관리(CRUD/정렬) | 7 |
| 공통 기반(C0/공용 type/시드) | 1, 2, 3, 4 |

## 범위/규모 요약
- 총 **9 스텝**. 백엔드 3계층(common/persistence/auth/menu) + seed. 프론트 없음(U3). NFR/Infra 스킵(state 계획대로).
- 테스트는 각 모듈 co-locate, Build & Test 단계에서 실행(계약 §13 CT#1~#3 + U1 unit tests).
- **PART 2는 이 계획 승인 후에만 시작.** 승인 전 제품 코드 생성 없음.

## 진행 추적 노트
- `aidlc-state.md`는 U1 no-touch 지정이므로 본 계획 체크박스로 진행 추적하고, 상태 반영은 coordination(Integration Lead)에 위임.
