from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Order
from schemas.order import OrderCreate, OrderOut
from services.routing import assign_order
from services.audit import log_action

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=list[OrderOut])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).all()


@router.post("/", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    order = Order(**payload.model_dump())
    db.add(order)
    db.flush()  # assign an id before we reference it in the audit log

    assign_order(db, order)
    log_action(
        db,
        "order",
        order.id,
        "system",
        "order_created",
        after_state={"status": order.status.value, "rider_id": order.rider_id},
    )
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order
