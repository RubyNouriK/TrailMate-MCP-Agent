# tools/geocode.py
from typing import Dict
import requests

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "TrailMate/0.1 (academic contact: danielamanozcacruz@ucalgary.ca)"}

def geocode_place(place: str) -> Dict[str, float]:
    """
    Geocode a place name in Alberta (e.g., 'Calgary') to lat/lon using OSM Nominatim.
    Returns: {"lat": float, "lon": float}
    """
    params = {"q": f"{place}, Alberta, Canada", "format": "json", "limit": 1}
    r = requests.get(NOMINATIM, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    results = r.json()
    if not results:
        raise ValueError(f"Could not geocode '{place}' in Alberta.")
    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])
    return {"lat": lat, "lon": lon}
