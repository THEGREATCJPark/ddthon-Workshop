# U1 — Business Rules, Validation & Error Handling

> 기준: FROZEN Integration Contract v0.1.0 §4(에러코드)·§5(엔드포인트). 계약 필드 집합/타입을 위반하지 않는다.

## 1. 공통 규칙
- **Store 스코프 강제**: 모든 조회/변경은 인증 컨텍스트의 `store_id`로 필터. 다른 매장 리소스 접근 시 존재하지 않는 것으로 처리(404) — 존재 노출 최소화.
- **식별정보 신뢰 출처(계약 §4)**: 고객(tablet) API는 store_id/table_no를 **TabletContext에서만** 취득. 요청 body/query의 store/table 값은 신뢰 입력이 아니다.
- **금액**: `price`는 정수(원), `≥ 0`. 부동소수·문자열 금지.
- **시각**: 저장/응답 timestamp는 ISO 8601 UTC 문자열. 공용 `now_iso()` 헬퍼 사용.
- **비밀번호**: 평문 저장 금지 → bcrypt 해시만 저장. 로그/응답에 해시·평문 노출 금지.

## 2. 인증 규칙 (C1)

### 2.1 관리자 로그인 (FR-A1)
- 자격 불일치(계정 없음 또는 비밀번호 불일치) → **401 UNAUTHORIZED**, 동일 메시지(계정 존재 여부 비노출).
- **로그인 시도 제한**: **(store_id, username) 기준 연속 5회 실패 시 10분 잠금**. 잠금 중에는 자격 검증 없이 **429 RATE_LIMITED**. **성공 로그인 시 카운터와 잠금을 리셋**.
- 성공 → JWT(HS256) 발급, 유효기간 **16시간**, `expires_at` ISO 8601 반환.
- **JWT 시크릿**: HS256, 시크릿은 환경변수 `TABLE_ORDER_JWT_SECRET`. 미설정 시 **프로세스 기동 시 랜덤 생성**(고정 시크릿 fallback 금지). 시크릿 값은 문서/코드에 기재하지 않는다.

### 2.2 태블릿 로그인
- (store_id, table_no) 미존재 또는 비밀번호 불일치 → **401**.
- 성공 → tablet_token(JWT류) 16시간, `expires_at` 반환.

### 2.3 토큰 검증
- Bearer 헤더 없음/형식 오류/서명 불일치/만료/`typ` 불일치 → **401 UNAUTHORIZED**.
- `verify_admin_token` → `typ==admin` 강제, AdminContext 구성. `verify_tablet_token` → `typ==tablet` 강제, TabletContext 구성. (교차 사용 차단, Q-U1-5)
- 만료 판정은 서버 시간 기준 `exp`.

## 3. 메뉴 규칙 (C2 — FR-C2, FR-A5)

### 3.1 생성/수정 검증
| 필드 | 규칙 | 위반 |
|---|---|---|
| category | 필수(생성), 비어있지 않은 문자열, 트림 | 422 VALIDATION_ERROR |
| name | 필수(생성), 비어있지 않은 문자열, 트림 | 422 |
| price | 필수(생성), 정수 `≥ 0` | 422 |
| description | 선택, 문자열 or null | 422(타입 오류 시) |
| image_url | 선택, 문자열 or null | 422 |
| store_id | 요청으로 받지 않음(컨텍스트 고정), 변경 불가 | — |

- PATCH는 제공된 필드만 검증·부분 갱신. 제공 필드가 위 규칙 위반 시 422.
- 존재하지 않는 menu_id(또는 타 매장) → **404 NOT_FOUND**.

### 3.2 조회
- 정렬: `display_order ASC, id ASC`(계약 "노출 순서 정렬").
- category 필터는 정확 일치(옵션). 미지정 시 전체.
- 응답 필드 집합: `{id, category, name, price, description, image_url, display_order}`(계약 §5.2).

