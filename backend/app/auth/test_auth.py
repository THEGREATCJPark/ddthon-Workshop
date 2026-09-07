"""Auth tests: security primitives, rate limit, and login endpoints (C1).

Covers contract §13 contract-tests #1 (tablet login) and #2 (admin login + 429).
"""
import pytest

from app.auth import rate_limit
from app.auth.security import decode_token, hash_password, issue_token, verify_password
from app.common.errors import Unauthorized
from seed import sample_data


# --- security primitives ---------------------------------------------------

def test_hash_and_verify_password():
    h = hash_password("secret123")
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_verify_password_handles_bad_hash():
    assert verify_password("x", "not-a-bcrypt-hash") is False


def test_token_typ_prevents_cross_use():
    token, _ = issue_token("admin", {"store_id": 1, "admin_user_id": 1, "username": "a"})
    assert decode_token(token, "admin")["store_id"] == 1
    with pytest.raises(Unauthorized):
        decode_token(token, "tablet")


def test_decode_rejects_garbage_token():
    with pytest.raises(Unauthorized):
        decode_token("garbage.token.value", "admin")


# --- rate limiter -----------------------------------------------------------

def test_rate_limit_locks_after_max_fails():
    rate_limit.reset_all()
    for _ in range(5):
        rate_limit.register_failure(1, "admin")
    assert rate_limit.is_locked(1, "admin")


def test_rate_limit_reset_clears_lock():
    rate_limit.reset_all()
    for _ in range(5):
        rate_limit.register_failure(1, "admin")
    rate_limit.reset(1, "admin")
    assert not rate_limit.is_locked(1, "admin")


# --- login endpoints --------------------------------------------------------

def test_tablet_login_success(client):
    resp = client.post(
        "/api/tablet/login",
        json={"store_id": 1, "table_no": 1, "table_password": sample_data.TABLE_PASSWORD},
    )
    assert resp.status_code == 200
    assert resp.json()["tablet_token"]
    assert resp.json()["expires_at"]


def test_tablet_login_bad_password_401(client):
    resp = client.post(
        "/api/tablet/login",
        json={"store_id": 1, "table_no": 1, "table_password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_login_success(client):
    resp = client.post(
        "/api/admin/login",
        json={"store_id": 1, "username": sample_data.ADMIN_USERNAME, "password": sample_data.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_admin_login_repeated_failures_return_429(client):
    payload = {"store_id": 1, "username": sample_data.ADMIN_USERNAME, "password": "wrong"}
    statuses = [client.post("/api/admin/login", json=payload).status_code for _ in range(5)]
    assert statuses[:4] == [401, 401, 401, 401]
    assert statuses[4] == 429
    # subsequent attempts remain locked
    assert client.post("/api/admin/login", json=payload).status_code == 429


def test_admin_login_success_resets_counter(client):
    bad = {"store_id": 1, "username": sample_data.ADMIN_USERNAME, "password": "wrong"}
    for _ in range(3):
        client.post("/api/admin/login", json=bad)
    ok = client.post(
        "/api/admin/login",
        json={"store_id": 1, "username": sample_data.ADMIN_USERNAME, "password": sample_data.ADMIN_PASSWORD},
    )
    assert ok.status_code == 200
    # counter reset: 3 more failures should not yet lock
    statuses = [client.post("/api/admin/login", json=bad).status_code for _ in range(3)]
    assert statuses == [401, 401, 401]
