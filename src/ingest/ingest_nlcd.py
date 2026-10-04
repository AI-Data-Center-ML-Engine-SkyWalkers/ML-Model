"""USGS Annual NLCD Collection 1.1 land cover 2024 (30 m): percent of county area by class group (exactextract)."""
from src.common.counties import load_counties
from src.common.geo import raster_class_pct
from src.common.io import download, register_source, set_status, unzip, write_interim

URL = "https://www.mrlc.gov/downloads/sciweb1/shared/mrlc/data-bundles/Annual_NLCD_LndCov_2024_CU_C1V1.zip"
GROUPS = {
    "lnd_pct_developed": [21, 22, 23, 24],
    "lnd_pct_buildable": [31, 52, 71, 81],
    "lnd_pct_wetland": [90, 95],
    "lnd_pct_cropland": [82],
    "lnd_pct_forest": [41, 42, 43],
}


def main():
    p = download(URL, "nlcd/Annual_NLCD_LndCov_2024_CU_C1V1.zip", timeout=3600)
    tif = next(unzip(p).rglob("*.tif"))
    out = raster_class_pct(tif, load_counties(), GROUPS)
    write_interim(out, "nlcd")
    register_source(
        "usgs_annual_nlcd", raw_files=[p], name="USGS Annual NLCD CONUS Collection 1.1 Land Cover 2024 (30 m)", url=URL,
        landing_page="https://www.mrlc.gov/data ; https://doi.org/10.5066/P94UXNTS",
        vintage="Land cover year 2024, Collection 1 Version 1 (C1.1)", license="Public domain (US Government work)",
        notes=(f"Class groups {GROUPS}. exactextract 'unique'+'frac' on county polygons reprojected to the raster CRS; "
               "denominator = all valid cells in the county including open water (11), so groups are % of total "
               "county area. Collection 1.2 (adds 2025) now exists on mrlc.gov; 1.1/2024 used as specified."),
    )
    set_status("usgs_annual_nlcd", "OK", "Land cover class shares for all counties.", list(GROUPS))


if __name__ == "__main__":
    main()
