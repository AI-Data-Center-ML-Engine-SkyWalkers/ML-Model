"""Global Energy Monitor: distance to nearest operating US EAF steel plant and operating cement plant."""
import json

import geopandas as gpd
import pandas as pd
import requests

from src.common.counties import centroids_albers, load_counties
from src.common.geo import nearest_distance_km
from src.common.io import RAW, register_source, set_status, write_interim

API = "https://api.globalenergymonitor.org/assets"
TYPES = {"iron-steel-plant": "Iron-Steel-March-2026.xlsx (Global Iron and Steel Tracker, March 2026 + quarterly updates)",
         "cement-plant": "Global Cement and Concrete Tracker, July 2026"}


def fetch(asset_type: str) -> list[dict]:
    dest = RAW / "gem" / f"{asset_type}_US.json"
    if dest.exists():
        print(f"[download] cached {dest}")
        return json.loads(dest.read_text())
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows, offset = [], 0
    while True:
        params = {"asset_type": asset_type, "country": "United States", "include_type_fields": "true",
                  "limit": 500, "offset": offset}
        print(f"[download] {API} {params}")
        r = requests.get(API, params=params, headers={"User-Agent": "curl/8.7.1", "Accept": "application/json"},
                         timeout=120)
        r.raise_for_status()
        j = r.json()
        rows += j["results"]
        offset += j["count"]
        if offset >= j["total"] or not j["count"]:
            break
    dest.write_text(json.dumps(rows))
    return rows


def _pts(df: pd.DataFrame) -> gpd.GeoDataFrame:
    df = df.dropna(subset=["latitude", "longitude"])
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326")


def main():
    steel = pd.DataFrame(fetch("iron-steel-plant"))
    cement = pd.DataFrame(fetch("cement-plant"))
    tf = pd.json_normalize(steel["type_fields"]).add_prefix("tf_")
    steel = pd.concat([steel.drop(columns="type_fields"), tf], axis=1)
    furnace = steel.get("tf_furnace_category", pd.Series("", index=steel.index)).fillna("").astype(str)
    is_eaf = furnace.str.upper().str.contains("EAF") | steel["unit_name"].fillna("").str.contains(r"\bEAF\b")
    eaf = steel[(steel["operating_status"] == "operating") & is_eaf]
    eaf_plants = eaf.drop_duplicates("location_id")
    cem = cement[cement["operating_status"] == "operating"]
    cty = load_counties()
    cen = centroids_albers()
    out = nearest_distance_km(cen, _pts(eaf_plants), "lnd_dist_eaf_steel_km", all_fips=cty[["fips"]])
    out = out.merge(nearest_distance_km(cen, _pts(cem), "lnd_dist_cement_km", all_fips=cty[["fips"]]), on="fips")
    write_interim(out, "gem_heavy_industry")
    register_source(
        "gem_heavy_industry", raw_files=[RAW / "gem" / f"{t}_US.json" for t in TYPES],
        name="Global Energy Monitor - Global Iron and Steel Tracker + Global Cement and Concrete Tracker (via GEM API)",
        url=f"{API}?asset_type={{iron-steel-plant|cement-plant}}&country=United States&include_type_fields=true",
        landing_page="https://globalenergymonitor.org/projects/global-iron-steel-tracker ; https://globalenergymonitor.org/projects/global-cement-concrete-tracker",
        vintage="; ".join(TYPES.values()), license="CC BY 4.0 (Global Energy Monitor)",
        notes=(f"Pulled from GEM's public asset API instead of the form-gated xlsx (same tracker sources, ids 10/11). "
               f"Steel: unit-level, operating_status == operating and furnace category / unit name contains EAF -> "
               f"{len(eaf)} units at {len(eaf_plants)} plants. Cement: operating plants ({len(cem)}). Distance from "
               "the population-weighted centroid to the nearest plant."),
    )
    set_status("gem_heavy_industry", "OK", f"{len(eaf_plants)} operating EAF plants, {len(cem)} operating cement plants.",
               ["lnd_dist_eaf_steel_km", "lnd_dist_cement_km"])


if __name__ == "__main__":
    main()
