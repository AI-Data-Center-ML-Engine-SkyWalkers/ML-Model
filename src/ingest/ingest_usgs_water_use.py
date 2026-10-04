"""USGS NWAA Data Companion: 2020 water withdrawals (public supply + irrigation + thermoelectric), HUC12 -> county."""
import json
import time

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import shape

from src.common.counties import load_counties
from src.common.fips_fixes import STATE_FIPS_TO_ABBR
from src.common.geo import polygon_area_weighted_sum
from src.common.io import CONTACT_UA, RAW, register_source, set_status, write_interim

API = "https://api.water.usgs.gov/nwaa-data/data"
YEAR = "2020"
MODELS = {  # model -> (variables, format). Geometry comes once, from the public-supply pull.
    "wu-public-supply-wd": (["pswdtot"], "geojson"),
    "wu-irrigation-wd": (["irrwdtot"], "json"),
    "wu-thermoelectric": (["tewdftot", "tewdssw"], "json"),
}
OUT = RAW / "usgs_nwaa"


def _get(params: dict) -> dict:
    for attempt in range(5):
        try:
            r = requests.get(API, params=params, headers={"User-Agent": CONTACT_UA}, timeout=300)
            if r.status_code == 200:
                return r.json()
            print(f"  HTTP {r.status_code}: {r.text[:200]}")
        except requests.RequestException as e:
            print(f"  {e}")
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"NWAA request failed: {params}")


def fetch_state(model: str, st: str) -> list:
    variables, fmt = MODELS[model]
    files, skip = [], 0
    while True:
        dest = OUT / model / f"{st}_{skip:06d}.json"
        files.append(dest)
        if dest.exists():
            j = json.loads(dest.read_text())
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            params = {"model": model, "variable": ",".join(variables), "location": f"stateCd:{st}",
                      "timeres": "annualcy", "startdate": YEAR, "enddate": YEAR, "intersection": "overlap",
                      "format": fmt, "limit": 600, "skip": skip}
            print(f"[download] {API} {model} {st} skip={skip}")
            j = _get(params)
            dest.write_text(json.dumps(j))
        md = j["metadata"]
        skip += md["recordsReturned"]
        if skip >= md["totalRecords"] or md["recordsReturned"] == 0:
            return files


def _values(files: list, variables: list[str]) -> pd.DataFrame:
    rows = []
    for f in files:
        j = json.loads(f.read_text())
        if "features" in j:
            for ft in j["features"]:
                p = ft["properties"]
                rec = next((r for r in p.get("data", [p]) if str(r.get("year", YEAR)) == YEAR), p)
                rows.append({"huc12": p.get("huc12_id") or p.get("huc12"), **{v: rec.get(v) for v in variables},
                             "geometry": shape(ft["geometry"])})
        else:
            for huc, recs in j["data"]["huc12_id"].items():
                rec = next(r for r in recs if str(r["year"]) == YEAR)
                rows.append({"huc12": huc, **{v: rec.get(v) for v in variables}})
    return pd.DataFrame(rows).drop_duplicates("huc12")


def main():
    cty = load_counties()
    states = sorted({STATE_FIPS_TO_ABBR[f[:2]] for f in cty["fips"]})
    files = {m: [] for m in MODELS}
    for m in MODELS:
        for st in states:
            files[m] += fetch_state(m, st)

    ps = _values(files["wu-public-supply-wd"], MODELS["wu-public-supply-wd"][0])
    irr = _values(files["wu-irrigation-wd"], MODELS["wu-irrigation-wd"][0])
    te = _values(files["wu-thermoelectric"], MODELS["wu-thermoelectric"][0])
    huc = ps.merge(irr, on="huc12", how="outer").merge(te, on="huc12", how="outer")
    no_geom = huc["geometry"].isna().sum()
    huc = gpd.GeoDataFrame(huc.dropna(subset=["geometry"]), geometry="geometry", crs="EPSG:4326")
    cols = ["pswdtot", "irrwdtot", "tewdftot", "tewdssw"]
    for c in cols:
        huc[c] = pd.to_numeric(huc[c], errors="coerce")
    huc["wtr_total_withdrawal_mgd"] = huc[cols].sum(axis=1, min_count=1)
    huc[["huc12", *cols, "wtr_total_withdrawal_mgd"]].to_csv(OUT / "huc12_2020_withdrawals.csv", index=False)

    out = polygon_area_weighted_sum(huc, ["wtr_total_withdrawal_mgd", "pswdtot", "irrwdtot", "tewdftot",
                                          "tewdssw"], cty)
    out = out.rename(columns={"pswdtot": "wtr_ps_withdrawal_mgd", "irrwdtot": "wtr_irr_withdrawal_mgd"})
    out["wtr_te_withdrawal_mgd"] = out[["tewdftot", "tewdssw"]].sum(axis=1, min_count=1)
    out = out.drop(columns=["tewdftot", "tewdssw"])
    write_interim(out, "usgs_water_use")

    all_files = [f for fs in files.values() for f in fs]
    register_source(
        "usgs_water_use", raw_files=[OUT / "huc12_2020_withdrawals.csv"],
        name="USGS National Water Availability Assessment (NWAA) Data Companion - water-use models",
        url=f"{API}?model={{{','.join(MODELS)}}}&location=stateCd:XX&timeres=annualcy&startdate={YEAR}",
        landing_page="https://water.usgs.gov/nwaa-data/", vintage=f"NWDC API v2.1.0, calendar year {YEAR}",
        license="Public domain (USGS)",
        notes=(f"{len(all_files)} cached API pages in {OUT}. The NWAA models are HUC12-only (no county table), so "
               "HUC12 annual mean withdrawals (Mgal/d) are split onto counties by the share of each HUC12's area that "
               "falls in the county (EPSG:5070); assumes withdrawals are uniform within a HUC12. HUC12 area outside "
               "CONUS counties (ocean, Canada, Mexico) is dropped. wtr_total_withdrawal_mgd = public supply (pswdtot) "
               "+ crop irrigation (irrwdtot) + thermoelectric fresh (tewdftot) + thermoelectric saline (tewdssw). "
               "NWAA does not model industrial, mining, livestock, aquaculture or domestic self-supplied use, so this "
               "is NOT the full USGS 'total withdrawals' of the legacy 5-year compilations. Component columns "
               f"wtr_ps/irr/te_withdrawal_mgd are kept. {no_geom} HUC12s had values but no geometry and were dropped."),
    )
    set_status("usgs_water_use", "OK", f"{len(huc)} HUC12s area-weighted onto counties (2020).",
               ["wtr_total_withdrawal_mgd", "wtr_ps_withdrawal_mgd", "wtr_irr_withdrawal_mgd", "wtr_te_withdrawal_mgd"])


if __name__ == "__main__":
    main()
