"""Auth business logic (C1): admin & tablet login (contract §5.1).

- admin_login: rate-limit precheck -> bcrypt verify -> issue JWT (typ=admin).
  On failure register a fail (5 -> 10min lock, 429). On success reset counter.
- tablet_login: bcrypt verify -> issue tablet token (typ=tablet). No rate limit
  (contract §5.1 lists only 401 for tablet login).
"""
import sqlite3

from app.auth import rate_limit, repository
from app.auth.security import issue_token, verify_password
from app.common.errors import RateLimited, Unauthorized


def admin_login(conn: sqlite3.Connection, store_id: int, username: str, password: str) -> dict:
    if rate_limit.is_locked(store_id, username):
        raise RateLimited("로그인 시도가 제한되었습니다. 잠시 후 다시 시도해 주세요.")

    admin = repository.get_admin(conn, store_id, username)
    if admin is None or not verify_password(password, admin["password_hash"]):
        rate_limit.register_failure(store_id, username)
        if rate_limit.is_locked(store_id, username):
            raise RateLimited("로그인 시도가 제한되었습니다. 잠시 후 다시 시도해 주세요.")
        raise Unauthorized("아이디 또는 비밀번호가 올바르지 않습니다.")

    rate_limit.reset(store_id, username)
    token, expires_at = issue_token(
        "admin",
        {"store_id": admin["store_id"], "admin_user_id": admin["id"], "username": admin["username"]},
    )
    return {"access_token": token, "expires_at": expires_at}


def tablet_login(conn: sqlite3.Connection, store_id: int, table_no: int, table_password: str) -> dict:
    table = repository.get_table(conn, store_id, table_no)
    if table is None or not verify_password(table_password, table["password_hash"]):
        raise Unauthorized("테이블 자격 정보가 올바르지 않습니다.")

    token, expires_at = issue_token(
        "tablet",
        {"store_id": table["store_id"], "table_no": table["table_no"]},
    )
    return {"tablet_token": token, "expires_at": expires_at}
