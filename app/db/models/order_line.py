from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    UniqueConstraint,
    func,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


class OrderLine(Base):
    __tablename__ = "order_lines"
    # make a compose primary key with order_id and line_number
    order_id = Column(
        Integer, ForeignKey("order_headers.order_id"), nullable=False, index=True
    )
    line_number = Column(
        Integer, nullable=False, index=True
    )  # Line number of the item in the order, unique within the scope of each order
    item_id = Column(Integer, nullable=False)
    quantity = Column(
        Integer, nullable=False
    )  # Quantity is whole number, no need for decimal, the partiality should be expressed in the unit of measure

    # Created at timestamp
    created_at = Column(DateTime, server_default=func.now())

    # Updated at timestamp
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    order_header = relationship("OrderHeader", back_populates="order_lines")

    # Composite primary key and unique constraint
    __table_args__ = (
        PrimaryKeyConstraint("order_id", "line_number", name="pk_order_line"),
        UniqueConstraint("order_id", "line_number", name="uq_order_line"),
    )

    def __repr__(self):
        return f"<OrderLine(id={self.order_id}, Line Number='{self.line_number}', Item='{self.item_id}', Quantity='{self.quantity}')>"
