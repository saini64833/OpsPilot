from pydantic import BaseModel

from models.rider import RiderStatus


class RiderCreate(BaseModel):
    name: str
    capacity_weight: float = 20.0
    lat: float
    lng: float


class RiderOut(BaseModel):
    id: str
    name: str
    capacity_weight: float
    current_load: float
    lat: float
    lng: float
    status: RiderStatus

    class Config:
        from_attributes = True
