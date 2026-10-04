"""Grid water intensity: EIA-923 Schedule 8D cooling water consumption / net generation, by eGRID subregion.

For each eGRID subregion: total water consumed by plant cooling systems (liters) divided by the
net generation of ALL plants in the subregion (kWh), so non-thermal generation counts as zero water.
Then area-weighted overlay of subregions onto counties.
"""
import geopandas as gpd
import numpy as np
import pandas as pd

from src.common.counties import load_counties
from src.common.geo import polygon_area_weighted_mean
from src.common.io import INTERIM, download, register_source, set_status, unzip, write_interim
from src.ingest.ingest_epa_egrid import load_egrid_sheet, load_subregions

YEAR = 2025
URL = f"https://www.eia.gov/electricity/data/eia923/xls/f923_{YEAR}.zip"
GAL_TO_L = 3.785411784


def main():
    z = download(URL, f"eia923/f923_{YEAR}.zip", timeout=900)
    folder = unzip(z)
    cool = pd.read_excel(folder / f"EIA923_Schedule_8_Annual_Envir_Infor_{YEAR}_Final.xlsx",
                         sheet_name="8D Cooling System Information", header=4)
    cons_col = next(c for c in cool.columns if c.startswith("Consumption Volume"))
    cool["mgal"] = pd.to_numeric(cool[cons_col], errors="coerce")
    water = cool.groupby("Plant ID")["mgal"].sum(min_count=1).rename("cons_mgal").reset_index()
    water = water.rename(columns={"Plant ID": "plant"})

    gen = pd.read_excel(folder / f"EIA923_Schedules_2_3_4_5_M_12_{YEAR}_Final.xlsx",
                        sheet_name="Page 1 Generation and Fuel Data", header=5)
    gen = gen[pd.to_numeric(gen["Plant Id"], errors="coerce").notna()]
    gen = gen[gen["Plant Id"].astype(int) != 99999]  # state-fuel imputation increments have no plant
    gen["mwh"] = pd.to_numeric(gen["Net Generation\n(Megawatthours)"], errors="coerce")
    g = gen.groupby(gen["Plant Id"].astype(int))["mwh"].sum().rename("netgen_mwh").reset_index()
    g = g.rename(columns={"Plant Id": "plant"})

    # Plant -> eGRID subregion: eGRID2023 plant table, else spatial join of EIA-860 coordinates.
    plnt, _ = load_egrid_sheet("PLNT23")
    sub_map = plnt.dropna(subset=["ORISPL"]).set_index(plnt["ORISPL"].dropna().astype(int))["SUBRGN"]
    plants = g.merge(water, on="plant", how="outer")
    plants["SUBRGN"] = plants["plant"].map(sub_map)
    shp, _ = load_subregions()
    p860 = pd.read_parquet(INTERIM / "_eia860_plants.parquet").set_index("Plant Code")
    need = plants["SUBRGN"].isna() & plants["plant"].isin(p860.index)
    if need.any():
        sub = plants[need].copy()
        sub["lat"] = sub["plant"].map(p860["Latitude"])
        sub["lon"] = sub["plant"].map(p860["Longitude"])
        sub = sub.dropna(subset=["lat", "lon"])
        pts = gpd.GeoDataFrame(sub, geometry=gpd.points_from_xy(sub["lon"], sub["lat"]), crs="EPSG:4326")
        j = gpd.sjoin(pts.to_crs(shp.crs), shp.rename(columns={"SUBRGN": "SR"}), how="left", predicate="within")
        j = j[~j.index.duplicated()]
        plants.loc[j.index, "SUBRGN"] = j["SR"].values
    n_spatial = int(need.sum())
    unmapped = plants["SUBRGN"].isna()
    unmapped_mwh = plants.loc[unmapped, "netgen_mwh"].sum()

    sr = plants[~unmapped].groupby("SUBRGN").agg(cons_mgal=("cons_mgal", "sum"), netgen_mwh=("netgen_mwh", "sum"))
    sr["wtr_grid_water_l_kwh"] = sr["cons_mgal"] * 1e6 * GAL_TO_L / (sr["netgen_mwh"] * 1000)
    sr.loc[sr["netgen_mwh"] <= 0, "wtr_grid_water_l_kwh"] = np.nan
    print(sr.round(3).to_string())
    poly = shp.merge(sr[["wtr_grid_water_l_kwh"]].reset_index(), on="SUBRGN", how="left")
    out = polygon_area_weighted_mean(poly, ["wtr_grid_water_l_kwh"], load_counties())
    write_interim(out, "eia923_water")
    register_source(
        "eia923_cooling_water", raw_files=[z], name=f"EIA-923 {YEAR} final: Schedule 8D cooling water + Page 1 net generation",
        url=URL, landing_page="https://www.eia.gov/electricity/data/eia923/",
        vintage=f"{YEAR} final (released 2026-09-14); plant->subregion from eGRID2023 PLNT23",
        license="Public domain (US Government work)",
        notes=(f"Per eGRID subregion: sum of 8D cooling water consumption (million gal -> L) / sum of net generation "
               f"of all plants (kWh), so wind/solar/hydro count as zero water. {n_spatial} plants not in eGRID2023 "
               f"mapped spatially with EIA-860 coordinates; {int(unmapped.sum())} plants ({unmapped_mwh:,.0f} MWh) "
               "unmapped and dropped. 8D covers thermoelectric plants >= 100 MW reporting cooling systems; "
               "smaller plants' water is not counted (understates intensity slightly). Vintage mismatch: 2025 "
               "generation/water vs 2023 subregion assignment."),
    )
    set_status("eia923_cooling_water", "OK", f"{len(sr)} subregions; {out['wtr_grid_water_l_kwh'].notna().sum()} counties.",
               ["wtr_grid_water_l_kwh"])


if __name__ == "__main__":
    main()
