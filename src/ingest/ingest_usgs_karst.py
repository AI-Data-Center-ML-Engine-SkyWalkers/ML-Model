"""USGS Karst in the United States (Open-File Report 2014-1156): share of county area on karst-prone rock."""
import pandas as pd
import pyogrio

from src.common.counties import load_counties
from src.common.geo import polygon_coverage_pct
from src.common.io import download, register_source, set_status, unzip, write_interim

URL = "https://pubs.usgs.gov/of/2014/1156/downloads/USKarstMap.zip"
LANDING = "https://pubs.usgs.gov/of/2014/1156/"
LAYERS = ["Carbonates48", "Evaporites48", "SandstoneKarst48"]  # solution karst; volcanic/piping pseudokarst excluded
FEATURES = ["haz_karst_pct", "haz_karst_exposed_pct"]


def main():
    z = download(URL, "usgs_karst/USKarstMap.zip", timeout=1800)
    folder = unzip(z) / "Shapefiles" / "Continguous48"
    karst = pd.concat([pyogrio.read_dataframe(folder / f"{n}.shp", columns=["Exposure"]) for n in LAYERS],
                      ignore_index=True)
    counties = load_counties()[["fips", "geometry"]]
    out = polygon_coverage_pct(karst, counties, "haz_karst_pct")
    exposed = polygon_coverage_pct(karst[karst["Exposure"].str.strip() == "E"], counties, "haz_karst_exposed_pct")
    out = out.merge(exposed, on="fips")
    write_interim(out, "usgs_karst")
    register_source(
        "usgs_karst", raw_files=[z], name="Karst in the United States: a digital map compilation and database "
        "(Weary & Doctor, USGS OFR 2014-1156)", url=URL, landing_page=LANDING, vintage="2014 (v1.0)",
        license="Public domain (USGS)",
        notes=(f"Layers {LAYERS} (carbonate, evaporite and quartz-sandstone solution karst) unioned per county; "
               "volcanic and piping pseudokarst and the buried evaporite basins layer are excluded. haz_karst_pct "
               "includes rock buried under insoluble cover (Exposure B1-B3); haz_karst_exposed_pct is Exposure = E "
               "only (at or near the land surface). Percent of the county polygon area (EPSG:5070)."),
    )
    set_status("usgs_karst", "OK", f"{int((out['haz_karst_pct'] > 0).sum())} counties with any karst; "
               f"{int((out['haz_karst_exposed_pct'] > 0).sum())} with exposed karst.", FEATURES)


if __name__ == "__main__":
    main()
