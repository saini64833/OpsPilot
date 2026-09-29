from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Order, OrderStatus
from schemas.order import OrderCreate, OrderOut
from services.routing import assign_order
from services.audit import log_action
from services.geocoder import get_coordinates_from_text

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=list[OrderOut])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).all()


@router.post("/", response_model=OrderOut)
async def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    order = Order(**payload.model_dump())
    db.add(order)
    db.flush()  # assign an id before we reference it in the audit log

    # Pickup address is always supplied as free text -> geocode it now.
    pickup_lat, pickup_lng = get_coordinates_from_text(order.pickup_address)
    if pickup_lat is None or pickup_lng is None:
        order.status = OrderStatus.UNPLACED
        log_action(
            db,
            "order",
            order.id,
            "system",
            "geocoding_failed",
            notes=f"Could not map pickup address: {order.pickup_address}",
        )
        db.commit()
        db.refresh(order)
        return order

    order.pickup_lat = pickup_lat
    order.pickup_lng = pickup_lng

    # Delivery address is optional at creation time (photo orders fill it
    # in later via the OCR pipeline), but geocode it now if it was given.
    if order.delivery_address:
        delivery_lat, delivery_lng = get_coordinates_from_text(order.delivery_address)
        if delivery_lat is None or delivery_lng is None:
            order.status = OrderStatus.UNPLACED
            log_action(
                db,
                "order",
                order.id,
                "system",
                "geocoding_failed",
                notes=f"Could not map delivery address: {order.delivery_address}",
            )
            db.commit()
            db.refresh(order)
            return order
        order.delivery_lat = delivery_lat
        order.delivery_lng = delivery_lng

    # FIX: ONLY assign the order if we successfully acquired delivery coordinates.
    # Otherwise, it must wait in the UNPLACED state for OCR or dispatcher input.
    if order.delivery_lat is not None and order.delivery_lng is not None:
        await assign_order(db, order)
    else:
        order.status = OrderStatus.UNPLACED

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