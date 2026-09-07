"""Pydantic request/response schemas for Order APIs (§5.3 / §5.4).

Pydantic v2. Response models mirror the exact contract JSON shapes. These are only
used by the FastAPI router layer; the service/repository core stays framework-agnostic.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.order.service import VALID_STATUSES


class OrderItemIn(BaseModel):
    menu_id: int
    qty: int = Field(gt=0)


class CreateOrderRequest(BaseModel):
    items: List[OrderItemIn] = Field(min_length=1)


class CreateOrderResponse(BaseModel):
    order_no: str
    session_id: int
    total: int


class OrderItemOut(BaseModel):
    name: str
    qty: int
    unit_price: int


class CurrentOrderOut(BaseModel):
    order_no: str
    created_at: str
    status: str
    total: int
    items: List[OrderItemOut]


class AdminOrderOut(BaseModel):
    order_id: int
    order_no: str
    created_at: str
    status: str
    total: int
    items: List[OrderItemOut]


class UpdateStatusRequest(BaseModel):
    status: str = Field(description=f"one of {VALID_STATUSES}")


class UpdatedOrderResponse(BaseModel):
    id: int
    status: str


class LatestOrderOut(BaseModel):
    order_no: str
    status: str
    total: int
    created_at: str


class AdminTableOverviewOut(BaseModel):
    table_no: int
    current_total: int
    has_active_session: bool
    latest_orders: List[LatestOrderOut]
