"""HIFLD transmission lines (HIFLD Next mirror): HV line length per county and distance to HV lines."""
import geopandas as gpd
import pandas as pd

from src.common.counties import centroids_albers, load_counties
from src.common.geo import line_length_km, nearest_distance_km
from src.common.hifld import fetch
from src.common.io import register_source, set_status, write_interim

SLUG = "transmission-lines-1"
EXCLUDE_STATUS = {"INACTIVE", "UNDER CONSTRUCTION"}


def main():
    p, info = fetch(SLUG)
    t = gpd.read_parquet(p)
    t["VOLTAGE"] = pd.to_numeric(t["VOLTAGE"], errors="coerce")
    n_unknown = int((t["VOLTAGE"].isna() | (t["VOLTAGE"] <= 0)).sum())
    t = t[(t["VOLTAGE"] > 0) & ~t["STATUS"].isin(EXCLUDE_STATUS)]
    cty = load_counties()
    cen = centroids_albers()
    out = cty[["fips"]].copy()
    for kv in (230, 345):
        lines = t[t["VOLTAGE"] >= kv]
        out = out.merge(line_length_km(lines, cty, f"pwr_hv{kv}_line_km"), on="fips")
        out = out.merge(nearest_distance_km(cen, lines, f"pwr_dist_hv{kv}_line_km", all_fips=cty[["fips"]]), on="fips")
    write_interim(out, "hifld_transmission")
    register_source(
        "hifld_transmission_lines", raw_files=[p], name="HIFLD Electric Power Transmission Lines (HIFLD Next mirror)",
        url=info["url"], landing_page="https://hifld.publicenvirodata.org (dataset hifld/transmission-lines-1)",
        vintage=f"{info['version']}; source issued/modified {info['source_dates']}",
        license="Public domain (US Government work, ORNL/DOE via HIFLD Open; retired 2025)",
        notes=(f"HIFLD Open retired in 2025; using the HIFLD Next GeoParquet copy. {n_unknown} lines with VOLTAGE "
               "<= 0 or missing (-999999 = unknown) excluded; INACTIVE and UNDER CONSTRUCTION excluded. Lengths are "
               "clipped to counties in EPSG:5070. Distances from the 2020 population centroid."),
    )
    set_status("hifld_transmission_lines", "OK",
               f"{(t['VOLTAGE'] >= 230).sum()} lines >= 230 kV, {(t['VOLTAGE'] >= 345).sum()} >= 345 kV; "
               f"{n_unknown} unknown-voltage lines excluded.",
               ["pwr_hv230_line_km", "pwr_hv345_line_km", "pwr_dist_hv230_line_km", "pwr_dist_hv345_line_km"])


if __name__ == "__main__":
    main()
