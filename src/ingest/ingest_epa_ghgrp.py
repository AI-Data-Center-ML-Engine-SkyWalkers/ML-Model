"""EPA GHGRP: Subpart C combustion facilities in low-temperature-heat industries (heat-reuse anchors)."""
import zipfile

import geopandas as gpd
import pandas as pd

from src.common.counties import load_counties
from src.common.geo import points_to_county
from src.common.io import RAW, download, register_source, set_status, write_interim

URL = "https://www.epa.gov/system/files/other-files/2024-10/2023_data_summary_spreadsheets.zip"
YEAR = 2023
NAICS_PREFIXES = ("311", "312", "322", "325", "1114")


def main():
    p = download(URL, "epa_ghgrp/2023_data_summary_spreadsheets.zip")
    member = f"ghgp_data_{YEAR}.xlsx"
    xlsx = RAW / "epa_ghgrp" / member
    if not xlsx.exists():
        with zipfile.ZipFile(p) as z:
            z.extract(member, xlsx.parent)
    d = pd.read_excel(xlsx, "Direct Point Emitters", header=3)
    d["naics"] = pd.to_numeric(d["Primary NAICS Code"], errors="coerce").astype("Int64").astype(str)
    d["subparts"] = d["Industry Type (subparts)"].fillna("").str.split(",")
    has_c = d["subparts"].apply(lambda s: "C" in [x.strip() for x in s])
    sel = d[d["naics"].str.startswith(NAICS_PREFIXES) & has_c].copy()
    sel["tco2"] = pd.to_numeric(sel["Stationary Combustion"], errors="coerce")
    for c in ("Latitude", "Longitude"):
        sel[c] = pd.to_numeric(sel[c], errors="coerce")
    no_xy = sel["Latitude"].isna() | sel["Longitude"].isna()
    pts = gpd.GeoDataFrame(sel[~no_xy], geometry=gpd.points_from_xy(sel.loc[~no_xy, "Longitude"],
                                                                      sel.loc[~no_xy, "Latitude"]), crs="EPSG:4326")
    cty = load_counties()
    out = points_to_county(pts, cty, "cob_ghgrp_combustion_facilities_n")
    out = out.merge(points_to_county(pts, cty, "cob_ghgrp_combustion_tco2", value_col="tco2", agg="sum"), on="fips")
    write_interim(out, "epa_ghgrp")
    by = sel["naics"].str[:3].value_counts().to_dict()
    register_source(
        "epa_ghgrp", raw_files=[p], name="EPA Greenhouse Gas Reporting Program - data summary spreadsheets",
        url=URL, landing_page="https://www.epa.gov/ghgreporting/data-sets", vintage=f"Reporting year {YEAR} (data as of 2024-08-16)",
        license="Public domain (US Government work)",
        notes=(f"Direct Point Emitters sheet, facilities whose subparts include C and whose primary NAICS starts with "
               f"{NAICS_PREFIXES} ({len(sel)} facilities; by 3-digit NAICS {by}; {int(no_xy.sum())} without coordinates). "
               "tCO2 = the 'Stationary Combustion' column (metric tons CO2e, AR4 GWPs; dominated by CO2). "
               "RY2023 is the latest EPA release: RY2024 data was not published by EPA (an FOIA copy exists from "
               "Environmental Integrity Project but is not an official release)."),
    )
    set_status("epa_ghgrp", "OK", f"RY{YEAR}: {len(pts)} Subpart C facilities in NAICS {NAICS_PREFIXES}.",
               ["cob_ghgrp_combustion_facilities_n", "cob_ghgrp_combustion_tco2"])


if __name__ == "__main__":
    main()
