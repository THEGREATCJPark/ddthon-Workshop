"""Menu business logic (C2, contract §5.2).

- Customer/admin listing (store scoped, ordered by display_order).
- Admin create/update/delete and reorder.
- Delete policy (Known limitation, per approved FD): unreferenced menus can be
  deleted; deleting a menu already referenced by order_items is a CONFLICT and
  its detailed policy is deferred (contract §3 FK kept as-is, no ON DELETE).
- Reorder: listed ids first (in given order), then unlisted menus keeping their
  relative order; whole set renumbered 0..N-1.
"""
import sqlite3

from app.common.errors import Conflict, NotFound, ValidationError
from app.menu import repository
from app.persistence.db import transaction

_PATCHABLE = ("category", "name", "price", "description", "image_url")


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_menus(conn: sqlite3.Connection, store_id: int, category: str | None = None) -> list[dict]:
    return [_row_to_dict(r) for r in repository.list_menus(conn, store_id, category)]


def _validate_create(data: dict) -> None:
    for field in ("category", "name"):
        if not str(data.get(field, "")).strip():
            raise ValidationError(f"'{field}'는 필수입니다.")
    if not isinstance(data.get("price"), int) or data["price"] < 0:
        raise ValidationError("'price'는 0 이상의 정수여야 합니다.")


def create_menu(conn: sqlite3.Connection, store_id: int, data: dict) -> dict:
    _validate_create(data)
    with transaction(conn):
        display_order = repository.max_display_order(conn, store_id) + 1
        menu_id = repository.insert_menu(conn, store_id, data, display_order)
    return get_menu(conn, store_id, menu_id)


def get_menu(conn: sqlite3.Connection, store_id: int, menu_id: int) -> dict:
    row = repository.get_menu(conn, store_id, menu_id)
    if row is None:
        raise NotFound("메뉴를 찾을 수 없습니다.")
    return _row_to_dict(row)


def update_menu(conn: sqlite3.Connection, store_id: int, menu_id: int, patch: dict) -> dict:
    get_menu(conn, store_id, menu_id)  # existence check -> 404
    fields = {k: v for k, v in patch.items() if k in _PATCHABLE and v is not None}
    if "price" in fields and (not isinstance(fields["price"], int) or fields["price"] < 0):
        raise ValidationError("'price'는 0 이상의 정수여야 합니다.")
    for field in ("category", "name"):
        if field in fields and not str(fields[field]).strip():
            raise ValidationError(f"'{field}'는 비어 있을 수 없습니다.")
    with transaction(conn):
        repository.update_menu(conn, store_id, menu_id, fields)
    return get_menu(conn, store_id, menu_id)


def delete_menu(conn: sqlite3.Connection, store_id: int, menu_id: int) -> None:
    get_menu(conn, store_id, menu_id)  # existence check -> 404
    if repository.count_order_item_refs(conn, menu_id) > 0:
        # Known limitation: referenced-menu deletion policy deferred (approved FD).
        raise Conflict("주문에서 이미 사용된 메뉴는 삭제할 수 없습니다.")
    with transaction(conn):
        repository.delete_menu(conn, store_id, menu_id)


def reorder(conn: sqlite3.Connection, store_id: int, ordered_ids: list[int]) -> None:
    if not isinstance(ordered_ids, list):
        raise ValidationError("'ordered_ids'는 정수 배열이어야 합니다.")

    current = repository.list_ids(conn, store_id)
    current_set = set(current)

    seen: set[int] = set()
    listed: list[int] = []
    for mid in ordered_ids:
        if not isinstance(mid, int):
            raise ValidationError("'ordered_ids'는 정수 배열이어야 합니다.")
        if mid not in current_set:
            raise ValidationError(f"메뉴 {mid}는 이 매장에 존재하지 않습니다.")
        if mid in seen:
            raise ValidationError(f"메뉴 {mid}가 중복되었습니다.")
        seen.add(mid)
        listed.append(mid)

    # listed first (given order), then unlisted keeping their relative order.
    final_order = listed + [mid for mid in current if mid not in seen]
    with transaction(conn):
        for position, mid in enumerate(final_order):
            repository.set_display_order(conn, store_id, mid, position)
