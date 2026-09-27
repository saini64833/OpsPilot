"""Run inside the backend container or venv: python seed_data.py"""

from database import Base, engine, SessionLocal
from models import Rider, Order, RiderStatus

# Clears out old data so you get a fresh map every time you run this script
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
db = SessionLocal()

riders = [
    # Placed right next to Order 1 for immediate pickup
    Rider(name="Fast Rider A", capacity_weight=20, current_load=0, lat=28.6140, lng=77.2090, status=RiderStatus.ACTIVE),
    Rider(name="Fast Rider B", capacity_weight=20, current_load=0, lat=28.6150, lng=77.2090, status=RiderStatus.ACTIVE),
        
]
db.add_all(riders)
db.commit()

orders = [
    # Order 1: Will be picked up and delivered quickly
    Order(
        pickup_label="Store 1", pickup_lat=28.6145, pickup_lng=77.2095,
        delivery_address="Delivery 1", delivery_lat=28.6180, delivery_lng=77.2120,
        weight=3, priority="high",
    ),
    # Order 2: Waiting exactly at the drop-off point of Order 1 to demonstrate sequence
    Order(
        pickup_label="Store 2", pickup_lat=28.6180, pickup_lng=77.2120,
        delivery_address="Delivery 2", delivery_lat=28.6250, delivery_lng=77.2100,
        weight=5, priority="normal",
    ),
]
db.add_all(orders)
db.commit()

print(f"Seeded {len(riders)} riders and {len(orders)} orders.")