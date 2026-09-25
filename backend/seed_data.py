"""Run inside the backend container or venv: python seed_data.py"""

from database import Base, engine, SessionLocal
from models import Rider, Order, RiderStatus

Base.metadata.create_all(bind=engine)
db = SessionLocal()

riders = [
    Rider(name="Rider A", capacity_weight=20, current_load=0, lat=28.6139, lng=77.2090, status=RiderStatus.ACTIVE),
    Rider(name="Rider B", capacity_weight=15, current_load=0, lat=28.6200, lng=77.2150, status=RiderStatus.ACTIVE),
    Rider(name="Rider C", capacity_weight=25, current_load=0, lat=28.6300, lng=77.2000, status=RiderStatus.ACTIVE),
]
db.add_all(riders)
db.commit()

orders = [
    Order(
        pickup_label="Store 1", pickup_lat=28.6145, pickup_lng=77.2095,
        delivery_address="12 MG Road", delivery_lat=28.6180, delivery_lng=77.2120,
        weight=3, priority="high",
    ),
    Order(
        pickup_label="Warehouse 2", pickup_lat=28.6250, pickup_lng=77.2100,
        delivery_address="45 Park Street", delivery_lat=28.6280, delivery_lng=77.2140,
        weight=5, priority="normal",
    ),
]
db.add_all(orders)
db.commit()

print(f"Seeded {len(riders)} riders and {len(orders)} orders.")
