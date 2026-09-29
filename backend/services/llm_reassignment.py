import asyncio
import json

from sqlalchemy.orm import Session

from models import Order, Rider, RiderStatus, OrderStatus
from schemas.llm_outputs import ReassignmentPlan
from services.llm_address_cleanup import _call_llm, _strip_code_fence
from services.routing import haversine
from services.road_routing import get_road_route

SYSTEM_PROMPT = (
    "You are a dispatch assistant. Given a broken-down rider's remaining "
    "orders and the current state of other riders, propose a reassignment "
    "for each order. Only assign to riders with enough remaining capacity "
    "(given to you as a number, do not do your own arithmetic to override "
    "it). Prefer riders closer to the pickup location and prioritize "
    "high-priority orders. If no rider can take an order, set "
    "suggested_rider_id to null rather than overloading someone. Return "
    "ONLY JSON, no other text, matching this shape: "
    '{"proposals": [{"order_id": string, "suggested_rider_id": string|null, '
    '"reason": string}]}'
)

async def propose_reassignment(db: Session, broken_rider: Rider) -> ReassignmentPlan:
    orders = (
        db.query(Order)
        .filter(Order.rider_id == broken_rider.id, Order.status == OrderStatus.ASSIGNED)
        .all()
    )
    other_riders = (
        db.query(Rider)
        .filter(Rider.status == RiderStatus.ACTIVE, Rider.id != broken_rider.id)
        .all()
    )

    async def road_km(r, o):
        route = await get_road_route(r.lat, r.lng, o.pickup_lat, o.pickup_lng)
        return round(route["distance"] / 1000, 2) if route else None

    # Fire every rider x order lookup CONCURRENTLY. The previous version
    # awaited these one at a time inside nested loops - with N riders and M
    # orders that's N x M sequential OSRM round trips (each with its own
    # retry/backoff), which is exactly what made a breakdown feel stuck or
    # unresponsive rather than just slow.
    pairs = [(r, o) for r in other_riders for o in orders]
    results = await asyncio.gather(*(road_km(r, o) for r, o in pairs)) if pairs else []
    road_distances: dict[str, dict[str, float | None]] = {r.id: {} for r in other_riders}
    for (r, o), km in zip(pairs, results):
        road_distances[r.id][o.id] = km

    context = {
        "orders": [
            {
                "order_id": o.id,
                "pickup_lat": o.pickup_lat,
                "pickup_lng": o.pickup_lng,
                "weight": o.weight,
                "priority": o.priority,
            }
            for o in orders
        ],
        "riders": [
            {
                "rider_id": r.id,
                "remaining_capacity": r.remaining_capacity,
                "distances_to_pickups_km": road_distances[r.id],
            }
            for r in other_riders
        ],
    }

    # Run the blocking LLM call in a thread so it doesn't freeze the event
    # loop (and therefore the live map's WebSocket updates) while it retries.
    content = await asyncio.to_thread(_call_llm, SYSTEM_PROMPT, json.dumps(context))
    data = json.loads(_strip_code_fence(content))
    plan = ReassignmentPlan(**data)

    rider_by_id = {r.id: r for r in other_riders}
    order_by_id = {o.id: o for o in orders}

    for item in plan.proposals:
        if item.order_id not in order_by_id:
            item.suggested_rider_id = None
            item.reason = "LLM referenced an unknown order_id; suggestion discarded"
            continue
        if item.suggested_rider_id:
            rider = rider_by_id.get(item.suggested_rider_id)
            order = order_by_id[item.order_id]
            if rider is None or rider.remaining_capacity < order.weight:
                item.suggested_rider_id = None
                item.reason = "LLM suggestion failed capacity/existence re-check; left unassigned"

    return plan