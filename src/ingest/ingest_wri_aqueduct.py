"""WRI Aqueduct 4.0: baseline and 2050 BAU baseline water stress scores, area-weighted onto counties."""
import numpy as np
import pyogrio

from src.common.counties import load_counties
from src.common.geo import polygon_area_weighted_mean
from src.common.io import download, register_source, set_status, unzip, write_interim

URL = "https://files.wri.org/aqueduct/aqueduct-4-0-water-risk-data.zip"
CONUS_BBOX = (-125.5, 24.0, -66.5, 49.6)


def main():
    z = download(URL, "wri_aqueduct/aqueduct-4-0-water-risk-data.zip", timeout=1800)
    gdb = next(unzip(z).rglob("*.gdb"))
    cty = load_counties()

    base = pyogrio.read_dataframe(gdb, layer="baseline_annual", bbox=CONUS_BBOX,
                                  columns=["pfaf_id", "gid_0", "bws_score"])
    base = base[base["gid_0"] == "USA"]
    base["bws_score"] = base["bws_score"].where(base["bws_score"] >= 0, np.nan)
    a = polygon_area_weighted_mean(base.rename(columns={"bws_score": "wtr_bws_score"}), ["wtr_bws_score"], cty)

    fut = pyogrio.read_dataframe(gdb, layer="future_annual", bbox=CONUS_BBOX, columns=["pfaf_id", "bau50_ws_x_s"])
    fut["bau50_ws_x_s"] = fut["bau50_ws_x_s"].where(fut["bau50_ws_x_s"] >= 0, np.nan)
    b = polygon_area_weighted_mean(fut.rename(columns={"bau50_ws_x_s": "wtr_bws_2050_score"}),
                                   ["wtr_bws_2050_score"], cty)
    out = a.merge(b, on="fips")
    write_interim(out, "wri_aqueduct")
    register_source(
        "wri_aqueduct40", raw_files=[z], name="WRI Aqueduct 4.0 water risk data (baseline annual + future annual)",
        url=URL, landing_page="https://www.wri.org/data/aqueduct-global-maps-40-data",
        vintage="Aqueduct 4.0, release Y2023M07D05 (baseline 1979-2019; future 2050)",
        license="CC BY 4.0 (World Resources Institute)",
        notes=("wtr_bws_score = baseline annual bws_score (0-5) from the 'baseline_annual' layer (HydroBASINS level 6 "
               "x GADM admin-1 units). wtr_bws_2050_score = bau50_ws_x_s from 'future_annual' (business-as-usual = "
               "SSP3-7.0, 2050). Negative sentinel scores -> NaN. Area-weighted overlay onto counties in EPSG:5070."),
    )
    set_status("wri_aqueduct40", "OK",
               f"baseline non-null {out['wtr_bws_score'].notna().sum()}, 2050 non-null {out['wtr_bws_2050_score'].notna().sum()}",
               ["wtr_bws_score", "wtr_bws_2050_score"])


if __name__ == "__main__":
    main()
