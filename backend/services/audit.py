from typing import Any, Optional

from sqlalchemy.orm import Session

from models import AuditLog


def log_action(
    db: Session,
    entity_type: str,
    entity_id: str,
    actor: str,
    action: str,
    before_state: Optional[dict[str, Any]] = None,
    after_state: Optional[dict[str, Any]] = None,
    raw_payload: Optional[dict[str, Any]] = None,
    notes: Optional[str] = None,
) -> AuditLog:
    """Writes one audit row. Call this in the SAME transaction as any state
    change so a mutation can never happen without a trace, and vice versa."""
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        action=action,
        before_state=before_state,
        after_state=after_state,
        raw_payload=raw_payload,
        notes=notes,
    )
    db.add(entry)
    return entry
