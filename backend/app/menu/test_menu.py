"""Menu tests (C2): customer read, admin CRUD, reorder, delete policy, auth.

Covers contract §13 contract-test #3 (menu listing order + 401 without auth).
"""
from seed import sample_data


def _ids_in_order(items):
    return [m["id"] for m in items]


# --- auth boundaries --------------------------------------------------------

def test_customer_menus_require_tablet_auth(client):
    assert client.get("/api/menus").status_code == 401


def test_admin_menus_require_admin_auth(client):
    assert client.get("/api/admin/menus").status_code == 401


def test_admin_token_rejected_on_customer_endpoint(client, admin_headers):
    # admin JWT has typ=admin; customer endpoint expects typ=tablet
    assert client.get("/api/menus", headers=admin_headers).status_code == 401


# --- customer listing -------------------------------------------------------

def test_customer_menus_returned_in_display_order(client, tablet_headers):
    resp = client.get("/api/menus", headers=tablet_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == len(sample_data.MENUS)
    orders = [m["display_order"] for m in items]
    assert orders == sorted(orders)


def test_customer_menus_category_filter(client, tablet_headers):
    resp = client.get("/api/menus", params={"category": "음료"}, headers=tablet_headers)
    assert resp.status_code == 200
    assert all(m["category"] == "음료" for m in resp.json())
    assert len(resp.json()) > 0


# --- admin CRUD -------------------------------------------------------------

def test_admin_create_menu(client, admin_headers):
    resp = client.post(
        "/api/admin/menus",
        json={"category": "메인", "name": "신메뉴", "price": 12000},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "신메뉴" and body["price"] == 12000
    # appended at the end of display order
    assert body["display_order"] == len(sample_data.MENUS)


def test_admin_create_menu_invalid_price_422(client, admin_headers):
    resp = client.post(
        "/api/admin/menus",
        json={"category": "메인", "name": "나쁨", "price": -5},
        headers=admin_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_update_menu(client, admin_headers):
    resp = client.patch("/api/admin/menus/1", json={"price": 9999}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["price"] == 9999


def test_admin_update_missing_menu_404(client, admin_headers):
    resp = client.patch("/api/admin/menus/99999", json={"price": 100}, headers=admin_headers)
    assert resp.status_code == 404


def test_admin_delete_unreferenced_menu(client, admin_headers):
    resp = client.delete("/api/admin/menus/1", headers=admin_headers)
    assert resp.status_code == 204
    # gone from listing
    listed = client.get("/api/admin/menus", headers=admin_headers).json()
    assert 1 not in _ids_in_order(listed)


def test_admin_delete_missing_menu_404(client, admin_headers):
    assert client.delete("/api/admin/menus/99999", headers=admin_headers).status_code == 404


def test_admin_delete_referenced_menu_conflict(client, admin_headers, app):
    # Simulate a reference in order_items (owned by U2 at runtime, but the FK is
    # part of U1's schema). Deleting a referenced menu is a CONFLICT (Known limitation).
    from app.common import config
    from app.persistence.db import get_connection, transaction

    conn = get_connection(config.DB_PATH)
    try:
        with transaction(conn):
            conn.execute(
                "INSERT INTO table_sessions(store_id, table_no, status, started_at) "
                "VALUES(1,1,'ACTIVE','2026-09-07T00:00:00Z')"
            )
            session_id = conn.execute("SELECT id FROM table_sessions LIMIT 1").fetchone()["id"]
            conn.execute(
                "INSERT INTO orders(store_id, table_no, session_id, order_no, status, total, created_at) "
                "VALUES(1,1,?,'A1','PENDING',9000,'2026-09-07T00:00:00Z')",
                (session_id,),
            )
            order_id = conn.execute("SELECT id FROM orders LIMIT 1").fetchone()["id"]
            conn.execute(
                "INSERT INTO order_items(order_id, menu_id, name, unit_price, qty) VALUES(?,?,?,?,?)",
                (order_id, 2, "불고기 덮밥", 9000, 1),
            )
    finally:
        conn.close()

    resp = client.delete("/api/admin/menus/2", headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


# --- reorder ----------------------------------------------------------------

def test_reorder_partial_list_places_listed_first(client, admin_headers):
    before = _ids_in_order(client.get("/api/admin/menus", headers=admin_headers).json())
    # move the last two ids to the front, in reversed order
    listed = [before[-1], before[-2]]
    resp = client.post("/api/admin/menus/reorder", json={"ordered_ids": listed}, headers=admin_headers)
    assert resp.status_code == 204

    after = _ids_in_order(client.get("/api/admin/menus", headers=admin_headers).json())
    assert after[:2] == listed
    # unlisted keep their relative order after the listed ones
    unlisted_before = [i for i in before if i not in listed]
    assert after[2:] == unlisted_before
    # contiguous renumbering 0..N-1
    orders = [m["display_order"] for m in client.get("/api/admin/menus", headers=admin_headers).json()]
    assert orders == list(range(len(after)))


def test_reorder_unknown_id_422(client, admin_headers):
    resp = client.post("/api/admin/menus/reorder", json={"ordered_ids": [99999]}, headers=admin_headers)
    assert resp.status_code == 422


# --- U2-facing lookups (contract §12) ---------------------------------------

def test_get_for_order_returns_price_snapshot(app):
    from app.common import config
    from app.menu import repository
    from app.persistence.db import get_connection

    conn = get_connection(config.DB_PATH)
    try:
        row = repository.get_for_order(conn, 1, 1)
        assert row is not None and row["price"] > 0
        assert repository.get_for_order(conn, 1, 99999) is None


        many = repository.get_many_for_order(conn, 1, [1, 2, 99999])
        assert set(many.keys()) == {1, 2}
        assert many[1]["name"] and many[1]["price"] > 0
    finally:
        conn.close()
