from enum import Enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    JSON,
)

from database import Base


class OrderStatus(str, Enum):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class OrderPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class OrderSource(str, Enum):
    TYPED = "typed"
    PHOTO = "photo"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Pickup location
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    pickup_label = Column(String(255), nullable=False)

    # Delivery
    delivery_address = Column(String(500), nullable=False)

    weight = Column(Float, nullable=False)

    priority = Column(
        SQLEnum(OrderPriority),
        default=OrderPriority.MEDIUM,
        nullable=False
    )

    # Nullable because an order can initially be UNASSIGNED
    rider_id = Column(
        Integer,
        ForeignKey("riders.id"),
        nullable=True,
        index=True
    )

    status = Column(
        SQLEnum(OrderStatus),
        default=OrderStatus.UNASSIGNED,
        nullable=False,
        index=True
    )

    source = Column(
        SQLEnum(OrderSource),
        default=OrderSource.TYPED,
        nullable=False
    )

    # OCR information
    raw_ocr_text = Column(String(5000), nullable=True)
    ocr_confidence = Column(Float, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )