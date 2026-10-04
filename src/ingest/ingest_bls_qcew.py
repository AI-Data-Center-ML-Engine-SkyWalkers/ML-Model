"""BLS QCEW annual averages, NAICS 518210 (computing infrastructure / data processing / hosting), by county."""
import pandas as pd

from src.common.counties import load_counties
from src.common.geo import table_join
from src.common.io import CONTACT_UA, download, register_source, set_status, write_interim

YEAR = 2025
NAICS = "518210"
URL = f"https://data.bls.gov/cew/data/api/{YEAR}/a/industry/{NAICS}.csv"
FEATURES = ["cob_qcew_dc_emp", "cob_qcew_dc_emp_suppressed"]


def main():
    p = download(URL, f"bls_qcew/{YEAR}_a_{NAICS}.csv", user_agent=CONTACT_UA)
    q = pd.read_csv(p, dtype=str)
    q = q[(q["agglvl_code"] == "78") & (q["size_code"] == "0")]  # county x 6-digit NAICS x ownership
    q["emp"] = pd.to_numeric(q["annual_avg_emplvl"], errors="coerce")
    q["supp"] = q["disclosure_code"].fillna("").str.strip().eq("N")
    g = q.groupby("area_fips").agg(emp=("emp", "sum"), supp=("supp", "max")).reset_index()
    g["cob_qcew_dc_emp"] = g["emp"].where(~g["supp"])
    g["cob_qcew_dc_emp_suppressed"] = g["supp"].astype(float)
    out = table_join(g[["area_fips", *FEATURES]], "area_fips",
                     {"cob_qcew_dc_emp": "sum", "cob_qcew_dc_emp_suppressed": "max"}, source="bls_qcew")
    out = load_counties()[["fips"]].merge(out, on="fips", how="left")
    absent = out["cob_qcew_dc_emp_suppressed"].isna()
    out.loc[absent, FEATURES] = 0.0  # QCEW lists every county with covered establishments; absent = none
    write_interim(out, "bls_qcew")
    register_source(
        "bls_qcew", raw_files=[p], name=f"BLS QCEW annual averages, NAICS {NAICS}, county level (open data API)",
        url=URL, landing_page="https://www.bls.gov/cew/downloadable-data-files.htm",
        vintage=f"{YEAR} annual averages", license="Public domain (US BLS)",
        notes=("Sum of annual average employment across ownership codes (private + government) for agglvl 78. "
               "If any ownership row is suppressed (disclosure_code N) the county value is NaN and "
               "cob_qcew_dc_emp_suppressed = 1. Counties with no row have no covered establishments: 0 / flag 0. "
               "NAICS 518210 = Computing Infrastructure Providers, Data Processing, Web Hosting (NAICS 2022)."),
    )
    n_supp = int((out["cob_qcew_dc_emp_suppressed"] == 1).sum())
    n_pos = int((out["cob_qcew_dc_emp"] > 0).sum())
    set_status("bls_qcew", "OK", f"{YEAR}: {n_pos} counties with disclosed employment > 0, {n_supp} suppressed "
               f"(NaN + flag), {int(absent.sum())} with no establishments (0).", FEATURES)


if __name__ == "__main__":
    main()
