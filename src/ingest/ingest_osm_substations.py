"""OpenStreetMap power=substation with max voltage >= 230 kV, via Overpass API per state (cached per state)."""
import json
import re
import time

import geopandas as gpd
import pandas as pd
import requests

from src.common.counties import load_counties
from src.common.fips_fixes import STATE_FIPS_TO_ABBR
from src.common.geo import points_to_county
from src.common.io import RAW, register_source, set_status, write_interim

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = "datacenter-siting/0.1 (iMasons OCP hackathon research script)"
MIN_V = 230_000
QUERY = """[out:json][timeout:600];
area["ISO3166-2"="US-{st}"]["admin_level"="4"]->.a;
nwr["power"="substation"]["voltage"](area.a);
out center tags;"""


def max_voltage(v) -> float:
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(v))]
    nums = [n * 1000 if n < 1000 else n for n in nums]  # tolerate "345" / "345 kV" style values
    return max(nums) if nums else float("nan")


def fetch_state(st: str) -> tuple[list, str]:
    dest = RAW / "osm_substations" / f"{st}.json"
    if dest.exists():
        return json.loads(dest.read_text())["elements"], str(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(6):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        print(f"[download] {url} (US-{st} substations)")
        try:
            r = requests.post(url, data={"data": QUERY.format(st=st)}, headers={"User-Agent": UA}, timeout=900)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
                j = r.json()
                if "remark" in j and "error" in j["remark"].lower():
                    raise RuntimeError(j["remark"])
                dest.write_text(json.dumps(j))
                return j["elements"], str(dest)
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = str(e)
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"Overpass failed for {st}: {last}")


def main():
    states = sorted(a for f, a in STATE_FIPS_TO_ABBR.items() if f in set(load_counties()["meta_state_fips"]))
    rows, files, failed = [], [], []
    for st in states:
        try:
            els, f = fetch_state(st)
        except RuntimeError as e:
            print(e)
            failed.append(st)
            continue
        files.append(f)
        for e in els:
            c = e.get("center") or ({"lat": e["lat"], "lon": e["lon"]} if "lat" in e else None)
            if c:
                rows.append({"osm": f"{e['type']}/{e['id']}", "lat": c["lat"], "lon": c["lon"],
                             "v": max_voltage(e.get("tags", {}).get("voltage"))})
    df = pd.DataFrame(rows).drop_duplicates("osm")
    hv = df[df["v"] >= MIN_V]
    pts = gpd.GeoDataFrame(hv, geometry=gpd.points_from_xy(hv["lon"], hv["lat"]), crs="EPSG:4326")
    cty = load_counties()
    out = points_to_county(pts, cty, "pwr_substations_230kv_n")
    if failed:
        out.loc[out["fips"].str[:2].isin([f for f, a in STATE_FIPS_TO_ABBR.items() if a in failed]),
                "pwr_substations_230kv_n"] = float("nan")
    write_interim(out, "osm_substations")
    register_source(
        "osm_substations", raw_files=files, name="OpenStreetMap power=substation (Overpass API, per state)",
        url=ENDPOINTS[0], landing_page="https://wiki.openstreetmap.org/wiki/Tag:power%3Dsubstation",
        vintage=f"Overpass snapshot {pd.Timestamp.today().date()} (cached per state)", license="ODbL 1.0 (OpenStreetMap contributors)",
        notes=(f"Substations with a voltage tag; max of multi-voltage strings; values < 1000 treated as kV. "
               f"{len(df)} tagged substations, {len(pts)} with max voltage >= 230 kV. Ways/relations use Overpass center. "
               f"Substations crossing state lines are deduplicated by OSM id. Untagged-voltage substations are excluded. "
               f"Failed states (NaN): {failed or 'none'}."),
    )
    set_status("osm_substations", "OK" if not failed else "PARTIAL",
               f"{len(pts)} substations >= 230 kV; failed states: {failed or 'none'}.", ["pwr_substations_230kv_n"])


if __name__ == "__main__":
    main()