### 3.3 삭제
- 미존재/타 매장 → 404. **참조되지 않은 메뉴 삭제**는 정상 지원 → 204.
- **FK 기준**: 계약 §3 `order_items.menu_id FK->menus.id` 정의를 그대로 사용. **이미 참조 중인 메뉴 삭제의 세부 정책은 이번 단계에서 확정하지 않음**(Known limitation, 도메인 §7 — CCR deferred). Build/Test·통합에서 blocker 시 CCR 재검토.

### 3.4 reorder
- `ordered_ids`의 모든 id가 (store 소속·존재)여야 함. 위반 시 **422**.
- **재정렬 규칙(부분 목록 허용)**: (1) `ordered_ids` 포함 메뉴를 지정 순서대로 앞에 배치, (2) 미포함 메뉴는 기존 상대 순서(display_order ASC, id ASC) 유지하며 뒤에 배치, (3) 전체를 0..N-1 연속 `display_order`로 재번호화(원자적 트랜잭션). 성공 → 204.

## 4. 에러 처리 표준 (계약 §4)
- 모든 오류 응답 형식: `{"error": {"code": <STRING>, "message": <STRING>}}`.
- 코드→HTTP 매핑: UNAUTHORIZED=401, FORBIDDEN=403, NOT_FOUND=404, VALIDATION_ERROR=422, RATE_LIMITED=429, CONFLICT=409.
- **U1이 `common/`에 공용 예외 타입 + 예외→ErrorResponse 매핑 핸들러를 제공**한다(전 유닛 공통). 핸들러의 **앱 등록(app.add_exception_handler)** 은 main.py에서 Integration Lead가 수행 — U1은 핸들러 함수만 제공(main.py 미수정).
- 검증 실패 메시지는 필드 단위로 구체화하되 민감정보(해시/토큰) 미포함.

## 5. 시드 규칙 (계약 §11)
- `stores` 비어있을 때만 시드(멱등). 재실행 시 자연키 기준 중복 삽입 방지.
- 최소 보장: 1 매장 / 1 관리자(bcrypt) / 다수 카테고리·메뉴 / 다수 테이블(bcrypt) → vertical slice 즉시 동작.

## 6. 테스트 관점 (계약 §13 U1 해당분)
> 상세 케이스는 Build & Test 단계에서 확장. 여기서는 U1 경계 검증 관점.

### 6.1 Contract-level (U1 소관)
- **CT#1** `POST /api/tablet/login`: 유효 자격 → tablet_token 발급 / 잘못된 비밀번호 → 401.
- **CT#2** `POST /api/admin/login`: 유효 자격 → JWT 발급 / 반복 실패 → 429(임계치 초과).
- **CT#3** `GET /api/menus`(tablet Bearer): 시드 메뉴가 display_order 순으로 반환 / 무인증 → 401.
- (참고) U1의 `verify_*` 의존성은 U2 소관 CT#4·#6의 전제 — U1은 TabletContext/AdminContext를 신뢰 출처로 제공.

### 6.2 U1 Unit tests
- Persistence: init_db 멱등(중복 실행), transaction commit/rollback, FK ON.
- Seed: 빈 DB 시드 성공 / 재실행 시 중복 0 / FK 순서.
- Auth: bcrypt 검증 성공·실패, JWT 발급→검증 round-trip, 만료 토큰 401, typ 교차 사용 차단, 시도 제한 임계치·잠금·리셋.
- Menu: 생성 검증(정상/누락/음수 price 422), display_order append, PATCH 부분 갱신·404, DELETE 204·404, reorder 순서 반영·422(외부 id), store 스코프 격리(타 매장 접근 차단).

## 7. 계약 준수 / 비침범 확인
- OrderStatus 값, event payload, SSE 프레임/엔드포인트 → **U1 미소유, 변경 없음**(참조만).
- §3 스키마 컬럼 추가/변경 없음(FK 정의 포함 계약 §3 그대로 구현). §5 path/method/auth/필드 집합 준수. 계약 문서는 U1이 수정하지 않음.
- **Contract conflict: NO / Contract Change Request: NO** — 이전 FK CCR 제안은 **withdrawn/deferred**(도메인 §7). 계약 안정성 우선.
- **Known limitation**: 참조 중인 메뉴 삭제 세부 정책은 통합 blocker가 되지 않는 한 deferred.
