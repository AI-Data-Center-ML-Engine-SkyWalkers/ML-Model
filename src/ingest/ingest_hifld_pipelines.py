"""EIA natural gas interstate/intrastate pipelines (HIFLD Next mirror): pipeline km per county."""
import geopandas as gpd

from src.common.counties import load_counties
from src.common.geo import line_length_km
from src.common.hifld import fetch
from src.common.io import register_source, set_status, write_interim

SLUG = "natural-gas-interstate-and-intrastate-pipelines"
KEEP = {"Interstate", "Intrastate"}


def main():
    p, info = fetch(SLUG)
    g = gpd.read_parquet(p)
    g = g[g["TYPEPIPE"].isin(KEEP)]
    out = line_length_km(g, load_counties(), "pwr_gas_pipeline_km")
    write_interim(out, "hifld_pipelines")
    register_source(
        "eia_gas_pipelines", raw_files=[p], name="Natural Gas Interstate and Intrastate Pipelines (EIA; HIFLD Next mirror)",
        url=info["url"], landing_page="https://hifld.publicenvirodata.org (dataset hifld/" + SLUG + ")",
        vintage=f"{info['version']}; source issued/modified {info['source_dates']}",
        license="Public domain (US Government work, EIA)",
        notes="Interstate + intrastate lines (gathering lines excluded). Length clipped to counties in EPSG:5070.",
    )
    set_status("eia_gas_pipelines", "OK", f"{len(g)} pipeline segments; {out['pwr_gas_pipeline_km'].sum():,.0f} km in CONUS.",
               ["pwr_gas_pipeline_km"])


if __name__ == "__main__":
    main()
