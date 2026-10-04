"""Census TIGER AIANNH: percent of county area in American Indian reservations / off-reservation trust land."""
import geopandas as gpd

from src.common.counties import load_counties
from src.common.geo import polygon_coverage_pct
from src.common.io import download, register_source, set_status, unzip, write_interim

URL = "https://www2.census.gov/geo/tiger/TIGER2025/AIANNH/tl_2025_us_aiannh.zip"
# Legal land areas only: reservations (federal and state), off-reservation trust land, joint-use areas.
# Statistical areas (OTSA G2140, SDTSA G2150, TDSA G2160, ANVSA G2130) are excluded.
LEGAL_MTFCC = {"G2101", "G2102", "G2170"}


def main():
    p = download(URL, "census_aiannh/tl_2025_us_aiannh.zip", timeout=600)
    g = gpd.read_file(next(unzip(p).rglob("*.shp")))
    sel = g[g["MTFCC"].isin(LEGAL_MTFCC)]
    cty = load_counties()
    out = polygon_coverage_pct(sel, cty, "prm_pct_tribal")
    otsa = polygon_coverage_pct(g[g["MTFCC"] == "G2140"], cty, "prm_pct_ok_tribal_stat_area")
    out = out.merge(otsa, on="fips")
    write_interim(out, "census_aiannh")
    register_source(
        "census_aiannh", raw_files=[p], name="Census TIGER/Line 2025 American Indian/Alaska Native/Native Hawaiian Areas",
        url=URL, landing_page="https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html",
        vintage="TIGER/Line 2025", license="Public domain (US Government work)",
        notes=(f"prm_pct_tribal = % of county area (cb_2025 500k boundary, incl. inland water) covered by the dissolved "
               f"union of MTFCC {sorted(LEGAL_MTFCC)} ({len(sel)} features: federal + state reservations, off-reservation "
               "trust land, joint-use areas). Statistical areas excluded. AMBIGUOUS: Oklahoma Tribal Statistical Areas "
               "(former reservations; post-McGirt several are reservations in law for some purposes) cover much of "
               "eastern Oklahoma - reported separately as prm_pct_ok_tribal_stat_area, not folded into prm_pct_tribal."),
    )
    set_status("census_aiannh", "OK", f"{(out['prm_pct_tribal'] > 0).sum()} counties with some tribal land.",
               ["prm_pct_tribal", "prm_pct_ok_tribal_stat_area"])


if __name__ == "__main__":
    main()
