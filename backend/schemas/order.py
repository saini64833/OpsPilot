from typing import Optional

from pydantic import BaseModel

from models.order import OrderStatus, OrderSource


class OrderCreate(BaseModel):
    pickup_label: Optional[str] = None
    pickup_lat: float
    pickup_lng: float
    delivery_address: Optional[str] = None
    delivery_lat: Optional[float] = None
    delivery_lng: Optional[float] = None
    weight: float
    priority: str = "normal"


class OrderOut(BaseModel):
    id: str
    pickup_label: Optional[str] = None
    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None
    delivery_address: Optional[str] = None
    delivery_lat: Optional[float] = None
    delivery_lng: Optional[float] = None
    weight: float
    priority: str
    status: OrderStatus
    source: OrderSource
    rider_id: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None

    class Config:
        from_attributes = True
