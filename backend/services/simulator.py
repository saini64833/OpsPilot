import asyncio
from typing import Callable, Awaitable
from sqlalchemy.orm import Session

from models import Rider, RiderStatus, Order, OrderStatus
from services.road_routing import get_road_route

STEP_SIZE = 0.015  

async def simulation_tick(
    db: Session,
    broadcast: Callable[[dict], Awaitable[None]]
):
    riders = db.query(Rider).filter(Rider.status == RiderStatus.ACTIVE).all()
    if not riders:
        return

    riders_payload = []

    for rider in riders:
        active_orders = (
            db.query(Order)
            .filter(
                Order.rider_id == rider.id, 
                Order.status.in_([OrderStatus.ASSIGNED, OrderStatus.IN_TRANSIT])
            )
            .all()
        )
        
        current_route_coords = None
        speed_kmh = 0
        
        if active_orders:
            primary_order = active_orders[0]
            if primary_order.status == OrderStatus.ASSIGNED:
                target_lat, target_lng = primary_order.pickup_lat, primary_order.pickup_lng
            else:
                target_lat, target_lng = primary_order.delivery_lat, primary_order.delivery_lng

            route = await get_road_route(rider.lat, rider.lng, target_lat, target_lng)
            
            # Default target is the final destination
            move_target_lat, move_target_lng = target_lat, target_lng
            
            if route and len(route["coordinates"]) > 0:
                current_route_coords = route["coordinates"]
                
                # Scan the route for the first waypoint that is actually ahead of the rider (> 11 meters away)
                # This prevents the rider from getting permanently stuck on a microscopic waypoint
                for lng, lat in route["coordinates"]:
                    dist = ((lat - rider.lat)**2 + (lng - rider.lng)**2)**0.5
                    if dist > 0.0001:
                        move_target_lat = lat
                        move_target_lng = lng
                        break

            # Move rider towards the chosen target
            d_lat = move_target_lat - rider.lat
            d_lng = move_target_lng - rider.lng
            distance = (d_lat**2 + d_lng**2)**0.5
            
            if distance > 0:
                move_dist = min(STEP_SIZE, distance)
                rider.lat += (d_lat / distance) * move_dist
                rider.lng += (d_lng / distance) * move_dist
                
                # Calculate speed: 1 degree ~ 111km, 1 tick = 1 sec
                speed_kmh = int(move_dist * 111 * 3600)

            # Check arrival threshold (approx 55 meters)
            for order in active_orders:
                o_lat = order.pickup_lat if order.status == OrderStatus.ASSIGNED else order.delivery_lat
                o_lng = order.pickup_lng if order.status == OrderStatus.ASSIGNED else order.delivery_lng
                
                dist_to_target = ((o_lat - rider.lat)**2 + (o_lng - rider.lng)**2)**0.5
                
                if dist_to_target < 0.0005: 
                    if order.status == OrderStatus.ASSIGNED:
                        order.status = OrderStatus.IN_TRANSIT
                        print(f"ORDER {order.id}: Picked up!")
                    elif order.status == OrderStatus.IN_TRANSIT:
                        order.status = OrderStatus.DELIVERED
                        rider.current_load -= order.weight
                        print(f"ORDER {order.id}: Delivered!")

        riders_payload.append({
            "id": rider.id,
            "lat": rider.lat,
            "lng": rider.lng,
            "status": rider.status.value,
            "route": current_route_coords,
            "speed": speed_kmh
        })

    db.commit()
    
    await broadcast({
        "type": "riders_updated",
        "riders": riders_payload,
    })


async def run_simulator(
    session_factory,
    broadcast,
    interval_seconds: float = 1.0
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