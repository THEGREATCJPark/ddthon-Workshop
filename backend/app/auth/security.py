"""Security primitives: bcrypt password hashing and HS256 JWT (C1).

Tokens carry a ``typ`` claim ("admin" | "tablet") to prevent cross-use, and a
16h expiry (contract §5.1/§9).
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.common import config
from app.common.errors import Unauthorized


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def issue_token(typ: str, claims: dict) -> tuple[str, str]:
    """Return (token, expires_at_iso). typ is 'admin' or 'tablet'."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=config.TOKEN_TTL_SECONDS)
    payload = dict(claims)
    payload.update({"typ": typ, "iat": int(now.timestamp()), "exp": int(exp.timestamp())})
    token = jwt.encode(payload, config.get_jwt_secret(), algorithm=config.JWT_ALGORITHM)
    return token, _iso(exp)


def decode_token(token: str, expected_typ: str) -> dict:
    try:
        payload = jwt.decode(token, config.get_jwt_secret(), algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise Unauthorized("유효하지 않은 토큰입니다.")
    if payload.get("typ") != expected_typ:
        raise Unauthorized("토큰 유형이 올바르지 않습니다.")
    return payload
