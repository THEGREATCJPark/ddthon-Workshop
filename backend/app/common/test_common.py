"""Unit tests for common utilities (config, errors, timeutil)."""
import re

from app.common import config
from app.common.errors import RateLimited, Unauthorized, error_body
from app.common.timeutil import now_iso


def test_error_body_shape():
    body = error_body("UNAUTHORIZED", "no")
    assert body == {"error": {"code": "UNAUTHORIZED", "message": "no"}}


def test_error_defaults():
    assert Unauthorized().http_status == 401 and Unauthorized().code == "UNAUTHORIZED"
    assert RateLimited().http_status == 429 and RateLimited().code == "RATE_LIMITED"


def test_now_iso_is_utc_zulu():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", now_iso())


def test_jwt_secret_is_stable_within_process():
    assert config.get_jwt_secret() == config.get_jwt_secret()


def test_login_policy_constants():
    assert config.LOGIN_MAX_FAILS == 5
    assert config.LOGIN_LOCK_SECONDS == 10 * 60
    assert config.TOKEN_TTL_SECONDS == 16 * 3600
