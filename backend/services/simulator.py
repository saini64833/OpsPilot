import asyncio
from typing import Callable, Awaitable
from sqlalchemy.orm import Session

from models import Rider, RiderStatus, Order, OrderStatus
from services.road_routing import get_road_route

# EXACTLY 80 KM/H (~0.0002 degrees/sec)
STEP_SIZE = 0.0002  

# In-memory route cache: stores current polyline and progress index per rider
# Structure: {rider_id: {"leg": (order_id, status), "coords": [[lng, lat], ...], "index": int}}
_rider_routes: dict[str, dict] = {}


async def simulation_tick(
    db: Session,
    broadcast: Callable[[dict], Awaitable[None]]
):
    # FIX 1: Fetch both ACTIVE and BREAKDOWN riders so the frontend map doesn't crash
    riders = db.query(Rider).filter(
        Rider.status.in_([RiderStatus.ACTIVE, RiderStatus.BREAKDOWN])
    ).all()
    
    if not riders:
        return

    riders_payload = []

    for rider in riders:
        # If the rider is broken down, broadcast their location for the dispatcher but do not move them
        if rider.status == RiderStatus.BREAKDOWN:
            riders_payload.append({
                "id": rider.id,
                "lat": rider.lat,
                "lng": rider.lng,
                "status": rider.status.value,
                "route": None,
                "speed": 0
            })
            continue

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
            current_leg = (str(primary_order.id), primary_order.status.value)
            
            if primary_order.status == OrderStatus.ASSIGNED:
                target_lat, target_lng = primary_order.pickup_lat, primary_order.pickup_lng
            else:
                target_lat, target_lng = primary_order.delivery_lat, primary_order.delivery_lng

            cached = _rider_routes.get(str(rider.id))
            if not cached or cached.get("leg") != current_leg or not cached.get("coords"):
                route = await get_road_route(rider.lat, rider.lng, target_lat, target_lng)
                coords = route.get("coordinates", []) if route else []
                _rider_routes[str(rider.id)] = {
                    "leg": current_leg,
                    "coords": coords,
                    "index": 0
                }
                cached = _rider_routes[str(rider.id)]

            route_coords = cached["coords"]
            current_route_coords = route_coords

            if route_coords and cached["index"] < len(route_coords):
                remaining_step = STEP_SIZE
                idx = cached["index"]

                while remaining_step > 0 and idx < len(route_coords):
                    tgt_lng, tgt_lat = route_coords[idx]
                    d_lat = tgt_lat - rider.lat
                    d_lng = tgt_lng - rider.lng
                    dist = (d_lat**2 + d_lng**2)**0.5

                    if dist <= remaining_step:
                        rider.lat = tgt_lat
                        rider.lng = tgt_lng
                        remaining_step -= dist
                        idx += 1
                    else:
                        rider.lat += (d_lat / dist) * remaining_step
                        rider.lng += (d_lng / dist) * remaining_step
                        remaining_step = 0

                cached["index"] = idx
                speed_kmh = int((STEP_SIZE - remaining_step) * 111 * 3600)
                
            elif route_coords and cached["index"] >= len(route_coords):
                # FIX 2: Safety Catch. If out of road network, snap directly to target to trigger geofence.
                rider.lat = target_lat
                rider.lng = target_lng
                speed_kmh = 10

            # ARRIVAL GEOFENCE
            for order in active_orders:
                o_lat = order.pickup_lat if order.status == OrderStatus.ASSIGNED else order.delivery_lat
                o_lng = order.pickup_lng if order.status == OrderStatus.ASSIGNED else order.delivery_lng
                
                dist_to_final = ((o_lat - rider.lat)**2 + (o_lng - rider.lng)**2)**0.5
                
                if dist_to_final < 0.0005: 
                    if order.status == OrderStatus.ASSIGNED:
                        order.status = OrderStatus.IN_TRANSIT
                        _rider_routes.pop(str(rider.id), None)
                    elif order.status == OrderStatus.IN_TRANSIT:
                        order.status = OrderStatus.DELIVERED
                        rider.current_load -= order.weight
                        _rider_routes.pop(str(rider.id), None)

        else:
            _rider_routes.pop(str(rider.id), None)

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