"""Shared pytest setup for U1 tests.

Ensures ``backend/`` (the package root containing ``app`` and ``seed``) is on
sys.path, and provides fixtures that build a U1 test app against an isolated
temporary SQLite DB. This is test scaffolding only — the real composition root
(main.py) is owned by the Integration Lead.
"""
import os
import sys

import pytest

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def app(db_path):
    from app.common.testing import build_test_app

    return build_test_app(db_path, seed=True)


@pytest.fixture
def app_empty(db_path):
    from app.common.testing import build_test_app

    return build_test_app(db_path, seed=False)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def admin_token(client):
    from seed import sample_data

    resp = client.post(
        "/api/admin/login",
        json={"store_id": 1, "username": sample_data.ADMIN_USERNAME, "password": sample_data.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def tablet_token(client):
    from seed import sample_data

    resp = client.post(
        "/api/tablet/login",
        json={"store_id": 1, "table_no": sample_data.TABLE_NUMBERS[0], "table_password": sample_data.TABLE_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["tablet_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def tablet_headers(tablet_token):
    return {"Authorization": f"Bearer {tablet_token}"}
