"""Application configuration (U1 owns).

Values are sourced from environment variables where relevant. The JWT signing
secret is read from ``TABLE_ORDER_JWT_SECRET``; if unset, a random per-process
secret is generated at first use (NO committed fixed fallback). No secret value
is written to source or docs.
"""
import os
import secrets
from pathlib import Path

# backend/ directory (config.py is at backend/app/common/config.py)
BASE_DIR = Path(__file__).resolve().parents[2]

# SQLite database file (persistent). Overridable for tests via TABLE_ORDER_DB_PATH.
DB_PATH = os.environ.get("TABLE_ORDER_DB_PATH", str(BASE_DIR / "table_order.db"))

# Token / auth policy (FROZEN contract §5.1, §9; FR-A1)
JWT_ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 16 * 3600          # 16 hours (admin JWT & tablet token)
LOGIN_MAX_FAILS = 5                    # consecutive failures before lock
LOGIN_LOCK_SECONDS = 10 * 60           # 10 minute lock

_JWT_SECRET: str | None = None


def get_jwt_secret() -> str:
    """Return the HS256 signing secret.

    Priority: env ``TABLE_ORDER_JWT_SECRET`` -> per-process random secret.
    A random secret means tokens are invalidated on process restart (local dev).
    """
    global _JWT_SECRET
    env_secret = os.environ.get("TABLE_ORDER_JWT_SECRET")
    if env_secret:
        return env_secret
    if _JWT_SECRET is None:
        _JWT_SECRET = secrets.token_urlsafe(48)
    return _JWT_SECRET
