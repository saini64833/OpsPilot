from enum import Enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    JSON,
)

from database import Base


class ProposalType(str, Enum):
    ADDRESS_CLEANUP = "address_cleanup"
    REASSIGNMENT = "reassignment"


class ProposalStatus(str, Enum):
    PENDING = "pending"
    EDITED = "edited"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)

    type = Column(
        SQLEnum(ProposalType),
        nullable=False
    )

    target_order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=True,
        index=True
    )

    target_rider_id = Column(
        Integer,
        ForeignKey("riders.id"),
        nullable=True,
        index=True
    )

    # Proposed changes from LLM
    proposed_payload = Column(
        JSON,
        nullable=False
    )

    status = Column(
        SQLEnum(ProposalStatus),
        default=ProposalStatus.PENDING,
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    resolved_at = Column(
        DateTime,
        nullable=True
    )

    resolved_by = Column(
        String(100),
        nullable=True
    )