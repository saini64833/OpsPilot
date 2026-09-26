import httpx

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

async def get_road_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
) -> dict | None:
    url = f"{OSRM_URL}/{start_lng},{start_lat};{end_lng},{end_lat}"
    params = {"overview": "full", "geometries": "geojson"}
    
    # ADDED: Custom User-Agent header (OSRM blocks default python headers)
    headers = {
        "User-Agent": "MyPythonRoutingApp/1.0 (your_email@example.com)"
    }

    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        response = await client.get(url, params=params)
    
    response.raise_for_status()

    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    route = data["routes"][0]
    return {
        "distance": route["distance"],  # meters
        "duration": route["duration"],  # seconds
        "coordinates": route["geometry"]["coordinates"],  # [ [lng, lat], ... ]
    }