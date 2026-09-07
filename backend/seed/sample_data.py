"""Sample data definitions for seed_if_empty (contract §11).

DEMO credentials below are local-workshop defaults for a runnable vertical slice.
They are overridable via environment variables; only bcrypt hashes are stored in
the DB. Do not treat these as production secrets.
"""
import os

STORE_NAME = "테이블오더 데모 매장"

ADMIN_USERNAME = "admin"
# DEMO-only default; override with TABLE_ORDER_SEED_ADMIN_PASSWORD
ADMIN_PASSWORD = os.environ.get("TABLE_ORDER_SEED_ADMIN_PASSWORD", "admin1234")

# DEMO-only default; override with TABLE_ORDER_SEED_TABLE_PASSWORD
TABLE_PASSWORD = os.environ.get("TABLE_ORDER_SEED_TABLE_PASSWORD", "table1234")
TABLE_NUMBERS = [1, 2, 3, 4]

CATEGORIES = ["메인", "사이드", "음료"]

# display_order is assigned by insertion order within seed_if_empty.
MENUS = [
    {"category": "메인", "name": "불고기 덮밥", "price": 9000, "description": "직화 불고기와 밥", "image_url": None},
    {"category": "메인", "name": "치킨 마요 덮밥", "price": 8500, "description": "바삭 치킨과 마요", "image_url": None},
    {"category": "메인", "name": "김치찌개", "price": 8000, "description": "얼큰한 김치찌개", "image_url": None},
    {"category": "사이드", "name": "감자튀김", "price": 4500, "description": "바삭한 감자튀김", "image_url": None},
    {"category": "사이드", "name": "계란말이", "price": 5000, "description": "부드러운 계란말이", "image_url": None},
    {"category": "음료", "name": "콜라", "price": 2000, "description": None, "image_url": None},
    {"category": "음료", "name": "사이다", "price": 2000, "description": None, "image_url": None},
    {"category": "음료", "name": "아메리카노", "price": 3000, "description": "따뜻한 아메리카노", "image_url": None},
]
