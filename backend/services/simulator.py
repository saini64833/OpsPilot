import asyncio
from typing import Callable, Awaitable
from sqlalchemy.orm import Session

from models import Rider, RiderStatus, Order, OrderStatus
from services.road_routing import get_road_route

# A large step size for fast simulation (approx 1.5 km per tick)
STEP_SIZE = 0.015  

async def simulation_tick(
    db: Session,
    broadcast: Callable[[dict], Awaitable[None]]
):
    riders = (
        db.query(Rider)
        .filter(Rider.status == RiderStatus.ACTIVE)
        .all()
    )

    if not riders:
        return

    for rider in riders:
        # Fetch ALL active orders for this rider instead of just the first one
        active_orders = (
            db.query(Order)
            .filter(
                Order.rider_id == rider.id, 
                Order.status.in_([OrderStatus.ASSIGNED, OrderStatus.IN_TRANSIT])
            )
            .all()
        )
        
        if active_orders:
            # 1. MOVEMENT: Route towards the first active order's destination
            primary_order = active_orders[0]
            if primary_order.status == OrderStatus.ASSIGNED:
                target_lat = primary_order.pickup_lat
                target_lng = primary_order.pickup_lng
            else:
                target_lat = primary_order.delivery_lat
                target_lng = primary_order.delivery_lng

            route = await get_road_route(rider.lat, rider.lng, target_lat, target_lng)
            
            if route and len(route["coordinates"]) > 1:
                target_idx = min(3, len(route["coordinates"]) - 1)
                next_step_lng, next_step_lat = route["coordinates"][target_idx]
                
                d_lat = next_step_lat - rider.lat
                d_lng = next_step_lng - rider.lng
                distance = (d_lat**2 + d_lng**2)**0.5
                
                if distance > 0:
                    move_dist = min(STEP_SIZE, distance)
                    rider.lat += (d_lat / distance) * move_dist
                    rider.lng += (d_lng / distance) * move_dist

            # 2. STATUS UPDATE LOOP: Check arrival for ALL of the rider's assigned orders
            for order in active_orders:
                if order.status == OrderStatus.ASSIGNED:
                    o_lat = order.pickup_lat
                    o_lng = order.pickup_lng
                else:
                    o_lat = order.delivery_lat
                    o_lng = order.delivery_lng

                dist_to_target = ((o_lat - rider.lat)**2 + (o_lng - rider.lng)**2)**0.5
                
                # If within threshold of THIS specific order's target, update it
                if dist_to_target < 0.005: 
                    if order.status == OrderStatus.ASSIGNED:
                        order.status = OrderStatus.IN_TRANSIT
                        print(f"ORDER {order.id}: Picked up!")
                    elif order.status == OrderStatus.IN_TRANSIT:
                        order.status = OrderStatus.DELIVERED
                        rider.current_load -= order.weight
                        print(f"ORDER {order.id}: Delivered!")

    db.commit()

    data = {
        "type": "riders_updated",
        "riders": [
            {
                "id": r.id,
                "lat": r.lat,
                "lng": r.lng,
                "status": r.status.value,
            }
            for r in riders
        ],
    }

    print("Broadcasting fast road-wise rider update:", data)
    await broadcast(data)


async def run_simulator(
    session_factory,
    broadcast,
    interval_seconds: float = 3.0
):
    while True:
        db = session_factory()
        try:
            await simulation_tick(db, broadcast)
        except Exception as e:
            print("SIMULATOR ERROR:", repr(e))
        finally:
            db.close()
        await asyncio.sleep(interval_seconds)