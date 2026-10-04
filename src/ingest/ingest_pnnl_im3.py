"""LABEL: PNNL IM3 Open Source Data Center Atlas - existing data centers per county."""
import geopandas as gpd
import pandas as pd
import pyogrio

from src.common.counties import load_counties
from src.common.geo import points_to_county
from src.common.io import download, register_source, set_status, write_interim

URL = ("https://raw.githubusercontent.com/IMMM-SFA/datacenter-atlas/main/data_center_database/"
       "im3_us_data_center_locations.gpkg")


def main():
    p = download(URL, "pnnl_im3/im3_us_data_center_locations.gpkg")
    layers = [l[0] for l in pyogrio.list_layers(p)]
    frames = {l: gpd.read_file(p, layer=l).to_crs(5070) for l in layers}
    # Buildings inside a mapped campus are part of that campus; count the campus once.
    n_dropped = 0
    if "campus" in frames and "building" in frames:
        b = frames["building"]
        inside = gpd.sjoin(b.set_geometry(b.representative_point()), frames["campus"][["geometry"]],
                           predicate="within", how="inner").index.unique()
        n_dropped = len(inside)
        frames["building"] = b.drop(index=inside)
    pts = pd.concat([f.set_geometry(f.representative_point())[["id", "geometry"]].assign(layer=l)
                     for l, f in frames.items()], ignore_index=True)
    pts = gpd.GeoDataFrame(pts, geometry="geometry", crs=5070)
    out = points_to_county(pts, load_counties(), "lbl_dc_existing_n")
    write_interim(out, "pnnl_im3")
    counts = {l: len(f) for l, f in frames.items()}
    register_source(
        "pnnl_im3_datacenter_atlas", raw_files=[p], name="IM3 Open Source Data Center Atlas (PNNL) - existing data centers",
        url=URL, landing_page="https://github.com/IMMM-SFA/datacenter-atlas ; https://data.msdlive.org/records/65g71-a4731",
        vintage="Atlas v1 (2025-06-06); GeoPackage from main branch", license="BSD-2-Clause (repo); data derived from OpenStreetMap (ODbL)",
        notes=(f"Layers {counts} after dropping {n_dropped} buildings that lie inside a campus polygon. Each feature's "
               "representative point is counted in its county. LABEL ONLY - never a model input."),
    )
    set_status("pnnl_im3_datacenter_atlas", "OK", f"{len(pts)} data center features counted.", ["lbl_dc_existing_n"])


if __name__ == "__main__":
    main()
