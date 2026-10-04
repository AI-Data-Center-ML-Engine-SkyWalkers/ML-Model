"""Resolve HIFLD Next (hifld.publicenvirodata.org) dataset assets through its public JSON/STAC API."""
from __future__ import annotations

import json

import requests

from .io import RAW, download

API = "https://hifld.publicenvirodata.org/api/collections/hifld/datasets/{slug}"


def _get(url: str) -> dict:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def resolve(slug: str, fmt: str = "geoparquet") -> dict:
    """Return {'url', 'version', 'meta'} for the latest version of a HIFLD Next dataset."""
    cache = RAW / "hifld" / f"{slug}.resolved.json"
    if cache.exists():
        return json.loads(cache.read_text())
    print(f"[hifld] resolving {API.format(slug=slug)}")
    cat = _get(API.format(slug=slug))
    child = next(l["href"] for l in cat["links"] if l["rel"] == "child")
    sub = _get(child)
    latest = next(l for l in sub["links"] if l["rel"] == "latest-version")
    col = _get(latest["href"])
    asset = next(a for k, a in col["assets"].items() if k.startswith(fmt))
    out = {
        "url": asset["href"], "version": latest.get("title"), "collection": latest["href"],
        "source_dates": col.get("hifld:source_dates"), "agency": col.get("hifld:agency"),
        "office": col.get("hifld:office"), "feature_count": col.get("hifld:feature_count"),
        "columns": [c["name"] for c in col.get("table:columns", [])],
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, indent=2))
    return out


def fetch(slug: str, fmt: str = "geoparquet"):
    info = resolve(slug, fmt)
    ext = info["url"].rsplit(".", 1)[-1]
    path = download(info["url"], f"hifld/{slug}.{ext}", timeout=1800)
    return path, info
