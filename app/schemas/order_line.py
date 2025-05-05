# Pydantic models for request/response validation, keep separate from database models

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OrderLineCreateRequest(BaseModel):
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderLineReadRequest(BaseModel):
    order_id: int
    line_number: int
    item_id: int
    quantity: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Enables compatibility with SQLAlchemy models
