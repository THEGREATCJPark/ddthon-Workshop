"""DDL for the shared schema (FROZEN contract §3).

U1 is the schema single-writer and creates ALL contract tables here, including
tables whose CRUD logic is owned by U2 (table_sessions, orders, order_items,
order_history). FK definitions follow §3 exactly.

Note (Known limitation): order_items.menu_id uses the §3 FK definition as-is
(no ON DELETE action). With foreign_keys=ON, deleting a menu still referenced by
order_items is blocked by SQLite; the referenced-menu-deletion policy is deferred
(see functional-design domain-entities §7). Unreferenced menu deletion works.
"""

CREATE_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS stores (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS admin_users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id      INTEGER NOT NULL REFERENCES stores(id),
        username      TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        UNIQUE(store_id, username)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tables (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id      INTEGER NOT NULL REFERENCES stores(id),
        table_no      INTEGER NOT NULL,
        password_hash TEXT NOT NULL,
        UNIQUE(store_id, table_no)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS menus (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id      INTEGER NOT NULL REFERENCES stores(id),
        category      TEXT NOT NULL,
        name          TEXT NOT NULL,
        price         INTEGER NOT NULL,
        description   TEXT,
        image_url     TEXT,
        display_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS table_sessions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id   INTEGER NOT NULL REFERENCES stores(id),
        table_no   INTEGER NOT NULL,
        status     TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id   INTEGER NOT NULL REFERENCES stores(id),
        table_no   INTEGER NOT NULL,
        session_id INTEGER NOT NULL REFERENCES table_sessions(id),
        order_no   TEXT NOT NULL,
        status     TEXT NOT NULL,
        total      INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id   INTEGER NOT NULL REFERENCES orders(id),
        menu_id    INTEGER REFERENCES menus(id),
        name       TEXT NOT NULL,
        unit_price INTEGER NOT NULL,
        qty        INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_history (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id     INTEGER,
        table_no     INTEGER,
        session_id   INTEGER,
        order_no     TEXT,
        total        INTEGER,
        items_json   TEXT,
        ordered_at   TEXT,
        completed_at TEXT
    )
    """,
    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_menus_store_order ON menus(store_id, display_order)",
    "CREATE INDEX IF NOT EXISTS idx_admin_users_store_username ON admin_users(store_id, username)",
    "CREATE INDEX IF NOT EXISTS idx_tables_store_no ON tables(store_id, table_no)",
]
