"""Cached address geocoding: US Census Geocoder first, OSM Nominatim as fallback (1 req/s)."""
from __future__ import annotations

import json
import time

import requests

from .io import RAW

# Nominatim rejects generic or placeholder-email user agents; it requires an identifying application name.
NOMINATIM_UA = "datacenter-siting/0.1 (iMasons OCP hackathon research script)"

CACHE = RAW / "geocode" / "cache.json"
CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


def _load() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def _save(c: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, indent=1, sort_keys=True))


def _nominatim(q: str, method: str) -> dict | None:
    time.sleep(1.1)
    try:
        r = requests.get(NOMINATIM, params={"q": q, "format": "json", "limit": 1, "countrycodes": "us"},
                         headers={"User-Agent": NOMINATIM_UA}, timeout=60)
        r.raise_for_status()
        j = r.json()
    except Exception as e:  # pragma: no cover
        print(f"[geocode] nominatim error for {q!r}: {e}")
        return None
    if not j:
        return None
    return {"lat": float(j[0]["lat"]), "lon": float(j[0]["lon"]), "method": method, "matched": j[0].get("display_name")}


def geocode(address: str) -> dict | None:
    """Return {'lat', 'lon', 'method', 'matched'} or None. Results (and misses) are cached."""
    addr = " ".join(str(address).split())
    cache = _load()
    if addr in cache:
        return cache[addr]
    res = None
    try:
        r = requests.get(CENSUS, params={"address": addr, "benchmark": "Public_AR_Current", "format": "json"},
                         timeout=60)
        m = r.json()["result"]["addressMatches"]
        if m:
            res = {"lat": m[0]["coordinates"]["y"], "lon": m[0]["coordinates"]["x"], "method": "census_geocoder",
                   "matched": m[0]["matchedAddress"]}
    except Exception as e:  # pragma: no cover
        print(f"[geocode] census error for {addr!r}: {e}")
    if res is None:
        res = _nominatim(addr, "osm_nominatim")
    if res is None:
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        if len(parts) >= 3:
            res = _nominatim(", ".join(parts[-2:]) if parts[-1].upper() != "USA" else ", ".join(parts[-3:]),
                             "osm_nominatim_city_level")
    cache[addr] = res
    _save(cache)
    return res
