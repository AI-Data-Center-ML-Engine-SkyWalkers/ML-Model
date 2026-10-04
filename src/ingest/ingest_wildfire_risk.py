"""USDA Forest Service Wildfire Risk to Communities, county risk to homes."""
import pandas as pd

from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

URL = "https://wildfirerisk.org/wp-content/uploads/2026/04/wrc_download_20260415.xlsx"


def main():
    p = download(URL, "wildfire_risk/wrc_download_20260415.xlsx")
    df = pd.read_excel(p, sheet_name="Counties", dtype={"GEOID": str})
    df["haz_wildfire_risk_to_homes"] = 100 * pd.to_numeric(df["RISK_NATIONAL_RANK"], errors="coerce")
    out = table_join(df, "GEOID", {"haz_wildfire_risk_to_homes": "mean"}, source="wildfire_risk")
    write_interim(out, "wildfire_risk")
    register_source(
        "wildfire_risk", raw_files=[p], name="Wildfire Risk to Communities - county download",
        url=URL, landing_page="https://wildfirerisk.org/download/", vintage="2026-04-15 release",
        license="Public domain (USDA Forest Service)",
        notes="'Risk to homes' = RISK_NATIONAL_RANK, the national percentile of the county's mean Risk to "
              "Potential Structures (RPS); stored as 0-100.",
    )
    set_status("wildfire_risk", "OK", f"{len(out)} counties.", ["haz_wildfire_risk_to_homes"])


if __name__ == "__main__":
    main()
