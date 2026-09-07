"""Tests for seed_if_empty (contract §11)."""
from app.persistence.db import get_connection, init_db
from seed import sample_data
from seed.seeder import seed_if_empty


def _seeded_conn(db_path):
    conn = get_connection(str(db_path))
    init_db(conn)
    return conn


def test_seed_populates_vertical_slice_data(db_path):
    conn = _seeded_conn(db_path)
    try:
        assert seed_if_empty(conn) is True
        assert conn.execute("SELECT COUNT(*) AS c FROM stores").fetchone()["c"] == 1
        assert conn.execute("SELECT COUNT(*) AS c FROM admin_users").fetchone()["c"] == 1
        assert conn.execute("SELECT COUNT(*) AS c FROM tables").fetchone()["c"] == len(sample_data.TABLE_NUMBERS)
        assert conn.execute("SELECT COUNT(*) AS c FROM menus").fetchone()["c"] == len(sample_data.MENUS)
    finally:
        conn.close()


def test_seed_is_idempotent(db_path):
    conn = _seeded_conn(db_path)
    try:
        assert seed_if_empty(conn) is True
        assert seed_if_empty(conn) is False  # second call is a no-op
        assert conn.execute("SELECT COUNT(*) AS c FROM stores").fetchone()["c"] == 1
    finally:
        conn.close()


def test_seed_display_order_is_sequential(db_path):
    conn = _seeded_conn(db_path)
    try:
        seed_if_empty(conn)
        rows = conn.execute("SELECT display_order FROM menus ORDER BY display_order ASC").fetchall()
        orders = [r["display_order"] for r in rows]
        assert orders == list(range(len(sample_data.MENUS)))
    finally:
        conn.close()


def test_seed_stores_only_password_hashes(db_path):
    conn = _seeded_conn(db_path)
    try:
        seed_if_empty(conn)
        h = conn.execute("SELECT password_hash FROM admin_users LIMIT 1").fetchone()["password_hash"]
        assert h != sample_data.ADMIN_PASSWORD  # never store plaintext
        assert h.startswith("$2")  # bcrypt
    finally:
        conn.close()
