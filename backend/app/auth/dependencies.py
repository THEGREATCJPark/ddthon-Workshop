"""FastAPI auth dependencies (C1): verify_admin_token / verify_tablet_token.

Stateless — contexts are built from JWT claims (no DB hit). These are consumed
by U1's own routers and by U2 (contract §12).
"""
from fastapi import Header

from app.auth.security import decode_token
from app.common.context import AdminContext, TabletContext
from app.common.errors import Unauthorized


def _bearer(authorization: str | None) -> str:
    if not authorization:
        raise Unauthorized("인증 토큰이 필요합니다.")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise Unauthorized("인증 토큰 형식이 올바르지 않습니다.")
    return parts[1].strip()


def verify_admin_token(authorization: str | None = Header(default=None)) -> AdminContext:
    payload = decode_token(_bearer(authorization), "admin")
    try:
        return AdminContext(
            store_id=int(payload["store_id"]),
            admin_user_id=int(payload["admin_user_id"]),
            username=str(payload["username"]),
        )
    except (KeyError, TypeError, ValueError):
        raise Unauthorized("토큰 정보가 올바르지 않습니다.")


def verify_tablet_token(authorization: str | None = Header(default=None)) -> TabletContext:
    payload = decode_token(_bearer(authorization), "tablet")
    try:
        return TabletContext(
            store_id=int(payload["store_id"]),
            table_no=int(payload["table_no"]),
        )
    except (KeyError, TypeError, ValueError):
        raise Unauthorized("토큰 정보가 올바르지 않습니다.")
