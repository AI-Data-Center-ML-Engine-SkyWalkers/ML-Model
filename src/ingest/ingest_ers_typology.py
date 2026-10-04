"""USDA ERS County Typology Codes 2025 edition: persistent poverty flag."""
import pandas as pd

from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

URL = "https://www.ers.usda.gov/media/6174/ers-county-typology-codes-2025-edition.csv"
ATTR = "Persistent_Poverty_1721"


def main():
    p = download(URL, "ers_typology/ers-county-typology-codes-2025-edition.csv")
    df = pd.read_csv(p, encoding="latin1", dtype={"FIPStxt": str})
    df = df[df["Attribute"] == ATTR].copy()
    df["cob_persistent_poverty"] = pd.to_numeric(df["Value"], errors="coerce")
    codes = df.loc[~df["cob_persistent_poverty"].isin([0, 1]), ["FIPStxt", "cob_persistent_poverty"]]
    ct_regions = df["FIPStxt"].str.match(r"^091[1-9]0$") & (df["cob_persistent_poverty"] == 99)
    df = df[~ct_regions]
    df.loc[~df["cob_persistent_poverty"].isin([0, 1]), "cob_persistent_poverty"] = float("nan")
    out = table_join(df, "FIPStxt", {"cob_persistent_poverty": "max"}, source="ers_typology")
    write_interim(out, "ers_typology")
    register_source(
        "ers_typology", raw_files=[p], name="USDA ERS County Typology Codes, 2025 edition",
        url=URL, landing_page="https://www.ers.usda.gov/data-products/county-typology-codes",
        vintage="2025 edition (data as of April 2025)", license="Public domain (US Government work)",
        notes=(f"cob_persistent_poverty = attribute {ATTR} (poverty rate >= 20% in the 1990 and 2000 Censuses and "
               "the 2007-11 and 2017-21 ACS). Non-0/1 codes -> NaN: -1 (undocumented; new or tiny counties such as "
               "Broomfield CO, Loving TX, Miami-Dade FL) and 99 (CT planning regions, not available). For CT the "
               "file also has the 8 old counties (all 0); those go through the old-county -> planning-region "
               "crosswalk (each region takes the value of the old county covering most of it). "
               f"Code counts: {codes['cob_persistent_poverty'].value_counts().to_dict()}."),
    )
    set_status("ers_typology", "OK", f"{out['cob_persistent_poverty'].notna().sum()} counties with a 0/1 value; "
               f"{out['cob_persistent_poverty'].isna().sum()} NaN (ERS codes -1).", ["cob_persistent_poverty"])


if __name__ == "__main__":
    main()
