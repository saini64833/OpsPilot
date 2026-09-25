"""Nudges active riders toward a next-stop position each tick and broadcasts
the update over the WebSocket. This is a placeholder movement model for the
one-day simulation - swap the movement rule for "toward next assigned
order's pickup/delivery" once you want real route-following."""

import asyncio
from typing import Callable, Awaitable

from models import Rider, RiderStatus

STEP_DEGREES = 0.0005


async def simulation_tick(db, broadcast: Callable[[dict], Awaitable[None]]):
    riders = db.query(Rider).filter(Rider.status == RiderStatus.ACTIVE).all()
    if not riders:
        return

    for rider in riders:
        rider.lat += STEP_DEGREES
        rider.lng += STEP_DEGREES

    db.commit()

    await broadcast(
        {
            "type": "riders_updated",
            "riders": [
                {"id": r.id, "lat": r.lat, "lng": r.lng, "status": r.status.value}
                for r in riders
            ],
        }
    )


async def run_simulator(session_factory, broadcast, interval_seconds: float = 3.0):
    while True:
        db = session_factory()
        try:
            await simulation_tick(db, broadcast)
        except Exception:
            # A simulator hiccup should never take the whole app down.
            pass
        finally:
            db.close()
        await asyncio.sleep(interval_seconds)
