"""EPA Green Book: county currently in nonattainment for any (non-revoked) NAAQS."""
import pandas as pd

from src.common.counties import load_counties
from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

URL = "https://www3.epa.gov/airquality/greenbook/downld/phistory.xls"


def main():
    p = download(URL, "epa_greenbook/phistory.xls")
    df = pd.read_excel(p)
    year_cols = sorted(c for c in df.columns if c.startswith("pw_"))
    latest = year_cols[-1]
    export = str(df["exportdt"].iloc[0])[:10]
    cur = df[df["revoked_naaqs"].isna() & df[latest].isin(["P", "W"])].copy()
    cur["fips"] = cur["fips_state"].astype(int).astype(str).str.zfill(2) + \
        cur["fips_cnty"].astype(int).astype(str).str.zfill(3)
    cur["prm_nonattainment"] = 1
    flagged = table_join(cur, "fips", {"prm_nonattainment": "max"}, source="epa_greenbook")
    base = load_counties()[["fips"]]
    out = base.merge(flagged, on="fips", how="left")
    out["prm_nonattainment"] = out["prm_nonattainment"].fillna(0).astype(int)
    write_interim(out, "epa_greenbook")
    register_source(
        "epa_greenbook", raw_files=[p], name="EPA Green Book - nonattainment/maintenance history by county (phistory)",
        url=URL, landing_page="https://www.epa.gov/green-book/green-book-data-download",
        vintage=f"export {export}, status year {latest[3:]}", license="Public domain (US Government work)",
        notes="1 if the county is wholly (W) or partly (P) in a nonattainment area in the latest year for any "
              "NAAQS that is not revoked; else 0.",
    )
    set_status("epa_greenbook", "OK", f"{int(out['prm_nonattainment'].sum())} counties in nonattainment ({latest}).",
               ["prm_nonattainment"])


if __name__ == "__main__":
    main()
