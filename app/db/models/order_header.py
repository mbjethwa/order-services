from sqlalchemy import Column, DateTime, Integer, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class OrderHeader(Base):
    __tablename__ = "order_headers"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    total_items = Column(Integer, nullable=False)  # Total number of items in the order

    # Created at timestamp
    created_at = Column(DateTime, server_default=func.now())

    # Updated at timestamp
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    order_lines = relationship("OrderLine", back_populates="order_header")

    def __repr__(self):
        return f"<OrderHeader(id={self.order_id}, User='{self.user_id}', Total Items='{self.total_items}')>"
