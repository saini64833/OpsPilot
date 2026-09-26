from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import AuditLog

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("/")
def list_audit_log(db: Session = Depends(get_db)):
    entries = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(200).all()
    return [
        {
            "id": e.id,
            # datetime.utcnow() produces a naive datetime; appending "Z"
            # tells the browser's Date parser this is UTC, not local time -
            # without it, every timestamp silently shifts by the viewer's
            # UTC offset.
            "timestamp": (e.timestamp.isoformat() + "Z") if e.timestamp else None,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "actor": e.actor,
            "action": e.action,
            "before_state": e.before_state,
            "after_state": e.after_state,
            "raw_payload": e.raw_payload,
            "notes": e.notes,
        }
        for e in entries
    ]