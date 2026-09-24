from enum import Enum

from sqlalchemy import Column, Integer, String, Float, Enum as SQLEnum

class RiderStatus(str, Enum):
    ACTIVE = "active"
    BROKEN_DOWN = "broken_down"
    OFFLINE = "offline"


from database import Base


class Rider(Base):
    __tablename__ = "riders"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    capacity_weight = Column(Float, nullable=False)
    current_load = Column(Float, default=0.0, nullable=False)

    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)

    status = Column(
        SQLEnum(RiderStatus),
        default=RiderStatus.ACTIVE,
        nullable=False
    )