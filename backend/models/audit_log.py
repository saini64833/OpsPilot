from enum import Enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum as SQLEnum,
    JSON,
)

from database import Base


class EntityType(str, Enum):
    ORDER = "order"
    RIDER = "rider"


class Actor(str, Enum):
    SYSTEM = "system"
    LLM = "llm"
    DISPATCHER = "dispatcher"


class AuditAction(str, Enum):
    OCR_EXTRACTED = "ocr_extracted"
    OCR_FAILED = "ocr_failed"

    LLM_PROPOSED_ADDRESS = "llm_proposed_address"
    LLM_PROPOSED_REASSIGNMENT = "llm_proposed_reassignment"
    LLM_CALL_FAILED = "llm_call_failed"

    DISPATCHER_EDITED = "dispatcher_edited"
    DISPATCHER_APPROVED = "dispatcher_approved"
    DISPATCHER_REJECTED = "dispatcher_rejected"

    ASSIGNMENT_CHANGED = "assignment_changed"
    STATUS_CHANGED = "status_changed"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    entity_type = Column(
        SQLEnum(EntityType),
        nullable=False
    )

    entity_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    actor = Column(
        SQLEnum(Actor),
        nullable=False
    )

    action = Column(
        SQLEnum(AuditAction),
        nullable=False
    )

    # Previous state
    before_state = Column(
        JSON,
        nullable=True
    )

    # New state
    after_state = Column(
        JSON,
        nullable=True
    )

    # Raw OCR / LLM payload
    raw_payload = Column(
        JSON,
        nullable=True
    )

    notes = Column(
        Text,
        nullable=True
    )