"""Shared auth contexts (FROZEN contract §4).

TabletContext is the ONLY trusted source of store_id/table_no for customer
(tablet) APIs — never taken from request body/query.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AdminContext:
    store_id: int
    admin_user_id: int
    username: str


@dataclass(frozen=True)
class TabletContext:
    store_id: int
    table_no: int
