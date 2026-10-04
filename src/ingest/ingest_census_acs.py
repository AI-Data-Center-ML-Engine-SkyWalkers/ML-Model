"""ACS 5-year 2023: population, poverty, median household income, house heating fuel.

Uses the Census API when CENSUS_API_KEY is set; otherwise the identical published estimates
from the ACS table-based Summary File on www2.census.gov (no key needed).
"""
import numpy as np
import pandas as pd
import requests

from src.common.geo import table_join
from src.common.io import RAW, download, env_key, register_source, set_status, write_interim

YEAR = 2023
SF_URL = ("https://www2.census.gov/programs-surveys/acs/summary_file/{y}/table-based-SF/data/5YRData/"
          "acsdt5y{y}-{t}.dat")
API_URL = f"https://api.census.gov/data/{YEAR}/acs/acs5"

# B25040: 002 utility gas, 003 bottled/tank/LP gas, 005 fuel oil/kerosene
VARS = {
    "b01003": ["B01003_E001"],
    "b17001": ["B17001_E001", "B17001_E002"],
    "b19013": ["B19013_E001"],
    "b25040": ["B25040_E001", "B25040_E002", "B25040_E003", "B25040_E005"],
}


def _from_summary_file() -> tuple[pd.DataFrame, list]:
    frames, files = [], []
    for t, cols in VARS.items():
        p = download(SF_URL.format(y=YEAR, t=t), f"acs/acsdt5y{YEAR}-{t}.dat", timeout=900)
        files.append(p)
        d = pd.read_csv(p, sep="|", dtype=str, usecols=["GEO_ID", *cols])
        d = d[d["GEO_ID"].str.startswith("0500000US")]
        d["fips"] = d["GEO_ID"].str[-5:]
        frames.append(d.drop(columns="GEO_ID").set_index("fips"))
    return pd.concat(frames, axis=1).reset_index(), files


def _from_api(key: str) -> tuple[pd.DataFrame, list]:
    api_vars = [v.replace("_E", "_") + "E" for cols in VARS.values() for v in cols]
    print(f"[download] {API_URL} (Census API)")
    r = requests.get(API_URL, params={"get": ",".join(api_vars), "for": "county:*", "key": key}, timeout=120)
    r.raise_for_status()
    rows = r.json()
    d = pd.DataFrame(rows[1:], columns=rows[0])
    d["fips"] = d["state"] + d["county"]
    d = d.rename(columns={v.replace("_E", "_") + "E": v for cols in VARS.values() for v in cols})
    out = RAW / "acs" / f"acs5_{YEAR}_api.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(out, index=False)
    return d, [out]


def main():
    key = env_key("CENSUS_API_KEY")
    method = "Census API" if key else "ACS table-based Summary File (bulk download)"
    d, files = _from_api(key) if key else _from_summary_file()
    for c in [v for cols in VARS.values() for v in cols]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
        d.loc[d[c] < 0, c] = np.nan  # Census annotation sentinels (-666666666 etc.)
    d["meta_pop_2023"] = d["B01003_E001"]
    d["cob_poverty_pct"] = 100 * d["B17001_E002"] / d["B17001_E001"]
    d["cob_median_hh_income"] = d["B19013_E001"]
    d["cob_pct_fossil_heat"] = 100 * (d["B25040_E002"] + d["B25040_E003"] + d["B25040_E005"]) / d["B25040_E001"]
    out = table_join(d, "fips", {"meta_pop_2023": "sum", "cob_poverty_pct": "mean",
                                 "cob_median_hh_income": "mean", "cob_pct_fossil_heat": "mean"},
                     source="census_acs")
    write_interim(out, "census_acs")
    register_source(
        "census_acs5_2023", raw_files=files,
        name="ACS 5-year estimates 2019-2023: B01003, B17001, B19013, B25040",
        url=API_URL if key else SF_URL.format(y=YEAR, t="<table>"), vintage="ACS 2019-2023 5-year",
        license="Public domain (US Government work)",
        notes=(f"Retrieved via {method}. CENSUS_API_KEY was "
               + ("set." if key else "not set, so the bulk Summary File (same published estimates) was used. ")
               + "Poverty % uses detailed table B17001 (below poverty / poverty universe), which is the "
                 "basis of subject table S1701's percent below poverty; S1701 is not in the bulk file. "
                 "Fossil heat = (utility gas + bottled/LP gas + fuel oil/kerosene) / occupied units."),
    )
    set_status("census_acs5_2023", "OK", f"{len(out)} counties via {method}.",
               ["meta_pop_2023", "cob_poverty_pct", "cob_median_hh_income", "cob_pct_fossil_heat"])


if __name__ == "__main__":
    main()
