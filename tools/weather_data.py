# tools/weather_data.py
from typing import Dict, Any, List, Optional, Tuple
import requests
from functools import lru_cache
from difflib import get_close_matches

# Reuse your OSM/Overpass tools
from .trails_api import get_trails_near, get_trails_in_bbox

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Approx Alberta bbox (S, W, N, E)
ALBERTA_BBOX: Tuple[float, float, float, float] = (49.0, -120.0, 60.0, -110.0)

def _clamp_hours(h: int) -> int:
    # Keep payloads small; 6–24 hours is plenty for near-term recs
    return max(1, min(int(h), 24))

def _slim_weather(data: Dict[str, Any], hours: int) -> Dict[str, Any]:
    """
    Reduce Open-Meteo response to only what we need and to at most `hours` entries.
    Keeps: time, temperature_2m, precipitation_probability, precipitation.
    """
    hours = _clamp_hours(hours)
    out: Dict[str, Any] = {"hourly": {}}

    hourly = data.get("hourly", {})
    # Only keep these keys
    keep_keys = ["time", "temperature_2m", "precipitation_probability", "precipitation"]
    for k in keep_keys:
        if k in hourly:
            out["hourly"][k] = hourly[k][:hours]

    # Basic quick summary (helps the LLM reason without lots of tokens)
    try:
        temps = out["hourly"].get("temperature_2m", [])
        precp = out["hourly"].get("precipitation", [])
        pprob = out["hourly"].get("precipitation_probability", [])

        if temps:
            out["summary"] = {
                "min_temp": round(min(temps), 1),
                "max_temp": round(max(temps), 1),
                "any_precip": bool(sum(1 for v in precp if (v or 0) > 0)),
                "max_precip_prob": max(pprob) if pprob else 0,
            }
    except Exception:
        pass

    return out

@lru_cache(maxsize=256)
def get_weather(lat: float, lon: float, hours: int = 24) -> Dict[str, Any]:
    """
    Return a trimmed hourly forecast for the next N hours at (lat, lon).
    Cached to reduce duplicate API calls during prototyping.
    """
    hours = _clamp_hours(hours)
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability,precipitation",
        "forecast_hours": hours,
        "timezone": "America/Edmonton",
    }
    r = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return _slim_weather(data, hours)

def _normalize_name(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def _pick_by_name(trails: List[Dict[str, Any]], trail_name: str) -> Optional[Dict[str, Any]]:
    """Exact match first; otherwise fuzzy pick the closest named trail."""
    if not trails:
        return None
    tname = _normalize_name(trail_name)

    named = [t for t in trails if _normalize_name(t.get("name"))]
    # 1) exact (case-insensitive)
    for t in named:
        if _normalize_name(t.get("name")) == tname:
            return t
    # 2) fuzzy closest
    names = [t["name"] for t in named]
    best = get_close_matches(trail_name, names, n=1, cutoff=0.6)
    if best:
        name = best[0]
        for t in named:
            if t.get("name") == name:
                return t
    # 3) fall back: any item with coords
    with_coords = [t for t in trails if t.get("lat") is not None and t.get("lon") is not None]
    return with_coords[0] if with_coords else None

def weather_for_trail(
    trail_name: str,
    hours: int = 24,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 15.0,
) -> Dict[str, Any]:
    """
    Find a trail by (partial) name via Overpass-derived results and return its coords + trimmed forecast.

    Strategy:
    - If lat/lon provided: query nearby trails (get_trails_near) within radius_km, then name-match.
    - Else: query a broad Alberta bbox (get_trails_in_bbox), then name-match.
    - Returns: {"trail": <trail_dict>, "forecast": <slim_open-meteo json>}
    """
    # 1) Get candidate trails
    if lat is not None and lon is not None:
        candidates = get_trails_near(lat=lat, lon=lon, radius_km=radius_km)
    else:
        s, w, n, e = ALBERTA_BBOX
        candidates = get_trails_in_bbox(s, w, n, e)

    if not candidates:
        raise ValueError("No trails found in the search area.")

    # 2) Pick by name (exact or fuzzy), prefer items with coordinates
    chosen = _pick_by_name(candidates, trail_name)
    if not chosen:
        raise ValueError(f"Trail '{trail_name}' not found in Alberta (or lacks coordinates).")

    tlat, tlon = chosen.get("lat"), chosen.get("lon")
    if tlat is None or tlon is None:
        raise ValueError(f"Trail '{chosen.get('name','Unnamed')}' has no coordinates in OSM center data.")

    # 3) Fetch slim weather
    forecast = get_weather(float(tlat), float(tlon), hours=hours)
    return {"trail": chosen, "forecast": forecast}

