"""EIA-860 (final 2025): operating generator capacity and clean capacity per county (points join)."""
import geopandas as gpd
import pandas as pd

from src.common.counties import load_counties
from src.common.geo import points_to_county
from src.common.io import INTERIM, download, register_source, set_status, unzip, write_interim

YEAR = 2025
URL = f"https://www.eia.gov/electricity/data/eia860/xls/eia860{YEAR}.zip"
OPERATING = ["OP", "SB"]
CLEAN_TECH = {
    "Nuclear", "Conventional Hydroelectric", "Onshore Wind Turbine", "Offshore Wind Turbine",
    "Solar Photovoltaic", "Solar Thermal with Energy Storage", "Solar Thermal without Energy Storage",
    "Geothermal",
}


def load_plants(folder) -> pd.DataFrame:
    p = pd.read_excel(folder / f"2___Plant_Y{YEAR}.xlsx", header=1)
    p = p[pd.to_numeric(p["Plant Code"], errors="coerce").notna()]
    p["Plant Code"] = p["Plant Code"].astype(int)
    for c in ("Latitude", "Longitude"):
        p[c] = pd.to_numeric(p[c], errors="coerce")
    return p[["Plant Code", "Plant Name", "State", "County", "Latitude", "Longitude",
              "Balancing Authority Code"]]


def main():
    z = download(URL, f"eia860/eia860{YEAR}.zip", timeout=900)
    folder = unzip(z)
    plants = load_plants(folder)
    plants.to_parquet(INTERIM / "_eia860_plants.parquet", index=False)
    g = pd.read_excel(folder / f"3_1_Generator_Y{YEAR}.xlsx", sheet_name="Operable", header=1)
    g = g[pd.to_numeric(g["Plant Code"], errors="coerce").notna()]
    g["Plant Code"] = g["Plant Code"].astype(int)
    g = g[g["Status"].isin(OPERATING)]
    g["mw"] = pd.to_numeric(g["Nameplate Capacity (MW)"], errors="coerce")
    g["clean_mw"] = g["mw"].where(g["Technology"].isin(CLEAN_TECH), 0.0)
    plant_mw = g.groupby("Plant Code")[["mw", "clean_mw"]].sum().reset_index()
    pm = plant_mw.merge(plants, on="Plant Code", how="left")
    no_xy = pm["Latitude"].isna() | pm["Longitude"].isna()
    pts = gpd.GeoDataFrame(pm[~no_xy], geometry=gpd.points_from_xy(pm.loc[~no_xy, "Longitude"],
                                                                     pm.loc[~no_xy, "Latitude"]), crs="EPSG:4326")
    cty = load_counties()
    a = points_to_county(pts, cty, "pwr_gen_capacity_mw", value_col="mw", agg="sum")
    b = points_to_county(pts, cty, "crb_clean_gen_mw", value_col="clean_mw", agg="sum")
    out = a.merge(b, on="fips")
    write_interim(out, "eia860")
    conus_mw = out["pwr_gen_capacity_mw"].sum()
    register_source(
        "eia860", raw_files=[z], name=f"EIA-860 Annual Electric Generator Report {YEAR} (final)", url=URL,
        landing_page="https://www.eia.gov/electricity/data/eia860/", vintage=f"{YEAR} final (released 2026-09-10)",
        license="Public domain (US Government work)",
        notes=(f"Operating = status {OPERATING} (operating + standby). Plant-level nameplate MW joined to counties "
               "spatially using plant lat/lon (no name matching). Clean = nuclear, conventional hydro, onshore/"
               "offshore wind, solar PV/thermal, geothermal; pumped storage and batteries excluded (storage). "
               f"{int(no_xy.sum())} plants without coordinates dropped. CONUS total {conus_mw:,.0f} MW."),
    )
    set_status("eia860", "OK", f"{len(pts)} plants joined; CONUS operating capacity {conus_mw:,.0f} MW.",
               ["pwr_gen_capacity_mw", "crb_clean_gen_mw"])


if __name__ == "__main__":
    main()
