from typing import Optional, Any, Dict

from pydantic import BaseModel

from models.proposal import ProposalType, ProposalStatus


class ProposalOut(BaseModel):
    id: str
    type: ProposalType
    target_order_id: Optional[str] = None
    target_rider_id: Optional[str] = None
    proposed_payload: Dict[str, Any]
    final_payload: Optional[Dict[str, Any]] = None
    status: ProposalStatus
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class ProposalResolve(BaseModel):
    # If provided, this is what actually gets applied (dispatcher edit).
    # If omitted, the original proposed_payload is applied as-is.
    final_payload: Optional[Dict[str, Any]] = None
    resolved_by: str = "dispatcher"
