# tools/trails_api.py
from typing import List, Dict, Any
import requests
from functools import lru_cache

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"
HEADERS = {"User-Agent": "TrailMate/0.1 (academic, contact: you@example.com)"}

URBAN_SURFACES = "asphalt|concrete|paving_stones|cement"

def _overpass_query_near(lat: float, lon: float, radius_m: int, hard_only: bool, natural_only: bool) -> str:
    sac = '["sac_scale"~"T3|T4|T5|T6"]' if hard_only else ""
    surf_excl = f'["surface"!~"{URBAN_SURFACES}"]' if natural_only else ""
    # Prefer named relations (routes), then trail ways; exclude urban surfaces if requested
    return f"""
[out:json][timeout:25];
(
  relation(around:{radius_m},{lat},{lon})["route"~"hiking|running"]["name"]{sac};
  way(around:{radius_m},{lat},{lon})["highway"~"path|footway"]{surf_excl}{sac};
);
out center tags 2000;
"""

def _overpass_query_bbox(min_lat: float, min_lon: float, max_lat: float, max_lon: float, hard_only: bool, natural_only: bool) -> str:
    sac = '["sac_scale"~"T3|T4|T5|T6"]' if hard_only else ""
    surf_excl = f'["surface"!~"{URBAN_SURFACES}"]' if natural_only else ""
    return f"""
[out:json][timeout:25];
(
  relation["route"~"hiking|running"]["name"]{sac}({min_lat},{min_lon},{max_lat},{max_lon});
  way["highway"~"path|footway"]{surf_excl}{sac}({min_lat},{min_lon},{max_lat},{max_lon});
);
out center tags 3000;
"""

def _normalize(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for el in elements:
        tags = el.get("tags") or {}
        etype = el.get("type")
        eid = el.get("id")
        name = tags.get("name") or tags.get("name:en") or tags.get("ref") or tags.get("route")
        if not name:
            # synthesize a stable, non-repeating name
            name = f"{('Way' if etype=='way' else 'Route')} {eid}"

        center = el.get("center") or {}
        lat = center.get("lat"); lon = center.get("lon")
        if lat is None or lon is None:
            continue

        out.append({
            "id": eid,
            "osm_type": etype,
            "name": name,
            "route_type": tags.get("route") if etype == "relation" else None,
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "difficulty": tags.get("sac_scale"),
            "surface": tags.get("surface"),
        })

    # dedup
    seen = set(); deduped = []
    for item in out:
        key = (item["osm_type"], item["id"])
        if key not in seen:
            seen.add(key); deduped.append(item)
    # keep it light for the LLM
    return deduped[:20]

def _clamp_radius_km(r: float) -> float:
    return max(0.5, min(float(r), 60.0))  # allow up to 60 km to reach Kananaskis

@lru_cache(maxsize=256)
def get_trails_near(lat: float, lon: float, radius_km: float = 12.0, hard_only: bool = False, natural_only: bool = True) -> List[Dict[str, Any]]:
    radius_m = int(_clamp_radius_km(radius_km) * 1000)
    ql = _overpass_query_near(lat, lon, radius_m, hard_only=hard_only, natural_only=natural_only)
    r = requests.post(OVERPASS_URL, data={"data": ql}, timeout=30, headers=HEADERS)
    if r.status_code != 200:
        print("Overpass error body (near):", r.text[:2000])
    r.raise_for_status()
    return _normalize(r.json().get("elements", []))

@lru_cache(maxsize=64)
def get_trails_in_bbox(min_lat: float, min_lon: float, max_lat: float, max_lon: float, hard_only: bool = False, natural_only: bool = True) -> List[Dict[str, Any]]:
    if min_lat > max_lat or min_lon > max_lon:
        raise ValueError("Invalid bbox.")
    ql = _overpass_query_bbox(min_lat, min_lon, max_lat, max_lon, hard_only=hard_only, natural_only=natural_only)
    r = requests.post(OVERPASS_URL, data={"data": ql}, timeout=60, headers=HEADERS)
    if r.status_code != 200:
        print("Overpass error body (bbox):", r.text[:2000])
    r.raise_for_status()
    return _normalize(r.json().get("elements", []))

