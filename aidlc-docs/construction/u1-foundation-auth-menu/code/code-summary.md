# U1 — Foundation · Auth · Menu · Code Summary

> Unit: **U1 (C0 Persistence, C1 Auth, C2 Menu)** · Baseline SHA `2639417`.
> 기준: **FROZEN Integration Contract v0.1.0** + 승인된 U1 Functional Design + 승인된 Code Generation Plan.
> 이 문서는 PART 2에서 생성한 코드의 요약이다. 실제 코드는 `backend/` 아래에 있다.

## 1. 생성 파일 목록

```text
backend/
├── requirements.txt                 # 의존성 핀 고정 (U1 owns)
├── requirements.lock.txt            # pip freeze 잠금 (재현용)
├── .gitignore                       # .venv / __pycache__ / *.db 등 테스트 아티팩트 제외
├── conftest.py                      # 테스트 sys.path + 공용 fixture (테스트 스캐폴딩)
├── app/
│   ├── __init__.py
│   ├── common/                      # 공용 type/error/config (계약 §4)
│   │   ├── __init__.py
│   │   ├── config.py                # JWT secret 소싱, TTL 16h, 로그인 5회/10분, DB 경로
│   │   ├── context.py               # AdminContext, TabletContext (frozen dataclass)
│   │   ├── errors.py                # AppError 계열 + ErrorResponse 직렬화 + handler 등록 함수
│   │   ├── timeutil.py              # now_iso / iso_from_datetime (ISO 8601 UTC)
│   │   ├── testing.py               # build_test_app (테스트 factory, 조립 root 아님)
│   │   └── test_common.py
│   ├── persistence/                 # C0
│   │   ├── __init__.py
│   │   ├── schema.py                # 계약 §3 전체 테이블 DDL (FK 그대로) + 인덱스
│   │   ├── db.py                    # get_connection / transaction / init_db / db_dependency
│   │   ├── repository.py            # 파라미터 바인딩 공통 helper
│   │   └── test_persistence.py
│   ├── auth/                        # C1
│   │   ├── __init__.py
│   │   ├── security.py              # bcrypt hash/verify + HS256 JWT issue/decode (typ claim)
│   │   ├── rate_limit.py            # 인메모리 로그인 시도 제한 (5회→10분)
│   │   ├── repository.py            # admin / table 조회
│   │   ├── service.py               # admin_login / tablet_login
│   │   ├── dependencies.py          # verify_admin_token / verify_tablet_token
│   │   ├── router.py                # POST /api/tablet/login, POST /api/admin/login
│   │   └── test_auth.py
│   └── menu/                        # C2
│       ├── __init__.py
│       ├── repository.py            # store 스코프 CRUD/reorder + U2용 get_for_order/get_many_for_order
│       ├── service.py               # 검증 / display_order / reorder / 삭제 정책
│       ├── router.py                # 계약 §5.2 전체
│       └── test_menu.py
└── seed/                            # C0 (단독 owner)
    ├── __init__.py
    ├── sample_data.py               # 샘플 매장/관리자/테이블/메뉴 정의 (해시만 저장)
    ├── seeder.py                    # seed_if_empty (멱등)
    └── test_seed.py
```

## 2. 모듈 책임 요약

| 모듈 | 책임 | 관련 스토리/계약 |
|---|---|---|
| `common/config` | JWT secret(env `TABLE_ORDER_JWT_SECRET`, 없으면 프로세스 랜덤·고정 fallback 없음), TTL 16h, 로그인 5회/10분, DB 경로 | 계약 §4/§5.1 |
| `common/context` | `AdminContext{store_id,admin_user_id,username}`, `TabletContext{store_id,table_no}` | 계약 §4 |
| `common/errors` | 표준 에러(UNAUTHORIZED/FORBIDDEN/NOT_FOUND/VALIDATION_ERROR/RATE_LIMITED/CONFLICT), `{"error":{"code","message"}}` 직렬화, FastAPI handler 등록(등록은 IL/테스트) | 계약 §4 |
| `persistence/schema` | 계약 §3 **전체 8테이블** DDL(FK 그대로, 금액 INTEGER, timestamp TEXT) + 인덱스 | 계약 §3, C0(single-writer) |
| `persistence/db` | 연결(PRAGMA foreign_keys=ON) / 트랜잭션 / 멱등 init_db / 요청당 연결 의존성 | C0 |
| `seed/*` | `seed_if_empty` — 빈 DB에만 시드(멱등). 샘플 매장1·관리자1·테이블4·메뉴8. 평문 비밀번호는 저장 안 함(bcrypt 해시만) | 계약 §11 |
| `auth/security` | bcrypt 해시/검증, HS256 JWT 발급/검증(`typ`로 admin/tablet 교차 사용 차단, 16h) | US-A1, US-C1, US-A6 |
| `auth/rate_limit` | (store_id,username) 인메모리 카운터, 5회 연속 실패→10분 잠금, 성공 시 리셋 | FR-A1 |
| `auth/service`/`router` | 관리자·태블릿 로그인(계약 §5.1 body/response) | US-A1, US-C1, US-A6 |
| `auth/dependencies` | Bearer 파싱→JWT 검증→context 생성(무상태, DB 미접근) | 계약 §12 |
| `menu/*` | 고객 조회 + 관리자 CRUD/reorder(계약 §5.2). 검증(category/name 필수, price 정수≥0), display_order append, reorder 규칙 | US-C2, US-A7 |

