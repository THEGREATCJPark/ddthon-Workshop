"""Shared unit-test support for U2 (framework-agnostic).

Builds the contract §3 schema in an in-memory sqlite3 DB and provides fakes for the
consumed U1 ports (Menu lookup, password hasher). No FastAPI/Pydantic needed here —
services/repositories are tested directly.
"""
from __future__ import annotations

import itertools
import sqlite3
from typing import Optional

from app.order.deps import MenuInfo

# Minimal contract §3 schema (only what U2 reads/writes).
SCHEMA = """
CREATE TABLE stores (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE tables (
  id INTEGER PRIMARY KEY, store_id INTEGER, table_no INTEGER NOT NULL,
  password_hash TEXT NOT NULL, UNIQUE(store_id, table_no)
);
CREATE TABLE menus (
  id INTEGER PRIMARY KEY, store_id INTEGER, category TEXT, name TEXT NOT NULL,
  price INTEGER NOT NULL, description TEXT, image_url TEXT, display_order INTEGER DEFAULT 0
);
CREATE TABLE table_sessions (
  id INTEGER PRIMARY KEY, store_id INTEGER, table_no INTEGER NOT NULL,
  status TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT
);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY, store_id INTEGER, table_no INTEGER NOT NULL,
  session_id INTEGER, order_no TEXT NOT NULL, status TEXT NOT NULL,
  total INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE order_items (
  id INTEGER PRIMARY KEY, order_id INTEGER, menu_id INTEGER, name TEXT NOT NULL,
  unit_price INTEGER NOT NULL, qty INTEGER NOT NULL
);
CREATE TABLE order_history (
  id INTEGER PRIMARY KEY, store_id INTEGER, table_no INTEGER, session_id INTEGER,
  order_no TEXT, total INTEGER, items_json TEXT, ordered_at TEXT, completed_at TEXT
);
"""


def make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    return conn


class FakeMenuLookup:
    """In-memory Menu lookup implementing MenuLookupPort."""

    def __init__(self, menus: Optional[dict[int, MenuInfo]] = None) -> None:
        self.menus = menus or {}

    def add(self, menu: MenuInfo) -> None:
        self.menus[menu.id] = menu

    def get_menu(self, store_id: int, menu_id: int) -> Optional[MenuInfo]:
        menu = self.menus.get(menu_id)
        if menu is None or menu.store_id != store_id:
            return None
        return menu


class FakeHasher:
    """Deterministic hasher implementing PasswordHasherPort (no real bcrypt)."""

    def hash_password(self, plaintext: str) -> str:
        return f"hashed::{plaintext}"


class FakeClock:
    """Monotonic ISO-ish clock so created_at ordering is deterministic."""

    def __init__(self, start: int = 0) -> None:
        self._counter = itertools.count(start)

    def __call__(self) -> str:
        n = next(self._counter)
        return f"2026-09-07T00:00:{n:02d}+00:00"
