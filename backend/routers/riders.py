from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Rider, RiderStatus, Proposal, ProposalType, ProposalStatus
from schemas.rider import RiderCreate, RiderOut
from services.audit import log_action
from services.llm_reassignment import propose_reassignment

router = APIRouter(prefix="/riders", tags=["riders"])


@router.get("/", response_model=list[RiderOut])
def list_riders(db: Session = Depends(get_db)):
    return db.query(Rider).all()


@router.post("/", response_model=RiderOut)
def create_rider(payload: RiderCreate, db: Session = Depends(get_db)):
    rider = Rider(**payload.model_dump())
    db.add(rider)
    db.commit()
    db.refresh(rider)
    return rider


@router.post("/{rider_id}/breakdown")
def breakdown_rider(rider_id: str, db: Session = Depends(get_db)):
    """Simulates a disruption. Marks the rider down and asks the LLM for a
    reassignment plan. This endpoint NEVER reassigns orders itself - it only
    creates pending Proposal rows for a dispatcher to review."""
    rider = db.query(Rider).get(rider_id)
    if not rider:
        raise HTTPException(404, "Rider not found")

    before = {"status": rider.status.value}
    rider.status = RiderStatus.BROKEN_DOWN
    log_action(
        db, "rider", rider.id, "system", "rider_broken_down",
        before_state=before, after_state={"status": rider.status.value},
    )
    db.commit()

    try:
        plan = propose_reassignment(db, rider)
    except Exception as e:
        log_action(db, "rider", rider.id, "system", "llm_reassignment_failed", notes=str(e))
        db.commit()
        raise HTTPException(502, "Reassignment proposal failed - orders flagged for manual handling")

    created_ids = []
    for item in plan.proposals:
        proposal = Proposal(
            type=ProposalType.REASSIGNMENT,
            target_order_id=item.order_id,
            target_rider_id=item.suggested_rider_id,
            proposed_payload=item.model_dump(),
            reason=item.reason,
            status=ProposalStatus.PENDING,
        )
        db.add(proposal)
        db.flush()
        log_action(
            db, "proposal", proposal.id, "llm", "llm_proposed_reassignment",
            raw_payload=item.model_dump(),
        )
        created_ids.append(proposal.id)

    db.commit()
    return {"rider_id": rider.id, "proposal_ids": created_ids}
