import math

from sqlalchemy.orm import Session

from models import Order, Rider, OrderStatus, RiderStatus

PRIORITY_PENALTY = {"high": 0, "normal": 2, "low": 4}


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    r = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def score_rider_for_order(rider: Rider, order: Order) -> float:
    """Lower is better. Combines distance-to-pickup with a priority nudge."""
    distance = haversine(rider.lat, rider.lng, order.pickup_lat, order.pickup_lng)
    return distance + PRIORITY_PENALTY.get(order.priority, 2)


def find_best_rider(db: Session, order: Order) -> Rider | None:
    candidates = db.query(Rider).filter(Rider.status == RiderStatus.ACTIVE).all()
    eligible = [r for r in candidates if r.remaining_capacity >= order.weight]
    if not eligible:
        return None
    eligible.sort(key=lambda r: score_rider_for_order(r, order))
    return eligible[0]


def assign_order(db: Session, order: Order) -> bool:
    """Assigns `order` to the best eligible rider in place.

    Returns True if assigned, False if left/marked UNASSIGNED. Never raises
    for "no rider available" - that's an expected outcome, not a failure.
    """
    rider = find_best_rider(db, order)
    if rider is None:
        order.status = OrderStatus.UNASSIGNED
        order.rider_id = None
        return False

    rider.current_load += order.weight
    order.rider_id = rider.id
    order.status = OrderStatus.ASSIGNED
    return True
def assign_unassigned_orders(db: Session) -> int:
    """Try to assign all currently unassigned orders."""

    orders = (
        db.query(Order)
        .filter(Order.status == OrderStatus.UNASSIGNED)
        .all()
    )

    assigned_count = 0

    for order in orders:
        if assign_order(db, order):
            assigned_count += 1

    return assigned_count