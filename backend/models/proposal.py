import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, JSON

from database import Base


class ProposalType(str, enum.Enum):
    ADDRESS_CLEANUP = "address_cleanup"
    REASSIGNMENT = "reassignment"


class ProposalStatus(str, enum.Enum):
    PENDING = "pending"
    EDITED = "edited"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Proposal(Base):
    """An AI-generated suggestion that has NOT taken effect yet.

    Nothing outside routers/proposals.py is allowed to flip a proposal to
    ACCEPTED/EDITED and apply it to Order/Rider state - that boundary is what
    keeps every AI suggestion behind explicit dispatcher approval.
    """

    __tablename__ = "proposals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(Enum(ProposalType), nullable=False)

    target_order_id = Column(String, nullable=True)
    target_rider_id = Column(String, nullable=True)

    proposed_payload = Column(JSON, nullable=False)
    final_payload = Column(JSON, nullable=True)  # set if dispatcher edits before applying

    status = Column(Enum(ProposalStatus), nullable=False, default=ProposalStatus.PENDING)
    reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
