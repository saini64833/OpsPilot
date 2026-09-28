from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Rider,
    RiderStatus,
    Proposal,
    ProposalType,
    ProposalStatus,
)
from schemas.rider import RiderCreate, RiderOut
from services.audit import log_action
from services.llm_reassignment import propose_reassignment
from services.routing import assign_unassigned_orders


router = APIRouter(prefix="/riders", tags=["riders"])


@router.get("/", response_model=list[RiderOut])
def list_riders(db: Session = Depends(get_db)):
    return db.query(Rider).all()


@router.post("/", response_model=RiderOut)
def create_rider(
    payload: RiderCreate,
    db: Session = Depends(get_db),
):
    rider = Rider(**payload.model_dump())

    db.add(rider)
    db.commit()
    db.refresh(rider)

    return rider


@router.post("/{rider_id}/restore", response_model=RiderOut)
async def restore_rider(
    rider_id: str,
    db: Session = Depends(get_db),
):
    """
    Restore a previously broken/offline rider.

    Important:
    - Existing orders that still belong to this rider are NOT moved.
    - Approved reassigned orders are NOT moved back.
    - Only genuinely UNASSIGNED orders may be assigned again.
    """

    rider = db.query(Rider).get(rider_id)

    if not rider:
        raise HTTPException(
            status_code=404,
            detail="Rider not found",
        )

    if rider.status == RiderStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Rider is already active",
        )

    before = {
        "status": rider.status.value,
        "current_load": rider.current_load,
    }

    # Restore rider
    rider.status = RiderStatus.ACTIVE

    # Existing orders that were never reassigned remain with this rider.
    # We DO NOT touch them here.
    #
    # Only orders whose rider_id is NULL and status is UNASSIGNED
    # are eligible for normal routing.
    assigned_count = await assign_unassigned_orders(db)

    log_action(
        db,
        "rider",
        rider.id,
        "dispatcher",
        "rider_restored",
        before_state=before,
        after_state={
            "status": rider.status.value,
            "current_load": rider.current_load,
        },
        notes=f"Restored rider; {assigned_count} unassigned order(s) re-routed",
    )

    db.commit()
    db.refresh(rider)

    return rider


@router.post("/{rider_id}/breakdown")
async def breakdown_rider(
    rider_id: str,
    db: Session = Depends(get_db),
):
    """
    Simulate a rider disruption.

    The rider becomes BROKEN_DOWN.

    Existing assigned orders remain untouched.

    The LLM only creates reassignment proposals.
    No order is reassigned automatically.
    """

    rider = db.query(Rider).get(rider_id)

    if not rider:
        raise HTTPException(
            status_code=404,
            detail="Rider not found",
        )

    # Prevent duplicate breakdown
    if rider.status == RiderStatus.BROKEN_DOWN:
        raise HTTPException(
            status_code=400,
            detail="Rider is already broken down",
        )

    before = {
        "status": rider.status.value,
        "current_load": rider.current_load,
    }

    # Mark rider as broken
    rider.status = RiderStatus.BROKEN_DOWN

    log_action(
        db,
        "rider",
        rider.id,
        "system",
        "rider_broken_down",
        before_state=before,
        after_state={
            "status": rider.status.value,
            "current_load": rider.current_load,
        },
    )

    db.commit()

    # ---------------------------------------------------------
    # Generate LLM proposals
    # ---------------------------------------------------------

    try:
        plan = await propose_reassignment(db, rider)
    except Exception as e:
        log_action(
            db,
            "rider",
            rider.id,
            "system",
            "llm_reassignment_failed",
            notes=str(e),
        )

        db.commit()

        raise HTTPException(
            status_code=502,
            detail=(
                "Reassignment proposal failed. "
                "Rider remains broken down and existing orders "
                "remain preserved for manual handling."
            ),
        )

    # ---------------------------------------------------------
    # Save proposals
    # ---------------------------------------------------------

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
            db,
            "proposal",
            proposal.id,
            "llm",
            "llm_proposed_reassignment",
            raw_payload=item.model_dump(),
        )

        created_ids.append(proposal.id)

    db.commit()

    return {
        "rider_id": rider.id,
        "proposal_ids": created_ids,
        "proposal_count": len(created_ids),
        "message": (
            "Rider marked as broken down. "
            "Orders remain unchanged until dispatcher approval."
        ),
    }