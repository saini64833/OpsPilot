import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Order, Rider, OrderStatus
from services.road_routing import get_road_route

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("/order/{order_id}")
async def get_order_route(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    if order.status not in (OrderStatus.ASSIGNED, OrderStatus.IN_TRANSIT):
        raise HTTPException(400, "Order is not currently routable")

    if not order.rider_id:
        raise HTTPException(400, "Order has no rider assigned")

    rider = db.query(Rider).get(order.rider_id)
    if not rider:
        raise HTTPException(404, "Assigned rider not found")

    # Route runs from the rider's CURRENT lat/lng to wherever the order needs
    # to go next - never a saved/cached route - so a breakdown + automatic
    # reassignment to a different rider is reflected on the very next call,
    # with no stale route to invalidate.
    if order.status == OrderStatus.ASSIGNED:
        dest_lat, dest_lng = order.pickup_lat, order.pickup_lng
    else:  # IN_TRANSIT
        dest_lat, dest_lng = order.delivery_lat, order.delivery_lng

    if dest_lat is None or dest_lng is None:
        raise HTTPException(400, "Order is missing destination coordinates")

    try:
        route = await get_road_route(rider.lat, rider.lng, dest_lat, dest_lng)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Routing service unavailable: {exc}") from exc

    if route is None:
        raise HTTPException(404, "Road route not found")

    return route