## 3. Provided Interfaces (U2 / U3 / Integration Lead 소비)

- **Persistence**: `app.persistence.db.get_connection() / transaction() / init_db() / db_dependency()`.
- **Seed**: `seed.seeder.seed_if_empty(conn) -> bool` (계약 §11).
- **Auth dependencies**: `app.auth.dependencies.verify_admin_token -> AdminContext`, `verify_tablet_token -> TabletContext`.
- **Routers (IL이 main.py에서 include)**: `app.auth.router.router`, `app.menu.router.router`.
- **Errors**: `app.common.errors.register_error_handlers(app)` (IL이 main.py에서 등록).
- **Menu 조회(U2 주문용)**: `app.menu.repository.get_for_order(conn, store_id, menu_id)`, `get_many_for_order(conn, store_id, menu_ids)` — 단가·이름 스냅샷/존재 검증.
- **공용 type**: `app.common.context.AdminContext / TabletContext`, `app.common.errors.*`.

> `main.py`(composition root)는 **U1이 생성하지 않는다**(Integration Lead 소유). U1은 위 router/함수만 export한다.
> `common/testing.build_test_app`는 U1 단독 검증용 테스트 factory이며 composition root가 아니다.

## 4. 계약 준수 / 경계

- **Owned paths만 수정**: `backend/app/{common,persistence,auth,menu}/`, `backend/seed/`, `backend/requirements.txt`(+lock). `main.py`·U2/U3 경로·`coordination/*`·`aidlc-state.md` 미수정.
- **FROZEN 계약 준수**: §3 스키마(FK 정의 그대로), §4 context/error, §5.1/§5.2 API, 16h JWT, bcrypt, 로그인 5회→10분 잠금.
- **보안**: Git 포함 고정 JWT secret 없음(env 미설정 시 프로세스별 랜덤). 문서/코드에 실제 credential 값 없음(시드 기본값은 DEMO·env override, 해시만 저장).
- **Known limitation (승인)**: 참조되지 않은 메뉴 삭제만 정상 지원. 이미 `order_items`에서 참조 중인 메뉴 삭제는 `409 CONFLICT`이며 세부 정책은 deferred(§3 FK as-is). 통합 blocker가 되면 CCR 재검토.

## 5. 실행 / 테스트 방법 (로컬)

U1은 단독 앱 기동이 없다(앱 기동은 IL의 `main.py`). 테스트는 U1 라우터만 포함한 로컬 app fixture로 검증한다.

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # 39 passed (U1 unit + 계약 CT#1~#3)
```

- 테스트 격리: `conftest.py`가 `tmp_path` 기반 임시 SQLite DB로 `build_test_app`을 구성하고, 매 테스트 `rate_limit.reset_all()` 수행.
- 계약 최소 테스트 커버: CT#1(태블릿 로그인 성공/401), CT#2(관리자 JWT + 반복 실패 429), CT#3(tablet Bearer 메뉴 display_order 정렬 + 무인증 401). 그 외 CT#4~#10은 U2/U3/통합 범위.

## 6. 환경 변수

| 변수 | 용도 | 기본값 |
|---|---|---|
| `TABLE_ORDER_JWT_SECRET` | JWT 서명 secret | 미설정 시 프로세스 기동 시 랜덤 생성(고정 fallback 없음) |
| `TABLE_ORDER_DB_PATH` | SQLite 파일 경로 | `backend/table_order.db` |
| `TABLE_ORDER_SEED_ADMIN_PASSWORD` | 시드 관리자 비밀번호(DEMO) | `admin1234` (해시만 저장) |
| `TABLE_ORDER_SEED_TABLE_PASSWORD` | 시드 테이블 비밀번호(DEMO) | `table1234` (해시만 저장) |
