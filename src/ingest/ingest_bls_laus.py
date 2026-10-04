"""BLS LAUS county annual average unemployment rate (latest full calendar year)."""
import pandas as pd

from src.common.geo import table_join
from src.common.io import CONTACT_UA, download, register_source, set_status, write_interim

# 2025 annual averages are an 11-month average (no October 2025 data due to the federal
# shutdown), so 2024 is the latest full year.
YEAR = 2024
URL = f"https://www.bls.gov/lau/laucnty{str(YEAR)[2:]}.xlsx"


def main():
    p = download(URL, f"bls_laus/laucnty{str(YEAR)[2:]}.xlsx", user_agent=CONTACT_UA)
    raw = pd.read_excel(p, header=None, dtype=str)
    hdr = raw.index[raw.iloc[:, 0].astype(str).str.contains("LAUS Code", na=False)][0]
    df = raw.iloc[hdr + 1:].copy()
    df.columns = ["laus", "st", "co", "name", "year", "lf", "emp", "unemp", "rate"][: df.shape[1]]
    df = df[df["st"].notna() & df["co"].notna() & df["st"].str.strip().str.isdigit()]
    df["fips"] = df["st"].str.strip().str.zfill(2) + df["co"].str.strip().str.zfill(3)
    df["cob_unemp_rate"] = pd.to_numeric(df["rate"], errors="coerce")
    out = table_join(df, "fips", {"cob_unemp_rate": "mean"}, source="bls_laus")
    write_interim(out, "bls_laus")
    register_source(
        "bls_laus", raw_files=[p], name="BLS Local Area Unemployment Statistics, county annual averages",
        url=URL, vintage=str(YEAR), license="Public domain (US Government work)",
        notes="2025 file exists but is an 11-month average (October 2025 not collected), so 2024 is used. "
              "BLS requires a User-Agent with a contact email (env CONTACT_EMAIL).",
    )
    set_status("bls_laus", "OK", f"{len(out)} counties, {YEAR} annual average.", ["cob_unemp_rate"])


if __name__ == "__main__":
    main()
