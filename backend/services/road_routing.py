import asyncio
import math
import time

import httpx

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

# OSRM's public server blocks default python user agents - use your own contact.
HEADERS = {"User-Agent": "OpsPilot/1.0 (your_email@example.com)"}

MAX_RETRIES = 3           # attempts per request before falling back
CACHE_TTL_SECONDS = 5.0   # identical (rounded) lookups within this window are reused
FALLBACK_SPEED_KMH = 25.0 # used only for the straight-line fallback ETA
DETOUR_FACTOR = 1.3       # straight-line -> rough road-distance multiplier

_client: httpx.AsyncClient | None = None
_cache: dict[tuple, tuple[float, dict | None]] = {}


def _get_client() -> httpx.AsyncClient:
    """One shared client = connection reuse instead of a new TLS handshake per call."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=10, headers=HEADERS)
    return _client


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _straight_line_route(start_lat, start_lng, end_lat, end_lng) -> dict:
    """Last-resort route when OSRM is unreachable, so riders keep moving and
    orders can still be scored/assigned instead of everything freezing."""
    km = _haversine_km(start_lat, start_lng, end_lat, end_lng) * DETOUR_FACTOR
    return {
        "distance": km * 1000,
        "duration": km / FALLBACK_SPEED_KMH * 3600,
        "coordinates": [[start_lng, start_lat], [end_lng, end_lat]],
        "source": "fallback",
    }


async def _fetch_shortest(start_lat, start_lng, end_lat, end_lng) -> dict | None:
    url = f"{OSRM_URL}/{start_lng},{start_lat};{end_lng},{end_lat}"
    # alternatives=true makes OSRM return several candidate roads. It ranks by
    # travel time, so we pick the one with the smallest DISTANCE ourselves.
    params = {"overview": "full", "geometries": "geojson", "alternatives": "true"}

    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await _get_client().get(url, params=params)
            if response.status_code == 429 or response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"OSRM returned {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()

            data = response.json()
            if data.get("code") != "Ok" or not data.get("routes"):
                return None  # genuinely no road connection - do not retry

            best = min(data["routes"], key=lambda r: r["distance"])
            return {
                "distance": best["distance"],  # meters
                "duration": best["duration"],  # seconds
                "coordinates": best["geometry"]["coordinates"],  # [[lng, lat], ...]
                "source": "osrm",
            }
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            await asyncio.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s, 2s

    raise last_exc  # type: ignore[misc]


async def get_road_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    allow_fallback: bool = True,
) -> dict | None:
    """Shortest road route between two points.

    Returns None only when OSRM says no road connects the points. If OSRM is
    unreachable and allow_fallback is True, returns a straight-line estimate
    (marked "source": "fallback") instead of raising.
    """
    key = (round(start_lat, 5), round(start_lng, 5), round(end_lat, 5), round(end_lng, 5))
    now = time.monotonic()

    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    try:
        route = await _fetch_shortest(start_lat, start_lng, end_lat, end_lng)
    except (httpx.TransportError, httpx.HTTPStatusError):
        if not allow_fallback:
            raise
        return _straight_line_route(start_lat, start_lng, end_lat, end_lng)  # not cached

    _cache[key] = (now, route)
    if len(_cache) > 500:  # keep memory bounded
        for k in [k for k, (t, _) in _cache.items() if now - t >= CACHE_TTL_SECONDS]:
            _cache.pop(k, None)
    return route