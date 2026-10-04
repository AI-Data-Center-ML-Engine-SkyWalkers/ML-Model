"""DOE/NETL IRA energy community layers (2024): 1 if more than 50% of the county area qualifies."""
import glob

import geopandas as gpd
import pandas as pd

from src.common.counties import load_counties
from src.common.geo import polygon_coverage_pct
from src.common.io import download, register_source, set_status, unzip, write_interim

BASE = "https://edx.netl.doe.gov/storage/f/edx/2024/06/"
MSA_URL = BASE + "2024-06-07T01:36:36.743668/13454403-ef6b-479b-b720-d5e3eaefbb91/MSA_NMSA_EC_FFE_v2024_1.zip"
COAL_URL = BASE + "2024-06-07T01:34:50.394202/4006c9da-f99c-4731-97b2-633cc1578994/Coal_Closures_EnergyComm_v2024_1.zip"
THRESHOLD_PCT = 50.0


def main():
    p1 = download(MSA_URL, "netl_energy_comm/MSA_NMSA_EC_FFE_v2024_1.zip", timeout=600)
    p2 = download(COAL_URL, "netl_energy_comm/Coal_Closures_EnergyComm_v2024_1.zip", timeout=600)
    msa = gpd.read_file(glob.glob(str(unzip(p1)) + "/**/MSA_NMSA_EC_v2024_1.shp", recursive=True)[0])
    msa = msa[msa["ec_qual_st"] == "Yes"]
    coal = gpd.read_file(glob.glob(str(unzip(p2)) + "/**/CoalClosures_EnergyComm_v2024_1.shp", recursive=True)[0])
    both = pd.concat([msa[["geometry"]].to_crs(5070), coal[["geometry"]].to_crs(5070)], ignore_index=True)
    out = polygon_coverage_pct(gpd.GeoDataFrame(both, crs=5070), load_counties(), "cob_energy_community_pct")
    out["cob_energy_community"] = (out["cob_energy_community_pct"] > THRESHOLD_PCT).astype(float)
    write_interim(out, "netl_energy_comm")
    register_source(
        "netl_energy_community", raw_files=[p1, p2], name="DOE/NETL IRA Energy Community Data Layers (v2024.1)",
        url=f"{MSA_URL} ; {COAL_URL}", landing_page="https://edx.netl.doe.gov/dataset/ira-energy-community-data-layers",
        vintage="2024.1 (published 2024-06-07)", license="CC BY (EDX resource license); DOI 10.18141/1967447",
        notes=(f"Union of MSA/non-MSA counties that are energy communities ({len(msa)} county pieces) and coal-closure "
               f"census tracts plus adjoining tracts ({len(coal)}). cob_energy_community = 1 if the union covers > "
               f"{THRESHOLD_PCT:.0f}% of the county area (cob_energy_community_pct kept for transparency). "
               "Not yet reflecting IRS Notice 2025-31 (2025 lists, published only as tables) - latest NETL spatial "
               "release is 2024. The brownfield category is not mapped by NETL and is excluded."),
    )
    set_status("netl_energy_community", "OK",
               f"{int(out['cob_energy_community'].sum())} counties > {THRESHOLD_PCT:.0f}% energy community (2024 layers).",
               ["cob_energy_community", "cob_energy_community_pct"])


if __name__ == "__main__":
    main()
