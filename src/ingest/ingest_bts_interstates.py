"""BTS NTAD North American Roads (ArcGIS-hosted copy published by USDOT_BTS): distance to nearest Interstate."""
import json

import geopandas as gpd
import pandas as pd
import requests

from src.common.counties import centroids_albers, load_counties
from src.common.geo import nearest_distance_km
from src.common.io import CONTACT_UA, RAW, register_source, set_status, write_interim

LAYER = "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/NTAD_North_American_Roads/FeatureServer/0"
WHERE = "COUNTRY=2 AND CLASS=1"
PAGE = 2000
OUT = RAW / "bts_interstates"


def _query(params: dict) -> dict:
    r = requests.post(f"{LAYER}/query", data={**params, "where": WHERE, "f": params.get("f", "json")},
                      headers={"User-Agent": CONTACT_UA}, timeout=180)
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        raise RuntimeError(j["error"])
    return j


def fetch() -> list:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"[download] {LAYER}/query where={WHERE}")
    ids = sorted(_query({"returnIdsOnly": "true"})["objectIds"])
    files = []
    for i in range(0, len(ids), PAGE):
        dest = OUT / f"page_{i // PAGE:04d}.geojson"
        files.append(dest)
        if dest.exists():
            continue
        chunk = ids[i:i + PAGE]
        j = _query({"objectIds": ",".join(map(str, chunk)), "outFields": "ROADNUM,JURISNAME,CLASS",
                    "outSR": 4326, "f": "geojson"})
        dest.write_text(json.dumps(j))
    print(f"[download] {len(ids)} interstate segments in {len(files)} pages (cached in {OUT})")
    return files


def main():
    files = fetch()
    roads = pd.concat([gpd.read_file(f) for f in files], ignore_index=True)
    roads = gpd.GeoDataFrame(roads, geometry="geometry", crs="EPSG:4326")
    roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty]
    cty = load_counties()
    out = nearest_distance_km(centroids_albers(), roads, "lnd_dist_interstate_km", all_fips=cty[["fips"]])
    write_interim(out, "bts_interstates")
    register_source(
        "bts_interstates", raw_files=files,
        name="BTS NTAD North American Roads (Interstates, CLASS=1)",
        url=f"{LAYER}/query?where={WHERE}",
        landing_page="https://www.arcgis.com/home/item.html?id=0b6c2fd2e3ac40a7929cdff1d4cf604a",
        vintage="NTAD North American Roads, compiled 2020-10-27 (service data last edited 2025-03-31)",
        license="Public domain (US DOT / BTS)",
        notes=("geodata.bts.gov / bts.gov downloads return HTTP 403 from this machine; used the identical NTAD layer "
               "hosted on ArcGIS Online by owner USDOT_BTS. CLASS=1 = Interstate (ROADNUM 'IH..'), COUNTRY=2 = USA. "
               f"{len(roads)} segments. Distance from population-weighted centroid to nearest segment."),
    )
    set_status("bts_interstates", "OK", f"{len(roads)} interstate segments (BTS NTAD via USDOT_BTS ArcGIS Online).",
               ["lnd_dist_interstate_km"])


if __name__ == "__main__":
    main()
