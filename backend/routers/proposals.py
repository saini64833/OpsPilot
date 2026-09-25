from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Proposal, ProposalStatus, Order, Rider, OrderStatus
from schemas.proposal import ProposalOut, ProposalResolve
from services.audit import log_action

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("/", response_model=list[ProposalOut])
def list_proposals(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Proposal)
    if status:
        q = q.filter(Proposal.status == status)
    return q.all()


@router.post("/{proposal_id}/accept", response_model=ProposalOut)
def accept_proposal(proposal_id: str, payload: ProposalResolve, db: Session = Depends(get_db)):
    """The ONLY place a reassignment proposal is allowed to mutate order/
    rider state. If final_payload differs from what the LLM proposed, this
    is logged as a dispatcher edit rather than a plain approval."""
    proposal = db.query(Proposal).get(proposal_id)
    if not proposal:
        raise HTTPException(404, "Proposal not found")
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(400, f"Proposal already {proposal.status.value}")

    final = payload.final_payload or proposal.proposed_payload
    was_edited = payload.final_payload is not None and payload.final_payload != proposal.proposed_payload
    proposal.final_payload = final

    order = db.query(Order).get(proposal.target_order_id) if proposal.target_order_id else None
    if order:
        before = {"status": order.status.value, "rider_id": order.rider_id}
        new_rider_id = final.get("suggested_rider_id")

        if new_rider_id:
            rider = db.query(Rider).get(new_rider_id)
            if not rider or rider.remaining_capacity < order.weight:
                raise HTTPException(400, "Selected rider no longer has capacity for this order")
            rider.current_load += order.weight
            order.rider_id = new_rider_id
            order.status = OrderStatus.ASSIGNED
        else:
            order.rider_id = None
            order.status = OrderStatus.UNASSIGNED

        log_action(
            db, "order", order.id, "dispatcher",
            "dispatcher_edited" if was_edited else "dispatcher_approved",
            before_state=before,
            after_state={"status": order.status.value, "rider_id": order.rider_id},
        )

    proposal.status = ProposalStatus.EDITED if was_edited else ProposalStatus.ACCEPTED
    proposal.resolved_by = payload.resolved_by
    db.commit()
    db.refresh(proposal)
    return proposal


@router.post("/{proposal_id}/reject", response_model=ProposalOut)
def reject_proposal(proposal_id: str, payload: ProposalResolve, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).get(proposal_id)
    if not proposal:
        raise HTTPException(404, "Proposal not found")
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(400, f"Proposal already {proposal.status.value}")

    proposal.status = ProposalStatus.REJECTED
    proposal.resolved_by = payload.resolved_by
    log_action(db, "proposal", proposal.id, "dispatcher", "dispatcher_rejected")
    db.commit()
    db.refresh(proposal)
    return proposal
