# Contract Change Request — CCR-001

> **제출 유닛(Submitter)**: U2 (Order · Session · Realtime)
> **수신(Owner/Approver)**: Integration Lead (`INTEGRATION_CONTRACT.md` single-writer)
> **제출일**: 2026-09-07
> **상태**: **APPROVED & MERGED** — Integration Lead가 검토·승인하여 `INTEGRATION_CONTRACT.md`에 반영 완료. 계약 버전 v0.1.0 → **v0.2.0** (minor/하위호환). §4에 헬퍼 추가, §12 U1 provides/U2 consumes 반영, §15 적용 CCR 이력 + U1 통지 기재. Q7=A 확정 가능.
> **분류(제안)**: **minor / 하위호환** (인터페이스 추가, 스키마·엔드포인트·이벤트 변경 없음) → 제안 버전 v0.**2**.0
> *(최종 버전 판정 및 문서 반영은 Integration Lead가 수행. U2는 계약 문서를 직접 수정하지 않음.)*

---

## 1. 대상 섹션
- **§4 공용 Type / Context (U1 `common/` 소유)**
- **§12 각 Unit의 Provided / Consumed Interface** (U1 provides / U2 consumes)
- (참고 연관: §3 스키마의 `tables.password_hash` / `admin_users.password_hash` — **변경 없음**)

## 2. 현재 계약 (as-is)
- §3: `admin_users.password_hash`, `tables.password_hash`는 **bcrypt** 문자열로 선언.
- §12 **U1 provides**: Persistence/Repository, Auth(`verify_tablet_token`/`verify_admin_token`, admin/tablet login), Menu 조회, 공용 type/context(`common/`).
- §12 **U2 consumes (from U1)**: Persistence/Repository, `verify_tablet_token`/`verify_admin_token`, Menu 단가/유효성 조회, 공용 type.
- **누락**: bcrypt **해싱/검증 유틸리티가 U1의 provided interface로 선언되어 있지 않다.**
- 그러나 Application Design상 `setup_table`(C4 / **U2**)은 "비밀번호 해싱"을 포함해 `tables.password_hash`를 **생성(write)** 해야 하고, `tablet_login`(C1 / **U1**)은 그 해시를 **검증(verify)** 한다.

## 3. 제안 변경 (to-be)
U1의 `common/`이 소유·구현하는 **공유 비밀번호 해싱 헬퍼**를 §4/§12의 U1 provided interface로 **명시 추가**한다:

```text
# common/ (U1 owns & implements) — 개념 시그니처
hash_password(plaintext: str) -> str          # bcrypt 해시 문자열 생성
verify_password(plaintext: str, password_hash: str) -> bool   # bcrypt 검증
```

- §12 **U1 provides**에 "공용 비밀번호 해싱 헬퍼(`hash_password`/`verify_password`, bcrypt) — `common/` 구현" 항목 추가.
- §12 **U2 consumes (from U1)**에 "`hash_password`(테이블 setup 시 `table_password` 해싱용)" 추가.
- §3 스키마, §5 엔드포인트, §6 OrderStatus, §7 SSE, §8 이벤트 payload는 **변경 없음**.

## 4. 사유 (Rationale)
- `tables.password_hash`를 **U2(`setup_table`)가 쓰고 U1(`tablet_login`)이 검증**하므로, 두 유닛은 **동일한 bcrypt 스킴(알고리즘 variant·cost factor·salt 처리)** 에 반드시 합의해야 한다. 공유 헬퍼가 없으면 U2가 crypto를 중복 구현하게 되어 U1 검증과 **불일치(로그인 실패) 위험**이 발생한다.
- bcrypt/자격증명 처리는 **C1 Auth(U1) 도메인**이며, §10 single-writer 원칙상 crypto는 U1이 소유하는 것이 자연스럽다. U2가 별도 crypto를 두면 소유 경계가 흐려진다.
- **새 요구사항 아님**: 이미 승인된 **US-A6(테이블 태블릿 초기 설정)** 와 **US-C1/FR-C1(태블릿 자동 로그인 검증)** 을 연결하기 위한 **내부 인터페이스 정합화**일 뿐이며, 제품 기능·엔드포인트·데이터 계약을 추가하지 않는다.

## 5. 영향 받는 유닛 (Impact)
| 유닛 | 영향 | 내용 |
|---|---|---|
| **U1** | provides (구현) | `common/`에 `hash_password`/`verify_password` 구현·노출. admin/tablet login 검증에도 동일 헬퍼 사용(일관성). |
| **U2** | consumes | `setup_table`에서 `table_password` → `hash_password()`로 해싱 후 `tables.password_hash` 저장. U2는 crypto를 직접 구현하지 않음. |
| **U3** | 없음 | 영향 없음(N/A). |

- 하위호환: 기존 인터페이스/스키마/이벤트 불변 → 기존 개발 산출물 재작업 불필요.

## 6. 승인 전 U2의 처리 방침 (대기 중 동작)
- 이 CCR이 **승인·반영되면**: U2 `setup_table`은 U1 `common.hash_password()`를 소비(consume)한다.
- **반려/보류되면**: U2는 crypto를 임의 구현하지 않고, `setup_table`의 해싱 지점을 **U1 제공 헬퍼에 대한 의존 지점으로 남겨둔(=coordination dependency)** 상태로 Functional Design을 확정하며, 통합 시 U1과 해시 스킴을 협의한다. (임의 bcrypt 중복 구현은 하지 않음.)

## 7. 요청 사항
Integration Lead의 검토 및 §15 절차에 따른 반영(승인 시 `INTEGRATION_CONTRACT.md` §4/§12 갱신 + 버전 증가)을 요청합니다. U2는 계약 문서를 직접 수정하지 않습니다.
