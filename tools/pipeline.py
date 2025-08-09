# tools/pipeline.py
from typing import Dict, Any
from .geocode import geocode_place
from .trails_api import get_trails_near
from .weather_data import get_weather

def recommend_near_place(place: str, radius_km: float = 12.0, hours: int = 12) -> Dict[str, Any]:
    """
    Deterministic helper: geocode place (in Alberta), fetch nearby trails, fetch area weather.
    Returns {"place": {...}, "trails": [...], "weather": {...}}
    """
    loc = geocode_place(place)  # {"lat","lon"}
    trails = get_trails_near(lat=loc["lat"], lon=loc["lon"], radius_km=radius_km)
    weather = get_weather(lat=loc["lat"], lon=loc["lon"], hours=hours)
    return {"place": {"name": place, **loc}, "trails": trails, "weather": weather}
