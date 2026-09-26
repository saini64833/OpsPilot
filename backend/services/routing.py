import math
from sqlalchemy.orm import Session
from models import Order, Rider, OrderStatus, RiderStatus
from services.road_routing import get_road_route 

PRIORITY_PENALTY = {
    "high": 0,
    "normal": 2,
    "low": 4,
}

# Keep haversine to satisfy other imports, but do not use it for routing
def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


async def score_rider_for_order(rider: Rider, order: Order) -> float:
    """Lower score = better rider. MUST be an actual road."""
    
    route_data = await get_road_route(
        start_lat=rider.lat,
        start_lng=rider.lng,
        end_lat=order.pickup_lat,
        end_lng=order.pickup_lng,
    )
    
    # If there is no road connecting them, disqualify the rider completely
    if not route_data:
        return float('inf')
        
    distance_km = route_data["distance"] / 1000
    priority_penalty = PRIORITY_PENALTY.get(order.priority, 2)

    return distance_km + priority_penalty


async def find_best_rider(db: Session, order: Order) -> Rider | None:
    candidates = db.query(Rider).filter(Rider.status == RiderStatus.ACTIVE).all()
    eligible = [r for r in candidates if r.remaining_capacity >= order.weight]

    if not eligible:
        return None

    rider_scores = {}
    for rider in eligible:
        rider_scores[rider.id] = await score_rider_for_order(rider, order)

    eligible.sort(key=lambda rider: rider_scores[rider.id])

    # Ensure the top rider actually has a valid road route
    if rider_scores[eligible[0].id] == float('inf'):
        return None

    return eligible[0]


async def assign_order(db: Session, order: Order) -> bool:
    rider = await find_best_rider(db, order)

    if rider is None:
        order.status = OrderStatus.UNASSIGNED
        order.rider_id = None
        return False

    rider.current_load += order.weight
    order.rider_id = rider.id
    order.status = OrderStatus.ASSIGNED
    return True


async def assign_unassigned_orders(db: Session) -> int:
    orders = db.query(Order).filter(Order.status == OrderStatus.UNASSIGNED).all()
    assigned_count = 0
    for order in orders:
        if await assign_order(db, order):
            assigned_count += 1
    return assigned_count