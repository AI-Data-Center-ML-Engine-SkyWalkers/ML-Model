"""USGS PAD-US 4.1 (source.coop GeoParquet mirror): percent of county area in GAP status 1-2 protected land."""
import geopandas as gpd
import shapely

from src.common.counties import load_counties
from src.common.geo import polygon_coverage_pct
from src.common.io import download, register_source, set_status, write_interim

URL = "https://data.source.coop/cboettig/padus/padus-4-1/combined.parquet"
GAP = ["1", "2"]


def main():
    p = download(URL, "padus/padus-4-1_combined.parquet", timeout=3600)
    cty = load_counties()
    xmin, ymin, xmax, ymax = cty.to_crs(4326).total_bounds
    g = gpd.read_parquet(p, columns=["GAP_Sts", "Category", "SHAPE"],
                         filters=[("GAP_Sts", "in", GAP)], bbox=(xmin, ymin, xmax, ymax))
    n_all = len(g)
    g = g[g["Category"] != "Marine"]
    g = g.to_crs(5070)
    g["SHAPE"] = shapely.make_valid(g.geometry.values)
    out = polygon_coverage_pct(g[["SHAPE"]].rename_geometry("geometry"), cty, "lnd_pct_protected")
    write_interim(out, "padus")
    register_source(
        "usgs_padus", raw_files=[p], name="USGS Protected Areas Database of the US (PAD-US) 4.1 - Combined layer",
        url=URL, landing_page="https://source.coop/cboettig/padus ; https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-download",
        vintage="PAD-US 4.1", license="Public domain (USGS); source.coop mirror by C. Boettiger",
        notes=(f"Combined layer (Fee, Easement, Designation, Proclamation) filtered to GAP_Sts in {GAP} within the CONUS "
               f"bbox ({n_all} features), Marine category dropped ({len(g)} kept). Overlaps dissolved per county before "
               "measuring, so area is not double counted. Denominator = cb_2025 500k county area incl. inland water. "
               "CAVEAT: some Designation polygons are proclamation boundaries rather than protected land, e.g. San Juan "
               "Islands National Monument (GAP 2, 432,005 acres) covers all of San Juan County WA, which therefore "
               "shows 100%. Kept as published; no ad hoc filter applied."),
    )
    set_status("usgs_padus", "OK", f"{len(g)} GAP 1-2 features overlaid.", ["lnd_pct_protected"])


if __name__ == "__main__":
    main()
