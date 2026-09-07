"""seed_if_empty implementation (U1 single owner; contract §11).

Seeds a sample store + admin + tables + categorized menus so the core vertical
slice works immediately. Idempotent: seeds only when the DB is empty (stores
table has 0 rows); re-running is a no-op.
"""
import sqlite3

from app.auth.security import hash_password
from app.persistence.db import transaction
from seed import sample_data


def seed_if_empty(conn: sqlite3.Connection) -> bool:
    """Return True if seeding was performed, False if DB already had data."""
    existing = conn.execute("SELECT COUNT(*) AS c FROM stores").fetchone()["c"]
    if existing > 0:
        return False

    with transaction(conn):
        store_id = conn.execute(
            "INSERT INTO stores(name) VALUES(?)", (sample_data.STORE_NAME,)
        ).lastrowid

        conn.execute(
            "INSERT INTO admin_users(store_id, username, password_hash) VALUES(?,?,?)",
            (store_id, sample_data.ADMIN_USERNAME, hash_password(sample_data.ADMIN_PASSWORD)),
        )

        for table_no in sample_data.TABLE_NUMBERS:
            conn.execute(
                "INSERT INTO tables(store_id, table_no, password_hash) VALUES(?,?,?)",
                (store_id, table_no, hash_password(sample_data.TABLE_PASSWORD)),
            )

        for order_idx, menu in enumerate(sample_data.MENUS):
            conn.execute(
                "INSERT INTO menus(store_id, category, name, price, description, image_url, display_order) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    store_id,
                    menu["category"],
                    menu["name"],
                    menu["price"],
                    menu.get("description"),
                    menu.get("image_url"),
                    order_idx,
                ),
            )
    return True
