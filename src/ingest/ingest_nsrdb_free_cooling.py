"""NREL NSRDB GOES TMY (PSM v4): free-cooling hours and high wet-bulb hours at each county's population centroid.

Needs NREL_API_KEY (free, https://developer.nlr.gov/signup/) and CONTACT_EMAIL (the API requires a real address).
One CSV per county is cached in data/raw/nsrdb_tmy/, so the script is resumable across days/rate limits.
"""
import time

import numpy as np
import pandas as pd
import requests

from src.common.counties import centroids_albers
from src.common.io import RAW, env_key, register_source, set_status, write_interim

API = "https://developer.nlr.gov/api/nsrdb/v2/solar/nsrdb-GOES-tmy-v4-0-0-download.csv"
NAMES = "tmy"  # latest tmy-20yy available
FREE_COOLING_MAX_DRYBULB_C = 18.0
FREE_COOLING_MAX_DEWPOINT_C = 15.0
WETBULB_THRESHOLD_C = 26.0
SLEEP_S = 2.1
FEATURES = ["haz_free_cooling_pct_hours", "haz_wetbulb_gt26c_hours"]
OUT = RAW / "nsrdb_tmy"


def stull_wetbulb(t_c: np.ndarray, rh_pct: np.ndarray) -> np.ndarray:
    """Stull (2011) wet-bulb temperature from dry-bulb (°C) and relative humidity (%)."""
    rh = np.clip(rh_pct, 5, 99)
    return (t_c * np.arctan(0.151977 * np.sqrt(rh + 8.313659)) + np.arctan(t_c + rh) - np.arctan(rh - 1.676331)
            + 0.00391838 * rh ** 1.5 * np.arctan(0.023101 * rh) - 4.686035)


def fetch(fips: str, lon: float, lat: float, key: str, email: str) -> pd.DataFrame | None:
    dest = OUT / f"{fips}.csv"
    if not dest.exists():
        params = {"api_key": key, "wkt": f"POINT({lon:.4f} {lat:.4f})", "names": NAMES, "email": email,
                  "attributes": "air_temperature,dew_point,relative_humidity", "utc": "false", "leap_day": "false"}
        t0 = time.time()
        r = None
        for attempt in range(4):
            try:
                r = requests.get(API, params=params, timeout=120)
                break
            except requests.RequestException as e:
                print(f"  {fips}: {type(e).__name__} (attempt {attempt + 1}/4); retrying")
                time.sleep(5 * (attempt + 1))
        if r is None:
            print(f"  {fips}: connection failed after retries")
            return None
        if r.status_code == 429:
            raise RuntimeError("rate limited (429); re-run later, progress is cached")
        if r.status_code != 200 or r.text.lstrip().startswith("{"):
            print(f"  {fips}: HTTP {r.status_code} {r.text[:200]}")
            return None
        OUT.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        tmp.write_text(r.text)
        tmp.rename(dest)
        time.sleep(max(0.0, SLEEP_S - (time.time() - t0)))  # >= SLEEP_S between request starts
    df = pd.read_csv(dest, skiprows=2)  # rows 0-1 are site metadata
    if len(df) != 8760:
        print(f"  {fips}: cached file has {len(df)} rows, deleting so the next run refetches")
        dest.unlink()
        return None
    return df


def summarize(df: pd.DataFrame) -> tuple[float, float]:
    t, td, rh = (df[c].to_numpy(float) for c in ("Temperature", "Dew Point", "Relative Humidity"))
    free = (t <= FREE_COOLING_MAX_DRYBULB_C) & (td <= FREE_COOLING_MAX_DEWPOINT_C)
    wb = stull_wetbulb(t, rh)
    return 100.0 * free.mean(), float((wb > WETBULB_THRESHOLD_C).sum())


def main():
    key, email = env_key("NREL_API_KEY"), env_key("CONTACT_EMAIL")
    if not key or not email:
        set_status("nsrdb_free_cooling", "BLOCKED",
                   "NREL_API_KEY and/or CONTACT_EMAIL not set (free key: https://developer.nlr.gov/signup/; the "
                   "NSRDB download API rejects requests without a valid email). DEMO_KEY is too rate-limited for "
                   "~3,108 calls.", FEATURES)
        return
    cen = centroids_albers().to_crs(4326)
    rows, failed = [], []
    n = len(cen)
    try:
        for i, (fips, pt) in enumerate(zip(cen["fips"], cen.geometry), 1):
            df = fetch(fips, pt.x, pt.y, key, email)
            if df is None:
                failed.append(fips)
                continue
            fc, wb = summarize(df)
            rows.append({"fips": fips, "haz_free_cooling_pct_hours": fc, "haz_wetbulb_gt26c_hours": wb})
            if i % 50 == 0 or i == n:
                print(f"[nsrdb] {i}/{n} processed, {len(rows)} ok, {len(failed)} failed", flush=True)
    except RuntimeError as e:
        print(f"[nsrdb] stopped early: {e}")
    done = {r["fips"] for r in rows}
    out = cen[["fips"]].merge(pd.DataFrame(rows, columns=["fips", *FEATURES]), on="fips", how="left")
    write_interim(out, "nsrdb_free_cooling")
    register_source(
        "nsrdb_free_cooling", raw_files=sorted(OUT.glob("*.csv"))[:20],
        name="NREL NSRDB GOES TMY PSM v4 (hourly typical meteorological year)",
        url=API, landing_page="https://developer.nlr.gov/docs/solar/nsrdb/nsrdb-GOES-tmy-v4-0-0-download/",
        vintage=f"names={NAMES} (latest tmy-20yy)", license="Public (NREL/NLR NSRDB; cite Sengupta et al. 2018)",
        notes=(f"One call per county at the population-weighted centroid (nearest 4 km NSRDB cell). Free-cooling hour "
               f"= dry-bulb <= {FREE_COOLING_MAX_DRYBULB_C} C AND dew point <= {FREE_COOLING_MAX_DEWPOINT_C} C; "
               f"percent of 8,760 hours. Wet-bulb via Stull (2011) from dry-bulb + RH; hours > {WETBULB_THRESHOLD_C} C."),
    )
    status = "OK" if len(done) == len(cen) else "PARTIAL"
    set_status("nsrdb_free_cooling", status,
               f"{len(done)}/{len(cen)} counties fetched; {len(failed)} failed. Re-run to resume.", FEATURES)


if __name__ == "__main__":
    main()
