import math

from sqlalchemy.orm import Session

from models import Order, Rider, OrderStatus, RiderStatus


PRIORITY_PENALTY = {
    "high": 0,
    "normal": 2,
    "low": 4,
}


def haversine(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float
) -> float:
    """Great-circle distance in km between two lat/lng points."""

    r = 6371

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlmb / 2) ** 2
    )

    return 2 * r * math.asin(math.sqrt(a))


def score_rider_for_order(
    rider: Rider,
    order: Order
) -> float:
    """Lower score = better rider."""

    distance = haversine(
        rider.lat,
        rider.lng,
        order.pickup_lat,
        order.pickup_lng,
    )

    priority_penalty = PRIORITY_PENALTY.get(
        order.priority,
        2,
    )

    return distance + priority_penalty


def find_best_rider(
    db: Session,
    order: Order
) -> Rider | None:

    candidates = (
        db.query(Rider)
        .filter(Rider.status == RiderStatus.ACTIVE)
        .all()
    )

    eligible = [
        rider
        for rider in candidates
        if rider.remaining_capacity >= order.weight
    ]

    if not eligible:
        return None

    eligible.sort(
        key=lambda rider: score_rider_for_order(
            rider,
            order,
        )
    )

    return eligible[0]


def assign_order(
    db: Session,
    order: Order
) -> bool:
    """Assign one order to the best available rider."""

    rider = find_best_rider(db, order)

    if rider is None:
        order.status = OrderStatus.UNASSIGNED
        order.rider_id = None

        print(
            f"ORDER {order.id}: "
            f"no eligible rider available"
        )

        return False

    rider.current_load += order.weight

    order.rider_id = rider.id
    order.status = OrderStatus.ASSIGNED

    print(
        f"ORDER {order.id}: "
        f"assigned to {rider.name} "
        f"({order.weight} kg)"
    )

    return True


def assign_unassigned_orders(
    db: Session
) -> int:
    """Try to assign all currently unassigned orders."""

    orders = (
        db.query(Order)
        .filter(
            Order.status == OrderStatus.UNASSIGNED
        )
        .all()
    )

    assigned_count = 0

    for order in orders:

        if assign_order(db, order):
            assigned_count += 1

    return assigned_count