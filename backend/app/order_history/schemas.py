"""Pydantic schemas for OrderHistory admin API (§5.4)."""
from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel


class HistoryItemOut(BaseModel):
    name: str
    qty: int
    unit_price: int


class HistoryRecordOut(BaseModel):
    session_id: int
    order_no: str
    ordered_at: str
    total: int
    items: List[HistoryItemOut]
    completed_at: str
