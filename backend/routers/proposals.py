from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Proposal,
    ProposalStatus,
    Order,
    Rider,
    RiderStatus,
    OrderStatus,
)
from schemas.proposal import ProposalOut, ProposalResolve
from services.audit import log_action


router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("/", response_model=list[ProposalOut])
def list_proposals(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Proposal)

    if status:
        q = q.filter(Proposal.status == status)

    return q.all()


@router.post("/{proposal_id}/accept", response_model=ProposalOut)
def accept_proposal(
    proposal_id: str,
    payload: ProposalResolve,
    db: Session = Depends(get_db),
):
    """
    The ONLY place where an approved reassignment mutates
    order/rider assignment.

    LLM proposals never directly modify order/rider state.
    The dispatcher must explicitly approve the proposal.
    """

    proposal = db.query(Proposal).get(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=404,
            detail="Proposal not found",
        )

    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal already {proposal.status.value}",
        )

    # ---------------------------------------------------------
    # Determine final dispatcher decision
    # ---------------------------------------------------------

    final = (
        payload.final_payload
        if payload.final_payload is not None
        else proposal.proposed_payload
    )

    was_edited = (
        payload.final_payload is not None
        and payload.final_payload != proposal.proposed_payload
    )

    proposal.final_payload = final

    # ---------------------------------------------------------
    # Get order
    # ---------------------------------------------------------

    order = (
        db.query(Order).get(proposal.target_order_id)
        if proposal.target_order_id
        else None
    )

    if not order:
        proposal.status = (
            ProposalStatus.EDITED
            if was_edited
            else ProposalStatus.ACCEPTED
        )

        proposal.resolved_by = payload.resolved_by

        log_action(
            db,
            "proposal",
            proposal.id,
            "dispatcher",
            "dispatcher_approved",
            notes="Target order no longer exists",
        )

        db.commit()
        db.refresh(proposal)

        return proposal

    # ---------------------------------------------------------
    # Current order state
    # ---------------------------------------------------------

    before = {
        "status": order.status.value,
        "rider_id": order.rider_id,
    }

    new_rider_id = final.get("suggested_rider_id")

    # ---------------------------------------------------------
    # Case 1: Dispatcher selected a replacement rider
    # ---------------------------------------------------------

    if new_rider_id:

        new_rider = db.query(Rider).get(new_rider_id)

        if not new_rider:
            raise HTTPException(
                status_code=400,
                detail="Selected rider not found",
            )

        # Replacement rider must currently be operational.
        if new_rider.status != RiderStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail="Selected rider is not active",
            )

        # If assigning to the same rider, don't add the
        # order weight twice.
        if new_rider.id != order.rider_id:

            if new_rider.remaining_capacity < order.weight:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Selected rider no longer has enough "
                        "capacity for this order"
                    ),
                )

            # -------------------------------------------------
            # Remove the order's weight from old rider
            # -------------------------------------------------

            old_rider = (
                db.query(Rider).get(order.rider_id)
                if order.rider_id
                else None
            )

            if old_rider:
                old_rider.current_load = max(
                    0,
                    old_rider.current_load - order.weight,
                )

            # -------------------------------------------------
            # Add order's weight to replacement rider
            # -------------------------------------------------

            new_rider.current_load += order.weight

        order.rider_id = new_rider.id
        order.status = OrderStatus.ASSIGNED

    # ---------------------------------------------------------
    # Case 2: Dispatcher explicitly chose no replacement
    # ---------------------------------------------------------

    else:

        old_rider = (
            db.query(Rider).get(order.rider_id)
            if order.rider_id
            else None
        )

        if old_rider:
            old_rider.current_load = max(
                0,
                old_rider.current_load - order.weight,
            )

        order.rider_id = None
        order.status = OrderStatus.UNASSIGNED

    # ---------------------------------------------------------
    # Audit order change
    # ---------------------------------------------------------

    log_action(
        db,
        "order",
        order.id,
        "dispatcher",
        "dispatcher_edited" if was_edited else "dispatcher_approved",
        before_state=before,
        after_state={
            "status": order.status.value,
            "rider_id": order.rider_id,
        },
    )

    # ---------------------------------------------------------
    # Resolve proposal
    # ---------------------------------------------------------

    proposal.status = (
        ProposalStatus.EDITED
        if was_edited
        else ProposalStatus.ACCEPTED
    )

    proposal.resolved_by = payload.resolved_by

    db.commit()
    db.refresh(proposal)

    return proposal


@router.post("/{proposal_id}/reject", response_model=ProposalOut)
def reject_proposal(
    proposal_id: str,
    payload: ProposalResolve,
    db: Session = Depends(get_db),
):
    """
    Rejecting a proposal does NOT modify the order or rider.

    The original assignment remains untouched.
    """

    proposal = db.query(Proposal).get(proposal_id)

    if not proposal:
        raise HTTPException(
            status_code=404,
            detail="Proposal not found",
        )

    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal already {proposal.status.value}",
        )

    proposal.status = ProposalStatus.REJECTED
    proposal.resolved_by = payload.resolved_by

    log_action(
        db,
        "proposal",
        proposal.id,
        "dispatcher",
        "dispatcher_rejected",
        raw_payload={
            "target_order_id": proposal.target_order_id,
            "target_rider_id": proposal.target_rider_id,
        },
    )

    db.commit()
    db.refresh(proposal)

    return proposal