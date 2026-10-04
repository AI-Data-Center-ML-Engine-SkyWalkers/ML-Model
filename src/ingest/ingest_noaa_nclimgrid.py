"""NOAA nClimGrid-Daily county averages 1991-2020: CDD, HDD (base 65F) and days with Tmax > 35C.

The county ID in these files is NCEI state code (alphabetical, e.g. CT=06) + FIPS county code,
so the FIPS state code is rebuilt from the state abbreviation in the name field.
"""
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from src.common.fips_fixes import STATE_ABBR_TO_FIPS
from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

BASE = "https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/{y}/{v}-{y}{m:02d}-cty-scaled.csv"
YEARS = range(1991, 2021)
BASE_F = 65.0
HOT_C = 35.0
MISSING = -999.0


def _fetch(args):
    v, y, m = args
    return download(BASE.format(v=v, y=y, m=m), f"nclimgrid/{y}/{v}-{y}{m:02d}-cty-scaled.csv",
                    min_bytes=10000, allow_html=False)


def _read(path) -> tuple[pd.Series, np.ndarray]:
    df = pd.read_csv(path, header=None)
    abbr = df[2].str.split(":").str[0].str.strip()
    fips = abbr.map(STATE_ABBR_TO_FIPS) + df[1].astype(str).str.zfill(5).str[2:]
    fips = fips.replace({"11511": "11001"})  # nClimGrid codes DC as county 511
    vals = df.iloc[:, 6:].to_numpy(dtype=float)
    vals[vals <= MISSING] = np.nan
    return fips, vals


def main():
    jobs = [(v, y, m) for v in ("tavg", "tmax") for y in YEARS for m in range(1, 13)]
    with ThreadPoolExecutor(8) as ex:
        paths = dict(zip(jobs, ex.map(_fetch, jobs)))

    acc = {}
    for (v, y, m), p in paths.items():
        fips, vals = _read(p)
        if v == "tavg":
            tf = vals * 9 / 5 + 32
            cdd = np.nansum(np.clip(tf - BASE_F, 0, None), axis=1)
            hdd = np.nansum(np.clip(BASE_F - tf, 0, None), axis=1)
            part = pd.DataFrame({"fips": fips, "cdd": cdd, "hdd": hdd})
        else:
            part = pd.DataFrame({"fips": fips, "hot": np.nansum(vals > HOT_C, axis=1)})
        part["year"] = y
        acc.setdefault(v, []).append(part)

    tavg = pd.concat(acc["tavg"]).groupby(["fips", "year"])[["cdd", "hdd"]].sum()
    tmax = pd.concat(acc["tmax"]).groupby(["fips", "year"])[["hot"]].sum()
    annual = tavg.join(tmax, how="outer").groupby("fips").mean().reset_index()
    n_years = pd.concat(acc["tavg"]).groupby("fips")["year"].nunique()
    assert (n_years == len(YEARS)).all(), "missing years for some counties"
    annual = annual.rename(columns={"cdd": "haz_cdd_annual", "hdd": "cob_hdd_annual", "hot": "haz_days_tmax_gt35c"})
    out = table_join(annual, "fips", {"haz_cdd_annual": "mean", "cob_hdd_annual": "mean",
                                      "haz_days_tmax_gt35c": "mean"}, source="noaa_nclimgrid")
    write_interim(out, "noaa_nclimgrid")
    register_source(
        "noaa_nclimgrid_daily", raw_files=list(paths.values())[:1] + list(paths.values())[-1:],
        name="NOAA nClimGrid-Daily county-averaged daily temperature (scaled CSVs)",
        url=BASE.format(v="{tavg|tmax}", y="{year}", m=0).replace("00-", "{MM}-"),
        landing_page="https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily",
        vintage="1991-2020 daily (nClimGrid-Daily v1, scaled county averages)",
        license="Public domain (NOAA)",
        notes=("CDD/HDD from daily TAVG converted to F, base 65F, summed per year then averaged over "
               "1991-2020. Hot days: daily TMAX > 35C. County ID in files = NCEI state code + FIPS county, "
               "remapped to FIPS via the state abbreviation. CT uses old counties -> area-weighted to "
               "planning regions. 720 monthly files cached under data/raw/nclimgrid/."),
    )
    set_status("noaa_nclimgrid_daily", "OK",
               f"{len(out)} counties, 1991-2020. Lexington city VA (51678) has no row in nClimGrid -> NaN.",
               ["haz_cdd_annual", "cob_hdd_annual", "haz_days_tmax_gt35c"])


if __name__ == "__main__":
    main()
