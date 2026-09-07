"""Pydantic schemas for TableSession/TableConfig admin APIs (§5.4)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CreateTableRequest(BaseModel):
    table_no: int = Field(gt=0)
    table_password: str = Field(min_length=1)


class CreateTableResponse(BaseModel):
    id: int
    store_id: int
    table_no: int


class EndSessionResponse(BaseModel):
    ended: bool
    session_id: int
