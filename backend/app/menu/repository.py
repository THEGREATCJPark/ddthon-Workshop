"""Menu data access (C2). All queries scoped by store_id (context-derived)."""
import sqlite3

from app.persistence.repository import execute, fetch_all, fetch_one

_COLUMNS = "id, store_id, category, name, price, description, image_url, display_order"


def list_menus(conn: sqlite3.Connection, store_id: int, category: str | None = None):
    if category:
        return fetch_all(
            conn,
            f"SELECT {_COLUMNS} FROM menus WHERE store_id = ? AND category = ? "
            "ORDER BY display_order ASC, id ASC",
            (store_id, category),
        )
    return fetch_all(
        conn,
        f"SELECT {_COLUMNS} FROM menus WHERE store_id = ? ORDER BY display_order ASC, id ASC",
        (store_id,),
    )


def get_menu(conn: sqlite3.Connection, store_id: int, menu_id: int):
    return fetch_one(
        conn,
        f"SELECT {_COLUMNS} FROM menus WHERE store_id = ? AND id = ?",
        (store_id, menu_id),
    )


def max_display_order(conn: sqlite3.Connection, store_id: int) -> int:
    row = fetch_one(
        conn,
        "SELECT COALESCE(MAX(display_order), -1) AS m FROM menus WHERE store_id = ?",
        (store_id,),
    )
    return int(row["m"])


def insert_menu(conn: sqlite3.Connection, store_id: int, data: dict, display_order: int) -> int:
    cur = execute(
        conn,
        "INSERT INTO menus(store_id, category, name, price, description, image_url, display_order) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            store_id,
            data["category"],
            data["name"],
            data["price"],
            data.get("description"),
            data.get("image_url"),
            display_order,
        ),
    )
    return int(cur.lastrowid)


def update_menu(conn: sqlite3.Connection, store_id: int, menu_id: int, fields: dict) -> None:
    if not fields:
        return
    columns = ", ".join(f"{k} = ?" for k in fields)
    params = tuple(fields.values()) + (store_id, menu_id)
    execute(conn, f"UPDATE menus SET {columns} WHERE store_id = ? AND id = ?", params)


def delete_menu(conn: sqlite3.Connection, store_id: int, menu_id: int) -> None:
    execute(conn, "DELETE FROM menus WHERE store_id = ? AND id = ?", (store_id, menu_id))


def count_order_item_refs(conn: sqlite3.Connection, menu_id: int) -> int:
    row = fetch_one(
        conn, "SELECT COUNT(*) AS c FROM order_items WHERE menu_id = ?", (menu_id,)
    )
    return int(row["c"])


def list_ids(conn: sqlite3.Connection, store_id: int) -> list[int]:
    rows = fetch_all(
        conn,
        "SELECT id FROM menus WHERE store_id = ? ORDER BY display_order ASC, id ASC",
        (store_id,),
    )
    return [int(r["id"]) for r in rows]


def set_display_order(conn: sqlite3.Connection, store_id: int, menu_id: int, order: int) -> None:
    execute(
        conn,
        "UPDATE menus SET display_order = ? WHERE store_id = ? AND id = ?",
        (order, store_id, menu_id),
    )


# --- Provided to U2 (order pricing/validation snapshot; contract §12) --------

def get_for_order(conn: sqlite3.Connection, store_id: int, menu_id: int):
    """Return {id, name, price} for a store's menu, or None if absent.

    Used by U2 to snapshot unit_price/name at order time and validate existence.
    """
    return fetch_one(
        conn,
        "SELECT id, name, price FROM menus WHERE store_id = ? AND id = ?",
        (store_id, menu_id),
    )


def get_many_for_order(conn: sqlite3.Connection, store_id: int, menu_ids: list[int]) -> dict[int, dict]:
    """Return {menu_id: {id, name, price}} for the given ids that exist in store."""
    if not menu_ids:
        return {}
    placeholders = ",".join("?" for _ in menu_ids)
    rows = fetch_all(
        conn,
        f"SELECT id, name, price FROM menus WHERE store_id = ? AND id IN ({placeholders})",
        (store_id, *menu_ids),
    )
    return {int(r["id"]): {"id": int(r["id"]), "name": r["name"], "price": int(r["price"])} for r in rows}
