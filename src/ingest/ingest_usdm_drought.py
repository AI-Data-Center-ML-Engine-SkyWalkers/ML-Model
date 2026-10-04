"""US Drought Monitor county statistics 2000-2025: % of weeks with any D2-D4 area."""
import pandas as pd

from src.common.fips_fixes import STATE_FIPS_TO_ABBR, EXCLUDED_STATE_FIPS
from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

URL = "https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
START, END = "1/1/2000", "12/31/2025"


def main():
    states = [a for f, a in STATE_FIPS_TO_ABBR.items() if f not in EXCLUDED_STATE_FIPS]
    frames, files = [], []
    for st in states:
        # statisticsType=1 = cumulative ("traditional"): the D2 column is the area in D2 or worse.
        p = download(URL, f"usdm/county_{st}_2000_2025.csv",
                     params={"aoi": st, "startdate": START, "enddate": END, "statisticsType": 1},
                     min_bytes=1000, timeout=600)
        files.append(p)
        frames.append(pd.read_csv(p, dtype={"FIPS": str}))
    df = pd.concat(frames, ignore_index=True)
    df["d2plus"] = pd.to_numeric(df["D2"], errors="coerce") > 0
    g = df.groupby("FIPS").agg(weeks=("MapDate", "nunique"), d2=("d2plus", "sum")).reset_index()
    g["wtr_drought_d2plus_pct_weeks"] = 100 * g["d2"] / g["weeks"]
    out = table_join(g, "FIPS", {"wtr_drought_d2plus_pct_weeks": "mean"}, source="usdm_drought")
    write_interim(out, "usdm_drought")
    register_source(
        "usdm_drought", raw_files=files, name="US Drought Monitor county statistics (percent area, cumulative)",
        url=URL, landing_page="https://droughtmonitor.unl.edu/DmData/DataDownload/ComprehensiveStatistics.aspx",
        vintage=f"weekly maps {START} to {END} ({int(g['weeks'].max())} weeks)",
        license="Public domain; credit: National Drought Mitigation Center, USDA, NOAA",
        notes="One REST call per state for the full period. A week counts if the D2-D4 area > 0%.",
    )
    set_status("usdm_drought", "OK", f"{len(out)} counties, {int(g['weeks'].max())} weeks.",
               ["wtr_drought_d2plus_pct_weeks"])


if __name__ == "__main__":
    main()
