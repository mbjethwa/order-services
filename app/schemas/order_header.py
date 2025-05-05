# Pydantic models for request/response validation, keep separate from database models

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from app.schemas.order_line import OrderLineCreateRequest, OrderLineReadRequest


class OrderHeaderCreateRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    total_items: int = Field(None, gt=0)
    order_lines: list[OrderLineCreateRequest]

    @field_validator("order_lines")
    def check_list_items_not_empty(cls, v):
        if len(v) < 1:
            raise ValueError("order_lines list must contain at least one item")
        return v


class OrderHeaderReadRequest(BaseModel):
    order_id: int
    user_id: int
    total_items: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    order_lines: list[OrderLineReadRequest] = []

    class Config:
        from_attributes = True  # Enables compatibility with SQLAlchemy models
