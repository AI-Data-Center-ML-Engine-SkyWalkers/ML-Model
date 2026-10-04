"""EPA Clean Watersheds Needs Survey 2022: existing design flow of wastewater treatment plants per county (MGD)."""
import html
import re
import zipfile

import geopandas as gpd
import pandas as pd
import requests

from src.common.counties import load_counties
from src.common.fips_fixes import apply_fips_fixes
from src.common.io import RAW, register_source, set_status, write_interim

APP = "https://sdwis.epa.gov/ords/sfdw_pub/"
PAGE = APP + "r/sfdw/cwns_pub/data-download"
DEST = RAW / "epa_cwns"


def fetch() -> "Path":
    """The national zip is served by APEX page 2 after the survey pop-up sets P2_LOCATION_ID=NA in session state."""
    cached = sorted(DEST.glob("2022CWNS_NATIONAL_*.zip"))
    if cached:
        print(f"[download] cached {cached[-1]}")
        return cached[-1]
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    print(f"[download] {PAGE} (APEX session flow, national CSV zip)")
    t = s.get(PAGE, timeout=60).text
    sess = re.search(r'name="p_instance" value="(\d+)"', t).group(1)
    pops = [html.unescape(x).encode().decode("unicode_escape")
            for x in re.findall(r"dialog\(&#x27;(.*?)&#x27;", t)]
    s.get("https://sdwis.epa.gov" + next(p for p in pops if "NA_CSV" in p), timeout=60)
    r = s.get(APP + f"f?p=148:2:{sess}:::::", timeout=900)
    name = re.search(r'filename="([^"]+)"', r.headers.get("content-disposition", ""))
    if r.status_code != 200 or not name:
        raise RuntimeError(f"CWNS download did not return a file (HTTP {r.status_code})")
    DEST.mkdir(parents=True, exist_ok=True)
    out = DEST / name.group(1)
    out.write_bytes(r.content)
    return out


def main():
    p = fetch()
    z = zipfile.ZipFile(p)
    prefix = z.namelist()[0].split("/")[0] + "/"
    read = lambda n: pd.read_csv(z.open(prefix + n + ".csv"), encoding="latin1", low_memory=False,
                                 dtype={"COUNTY_FIPS": str})
    types, flow = read("FACILITY_TYPES"), read("FLOW")
    plants = types.loc[types["FACILITY_TYPE"] == "Treatment Plant", "FACILITY_ID"].unique()
    tot = flow[(flow["FLOW_TYPE"] == "Total Flow") & flow["FACILITY_ID"].isin(plants)]
    tot = tot.groupby("FACILITY_ID", as_index=False)["CURRENT_DESIGN_FLOW"].max()
    tot = tot[tot["CURRENT_DESIGN_FLOW"] > 0]

    areas = read("AREAS_COUNTY")
    prim = areas[areas["COUNTY_PRIMARY_FLAG"] == "Y"].drop_duplicates("FACILITY_ID").set_index("FACILITY_ID")["COUNTY_FIPS"]
    tot["fips"] = tot["FACILITY_ID"].map(prim).str.zfill(5)
    n_table = int(tot["fips"].notna().sum())
    loc = read("PHYSICAL_LOCATION").drop_duplicates("FACILITY_ID").set_index("FACILITY_ID")
    miss = tot["fips"].isna()
    xy = loc.reindex(tot.loc[miss, "FACILITY_ID"])[["LATITUDE", "LONGITUDE"]].dropna()
    if len(xy):
        pts = gpd.GeoDataFrame(xy, geometry=gpd.points_from_xy(xy["LONGITUDE"], xy["LATITUDE"]), crs="EPSG:4269")
        j = gpd.sjoin(pts, load_counties()[["fips", "geometry"]], how="left", predicate="within")
        j = j[~j.index.duplicated()]
        tot.loc[miss, "fips"] = tot.loc[miss, "FACILITY_ID"].map(j["fips"])
    n_unloc = int(tot["fips"].isna().sum())
    agg = tot.dropna(subset=["fips"]).groupby("fips", as_index=False)["CURRENT_DESIGN_FLOW"].sum()
    agg = apply_fips_fixes(agg.rename(columns={"CURRENT_DESIGN_FLOW": "wtr_wwtp_flow_mgd"}),
                           {"wtr_wwtp_flow_mgd": "sum"}, source="epa_cwns")
    out = load_counties()[["fips"]].merge(agg, on="fips", how="left").fillna({"wtr_wwtp_flow_mgd": 0.0})
    write_interim(out, "epa_cwns")
    register_source(
        "epa_cwns", raw_files=[p], name="EPA Clean Watersheds Needs Survey 2022 - nationwide CSV dataset",
        url=PAGE + " (national 'Download CSVs'; served via APEX page f?p=148:2)", landing_page="https://www.epa.gov/cwns",
        vintage=f"2022 CWNS (snapshot as of 2022-01-01); file {p.name}", license="Public domain (US Government work)",
        notes=(f"Facilities with FACILITY_TYPE 'Treatment Plant'; CURRENT_DESIGN_FLOW of FLOW_TYPE 'Total Flow' (MGD), "
               f"> 0. {len(tot)} plants, {tot['CURRENT_DESIGN_FLOW'].sum():,.0f} MGD total. County = AREAS_COUNTY primary "
               f"county ({n_table} plants), else facility coordinates point-in-polygon; {n_unloc} unlocated. Counties "
               "with no plant = 0. Old CT counties converted to planning regions by area weight."),
    )
    set_status("epa_cwns", "OK", f"{len(tot) - n_unloc} treatment plants located.", ["wtr_wwtp_flow_mgd"])


if __name__ == "__main__":
    main()
