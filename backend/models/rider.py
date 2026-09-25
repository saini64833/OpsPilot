import enum
import uuid

from sqlalchemy import Column, String, Float, Enum
from sqlalchemy.orm import relationship

from database import Base


class RiderStatus(str, enum.Enum):
    ACTIVE = "active"
    BROKEN_DOWN = "broken_down"
    OFFLINE = "offline"


class Rider(Base):
    __tablename__ = "riders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    capacity_weight = Column(Float, nullable=False, default=20.0)
    current_load = Column(Float, nullable=False, default=0.0)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    status = Column(Enum(RiderStatus), nullable=False, default=RiderStatus.ACTIVE)

    orders = relationship("Order", back_populates="rider")

    @property
    def remaining_capacity(self) -> float:
        return self.capacity_weight - self.current_load
