"""LABEL: Epoch AI Frontier Data Centers - US sites per county (addresses geocoded)."""
import geopandas as gpd
import pandas as pd

from src.common.counties import load_counties
from src.common.geo import points_to_county
from src.common.geocode import geocode
from src.common.io import INTERIM, download, register_source, set_status, write_interim

URL = "https://epoch.ai/data/data_centers/data_centers.csv"


def main():
    p = download(URL, "epoch_ai/data_centers.csv")
    df = pd.read_csv(p)
    us = df[df["Country"] == "United States"].copy()
    rows = []
    for _, r in us.iterrows():
        addr = r["Address"]
        g = geocode(addr) if isinstance(addr, str) and addr.strip() else None
        rows.append({"name": r["Name"], "address": addr, **(g or {"lat": None, "lon": None, "method": "no_address"
                     if not isinstance(addr, str) else "unmatched", "matched": None})})
    geo = pd.DataFrame(rows)
    ok = geo["lat"].notna()
    pts = gpd.GeoDataFrame(geo[ok], geometry=gpd.points_from_xy(geo.loc[ok, "lon"], geo.loc[ok, "lat"]), crs="EPSG:4326")
    cty = load_counties()
    j = gpd.sjoin(pts, cty[["fips", "geometry"]], how="left", predicate="within")
    geo.loc[ok, "fips"] = j["fips"].values
    geo.to_csv(INTERIM / "_epoch_geocoded.csv", index=False)
    out = points_to_county(pts, cty, "lbl_frontier_ai_dc_n")
    write_interim(out, "epoch_ai")
    unmatched = geo[~ok][["name", "address", "method"]].to_dict("records")
    register_source(
        "epoch_ai_frontier_dc", raw_files=[p], name="Epoch AI - Frontier Data Centers dataset", url=URL,
        landing_page="https://epoch.ai/data/ai-data-centers", vintage=f"download {pd.Timestamp.today().date()} (cached)",
        license="CC BY 4.0 (Epoch AI)",
        notes=(f"{len(us)} US sites; addresses geocoded with the US Census Geocoder, OSM Nominatim fallback "
               f"(per-site results: data/interim/_epoch_geocoded.csv). {int(ok.sum())} located; not located: {unmatched}. "
               "LABEL ONLY - never a model input."),
    )
    set_status("epoch_ai_frontier_dc", "OK" if ok.all() else "PARTIAL",
               f"{int(ok.sum())}/{len(us)} US sites geocoded; {len(us) - int(ok.sum())} without a usable address.",
               ["lbl_frontier_ai_dc_n"])


if __name__ == "__main__":
    main()
