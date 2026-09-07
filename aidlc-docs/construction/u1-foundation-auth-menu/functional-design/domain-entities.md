# U1 — Domain Entities

> 기준: FROZEN Integration Contract v0.1.0 §3(공유 스키마) · §4(공용 Type). U1은 **스키마 single-writer**로서 계약 §3의 **모든 테이블을 init_db에서 생성**한다(U2 소유 도메인 테이블 포함). 아래는 계약 스키마를 U1 관점에서 상세화한 것이며 **컬럼 추가/변경은 없다**.

## 1. U1 소유·직접 조작 엔티티

### Store (`stores`)
| 필드 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| name | TEXT | NOT NULL | 매장 표시명 |

- 멀티테넌시 최소 단위. 모든 하위 엔티티는 `store_id`로 스코프된다.

### AdminUser (`admin_users`)
| 필드 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| store_id | INTEGER | FK→stores.id, NOT NULL | |
| username | TEXT | NOT NULL, UNIQUE(store_id, username) | 로그인 ID |
| password_hash | TEXT | NOT NULL | **bcrypt** 해시(평문 미저장) |

### TableConfig (`tables`)
| 필드 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| store_id | INTEGER | FK→stores.id, NOT NULL | |
| table_no | INTEGER | NOT NULL, UNIQUE(store_id, table_no) | 테이블 번호 |
| password_hash | TEXT | NOT NULL | **bcrypt** (태블릿 로그인 자격) |

- 태블릿 초기 설정 결과(관리자가 생성 — 생성 API는 U2 US-A6 Primary이나 **인증/토큰 발급 로직은 U1**). U1은 로그인 시 이 레코드로 자격을 검증한다.

### Menu (`menus`)
| 필드 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | INTEGER | PK | |
| store_id | INTEGER | FK→stores.id, NOT NULL | |
| category | TEXT | NOT NULL | 카테고리(문자열) |
| name | TEXT | NOT NULL | 메뉴명 |
| price | INTEGER | NOT NULL, ≥ 0 | **원 단위 정수**(부동소수 금지) |
| description | TEXT | NULL 허용 | 설명 |
| image_url | TEXT | NULL 허용 | 이미지 URL |
| display_order | INTEGER | NOT NULL DEFAULT 0 | 노출 순서(오름차순) |

- FR-C2 메뉴 필드(명·가격·설명·카테고리·이미지 URL) 충족. 조회 정렬 키: `display_order ASC, id ASC`.

## 2. U1이 스키마만 생성하고 **직접 조작하지 않는** 엔티티 (U2 소유 로직)
> init_db가 생성하지만 CRUD 로직은 U2. U1은 **Menu 단가 조회 인터페이스**만 제공(U2가 주문 스냅샷에 사용).

- `table_sessions`, `orders`, `order_items`, `order_history` — **계약 §3 정의를 그대로 구현 기준으로 사용**한다(`order_items.menu_id INTEGER FK->menus.id`, nullable/ON DELETE 미규정 = 계약 그대로).
- **메뉴 삭제와 FK (Known limitation)**: 참조되지 않은 메뉴 삭제는 정상 지원한다. 이미 `order_items`에서 참조 중인 메뉴 삭제의 세부 정책은 **이번 Functional Design에서 새로 확정하지 않는다**(§7 참조 — CCR deferred). 계약 안정성 우선(U2/U3가 FROZEN v0.1.0 기준 병렬 진행 중, 핵심 vertical slice의 blocker 아님).

## 3. 공용 Context / DTO (`common/`, U1 소유 — 계약 §4)

```text
AdminContext   = { store_id: int, admin_user_id: int, username: str }
TabletContext  = { store_id: int, table_no: int }
ErrorResponse  = { "error": { "code": str, "message": str } }
```

- **TabletContext = 고객 보호 API의 store_id/table_no 유일 신뢰 출처(Source of Truth)**. 요청 body/query의 store/table은 신뢰 입력이 아니다.
- 표준 에러 코드: `UNAUTHORIZED`(401), `FORBIDDEN`(403), `NOT_FOUND`(404), `VALIDATION_ERROR`(422), `RATE_LIMITED`(429), `CONFLICT`(409).

## 4. 인증 토큰 (엔티티 아님 — 클레임 모델)
> DB 저장 없는 stateless 토큰(계약 §9: tablet_token = JWT류, 16h).

```text
AdminToken(JWT, HS256)   claims: { sub/admin_user_id, store_id, username, typ:"admin", exp(+16h), iat }
TabletToken(JWT, HS256)  claims: { store_id, table_no, typ:"tablet", exp(+16h), iat }
```

- `typ` claim으로 admin/tablet 토큰 교차 사용 차단(Q-U1-5).
- `expires_at`은 응답에 ISO 8601 문자열로 반환(계약 §5.1).

## 5. 관계 요약 (ERD 텍스트)

```text
stores 1 ── N admin_users        (store_id)
stores 1 ── N tables             (store_id, UNIQUE table_no per store)
stores 1 ── N menus              (store_id)
stores 1 ── N table_sessions*    (*U2 로직)
table_sessions 1 ── N orders*    (*U2 로직)
orders 1 ── N order_items*       (order_items.menu_id → menus.id [계약 §3 그대로]; name/unit_price 스냅샷)
```

- U1 책임 관계: stores↔admin_users, stores↔tables, stores↔menus 무결성 및 스코프.
- `order_items`가 `menus`를 참조하되 **주문 시점 name/unit_price 스냅샷**을 보유 → 메뉴 수정이 과거 주문 표시를 훼손하지 않음. FK 삭제 세부 동작은 계약 §3 정의를 따르며 이 단계에서 새로 확정하지 않음(§7).

## 7. FK 삭제 정책 — CCR deferred (Known limitation)

> 이전 리비전에서 제안했던 `order_items.menu_id` nullable + `ON DELETE SET NULL` CCR은 **withdrawn/deferred** 상태다. **이번 단계에서 CCR을 진행하지 않는다.**

| 항목 | 내용 |
|---|---|
| 이전 제안(참고) | §3 `order_items.menu_id` → `NULL, ON DELETE SET NULL` |
| **현재 상태** | **Withdrawn / Deferred** — CCR 미제출. FROZEN 계약 §3 FK 정의를 그대로 구현 기준으로 사용 |
| 사유 | U2/U3가 FROZEN v0.1.0 기준 병렬 진행 중이며, 해당 이슈는 핵심 vertical slice의 blocker가 아님 → 계약 안정성 우선 |
| Known limitation | 참조되지 않은 메뉴 삭제는 정상 지원. **이미 `order_items`에서 참조 중인 메뉴 삭제의 세부 정책은 이번 Functional Design에서 확정하지 않음.** Build/Test 또는 통합에서 이 케이스가 blocker가 되면 그때 CCR로 재검토 |

## 6. 불변 규칙 (계약 유래)
- 금액: 모든 화폐 값 **정수(원)**.
- 시각: 모든 timestamp **ISO 8601 UTC 문자열**(U1 공용 시간 헬퍼 제공).
- store 스코프: 모든 조회/변경은 인증 컨텍스트의 `store_id`로 필터(다른 매장 데이터 접근 불가 → FORBIDDEN/NOT_FOUND).
