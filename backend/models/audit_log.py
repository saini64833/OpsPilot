import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, JSON

from database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow)

    entity_type = Column(String, nullable=False)  # "order" | "rider" | "proposal"
    entity_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)  # "system" | "llm" | "dispatcher"
    action = Column(String, nullable=False)

    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    notes = Column(String, nullable=True)
