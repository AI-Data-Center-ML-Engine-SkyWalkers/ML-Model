"""NPS National Register of Historic Places: listed properties per county."""
import glob

import geopandas as gpd
import pandas as pd
import pyogrio

from src.common.counties import load_counties
from src.common.geo import points_to_county
from src.common.io import download, register_source, set_status, unzip, write_interim

URL = "https://irma.nps.gov/DataStore/DownloadFile/762962?Reference=2319397"
TYPES = ("bldg", "site", "dist", "obj", "stru")


def main():
    p = download(URL, "nps_nrhp/NRIS_CR_Standards_Public.gdb.zip", timeout=900)
    gdb = glob.glob(str(unzip(p)) + "/**/*.gdb", recursive=True)[0]
    main_tbl = pyogrio.read_dataframe(gdb, layer="NR_Main", columns=["Property_ID", "Status"], read_geometry=False)
    listed = set(main_tbl.loc[main_tbl["Status"].str.upper() == "LISTED", "Property_ID"].astype(str))
    frames = []
    for t in TYPES:
        for kind in ("pt", "py"):
            g = gpd.read_file(gdb, layer=f"cr{t}_{kind}", columns=["NR_PROPERTYID"]).to_crs(5070)
            g["geometry"] = g.representative_point() if kind == "py" else g.geometry
            g["kind"] = kind
            frames.append(g)
    allg = pd.concat(frames, ignore_index=True)
    allg = allg[allg.geometry.notna() & ~allg.geometry.is_empty]
    allg["NR_PROPERTYID"] = allg["NR_PROPERTYID"].astype(str)
    # One location per property: prefer the point feature, else a polygon's representative point.
    allg = allg.sort_values("kind").drop_duplicates("NR_PROPERTYID")
    n_with_geom = len(allg)
    allg = allg[allg["NR_PROPERTYID"].isin(listed)]
    pts = gpd.GeoDataFrame(allg, geometry="geometry", crs=5070)
    out = points_to_county(pts, load_counties(), "prm_nrhp_n")
    write_interim(out, "nps_nrhp")
    register_source(
        "nps_nrhp", raw_files=[p], name="National Register of Historic Places - NRIS_CR_Standards_Public geodatabase",
        url=URL, landing_page="https://irma.nps.gov/DataStore/Reference/Profile/2319397",
        vintage="August 2026 release (NRIS extract March 2026)", license="Public domain (US Government work)",
        notes=(f"{n_with_geom} unique properties with geometry across building/site/district/object/structure layers; "
               f"{len(pts)} with NR_Main Status = Listed (removed properties excluded). Point preferred, else polygon "
               "representative point. Restricted/sensitive sites are excluded by NPS, so counts are a lower bound."),
    )
    set_status("nps_nrhp", "OK", f"{len(pts)} listed NRHP properties located.", ["prm_nrhp_n"])


if __name__ == "__main__":
    main()
