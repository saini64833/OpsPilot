import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Enum, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from database import Base


class OrderStatus(str, enum.Enum):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    UNPLACED = "UNPLACED"  # address could not be confidently determined


class OrderSource(str, enum.Enum):
    TYPED = "typed"
    PHOTO = "photo"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    pickup_label = Column(String, nullable=True)
    pickup_address = Column(Text, nullable=True)
    pickup_lat = Column(Float, nullable=True)
    pickup_lng = Column(Float, nullable=True)

    delivery_address = Column(Text, nullable=True)
    delivery_lat = Column(Float, nullable=True)
    delivery_lng = Column(Float, nullable=True)

    weight = Column(Float, nullable=False, default=1.0)
    priority = Column(String, nullable=False, default="normal")  # low | normal | high

    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.UNASSIGNED)
    source = Column(Enum(OrderSource), nullable=False, default=OrderSource.TYPED)

    rider_id = Column(String, ForeignKey("riders.id"), nullable=True)

    image_path = Column(String, nullable=True)
    raw_ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rider = relationship("Rider", back_populates="orders")