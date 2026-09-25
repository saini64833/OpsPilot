from typing import Optional, List

from pydantic import BaseModel, Field


class CleanedAddress(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    confidence: str = Field(description="'high' or 'low'")
    notes: Optional[str] = None


class ReassignmentItem(BaseModel):
    order_id: str
    suggested_rider_id: Optional[str] = None
    reason: str


class ReassignmentPlan(BaseModel):
    proposals: List[ReassignmentItem]
