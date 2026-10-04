"""EIA-860M Retired tab (latest month): retired MW per county and distance to big retired plants."""
import geopandas as gpd
import pandas as pd

from src.common.counties import centroids_albers, load_counties
from src.common.geo import nearest_distance_km, points_to_county
from src.common.io import INTERIM, RAW, download, register_source, set_status, write_interim

MONTHS = ["december", "november", "october", "september", "august", "july", "june", "may", "april",
          "march", "february", "january"]
YEARS = [2026, 2025]
MIN_PLANT_MW = 100.0


def latest_860m():
    """Newest monthly file; a cached copy is reused (delete data/raw/eia860m/ to refresh)."""
    for y in YEARS:
        for m in MONTHS:
            cached = RAW / f"eia860m/{m}_generator{y}.xlsx"
            if cached.exists():
                url = f"https://www.eia.gov/electricity/data/eia860m/xls/{m}_generator{y}.xlsx"
                return cached, url, f"{m.title()} {y}"
    for y in YEARS:
        for m in MONTHS:
            url = f"https://www.eia.gov/electricity/data/eia860m/xls/{m}_generator{y}.xlsx"
            try:
                return download(url, f"eia860m/{m}_generator{y}.xlsx"), url, f"{m.title()} {y}"
            except Exception as e:
                print(f"[eia860m] {m} {y} not available: {e}")
    raise RuntimeError("no EIA-860M file found")


def main():
    p, url, label = latest_860m()
    r = pd.read_excel(p, sheet_name="Retired", header=2)
    r = r[pd.to_numeric(r["Plant ID"], errors="coerce").notna()].copy()
    r["Plant ID"] = r["Plant ID"].astype(int)
    r["mw"] = pd.to_numeric(r["Nameplate Capacity (MW)"], errors="coerce")
    r["lat"] = pd.to_numeric(r["Latitude"], errors="coerce")
    r["lon"] = pd.to_numeric(r["Longitude"], errors="coerce")
    plant = r.groupby("Plant ID").agg(
        mw=("mw", "sum"), lat=("lat", "first"), lon=("lon", "first"), name=("Plant Name", "first"),
        state=("Plant State", "first"), last_retired=("Retirement Year", "max"),
    ).reset_index()

    # Fill missing coordinates from the EIA-860 plant file (same Plant ID).
    p860 = INTERIM / "_eia860_plants.parquet"
    n_fill = 0
    if p860.exists():
        ref = pd.read_parquet(p860).set_index("Plant Code")
        miss = plant["lat"].isna() & plant["Plant ID"].isin(ref.index)
        plant.loc[miss, "lat"] = plant.loc[miss, "Plant ID"].map(ref["Latitude"])
        plant.loc[miss, "lon"] = plant.loc[miss, "Plant ID"].map(ref["Longitude"])
        n_fill = int(miss.sum())
    no_xy = plant["lat"].isna() | plant["lon"].isna()
    dropped_mw = plant.loc[no_xy, "mw"].sum()
    big_missing = plant[no_xy & (plant["mw"] >= MIN_PLANT_MW)][["Plant ID", "name", "state", "mw"]]
    pts = gpd.GeoDataFrame(plant[~no_xy], geometry=gpd.points_from_xy(plant.loc[~no_xy, "lon"],
                                                                        plant.loc[~no_xy, "lat"]), crs="EPSG:4326")
    cty = load_counties()
    out = points_to_county(pts, cty, "pwr_retired_capacity_mw", value_col="mw", agg="sum")

    big = pts[pts["mw"] >= MIN_PLANT_MW]
    big.to_parquet(INTERIM / "_retired_plants_100mw.parquet")
    dist = nearest_distance_km(centroids_albers(), big, "pwr_dist_retired_plant_km", all_fips=cty[["fips"]])
    out = out.merge(dist, on="fips", how="left")
    write_interim(out, "eia860m")
    register_source(
        "eia860m", raw_files=[p], name="EIA-860M Preliminary Monthly Electric Generator Inventory, Retired tab",
        url=url, landing_page="https://www.eia.gov/electricity/data/eia860m/", vintage=f"inventory as of {label}",
        license="Public domain (US Government work)",
        notes=(f"Generators aggregated to plants. pwr_retired_capacity_mw sums all retired nameplate MW per county. "
               f"Distance uses plants with >= {MIN_PLANT_MW:.0f} MW total retired. Missing coordinates filled from "
               f"EIA-860 plant file for {n_fill} plants; {int(no_xy.sum())} plants ({dropped_mw:,.0f} MW) still lack "
               f"coordinates and are excluded. Big plants excluded: {big_missing.to_dict('records')}"),
    )
    set_status("eia860m", "OK" if no_xy.sum() == 0 else "PARTIAL",
               f"{len(pts)} retired plants located ({len(big)} >= {MIN_PLANT_MW:.0f} MW); {int(no_xy.sum())} plants "
               f"({dropped_mw:,.0f} MW) without coordinates excluded.",
               ["pwr_retired_capacity_mw", "pwr_dist_retired_plant_km"])


if __name__ == "__main__":
    main()
