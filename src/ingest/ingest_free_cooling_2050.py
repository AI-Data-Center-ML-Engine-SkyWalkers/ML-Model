"""Free-cooling hours around 2050 by the delta method: NSRDB TMY hourly data (cached by
ingest_nsrdb_free_cooling) shifted by the county's LOCA2 SSP2-4.5 change in annual mean temperature.

The CMRA county layer has no mean-temperature variable, so the change comes from the companion NOAA/CMRA
"LOCA2-Ensemble SSP2-4.5 Temperature Variables" county layer (decadal TAVG, 1950-2100).
"""
import json

import pandas as pd
import requests

from src.common.geo import table_join
from src.common.io import RAW, register_source, set_status, write_interim
from src.ingest.ingest_nsrdb_free_cooling import FREE_COOLING_MAX_DEWPOINT_C, FREE_COOLING_MAX_DRYBULB_C
from src.ingest.ingest_nsrdb_free_cooling import OUT as TMY_DIR

SERVICE = ("https://services3.arcgis.com/0Fs3HcaFfvzXvm7w/arcgis/rest/services/"
           "LOCA2_Ensemble_SSP245_Temperature_Variables_1950_2100/FeatureServer/0")
ITEM_SEARCH = "https://www.arcgis.com/sharing/rest/search?q=LOCA2-Ensemble%20SSP2-4.5%20Temperature%20Variables"
BASE_DECADES = [2000, 2010]    # brackets the NSRDB TMY observation years (1998-2023)
FUTURE_DECADES = [2040, 2050]  # centred on 2050
DEST = RAW / "loca2_temperature" / "loca2_ssp245_county_decadal_tavg.json"
FEATURES = ["haz_free_cooling_pct_hours_2050", "haz_tavg_delta_2050_c"]


def fetch_tavg() -> pd.DataFrame:
    if not DEST.exists():
        DEST.parent.mkdir(parents=True, exist_ok=True)
        print(f"[download] {SERVICE}/query")
        rows, off = [], 0
        while True:
            j = requests.get(f"{SERVICE}/query", params={
                "where": "1=1", "outFields": "GEOID,DECADE,TAVG", "returnGeometry": "false", "f": "json",
                "orderByFields": "OBJECTID", "resultOffset": off, "resultRecordCount": 2000}, timeout=300).json()
            if "error" in j:
                raise RuntimeError(j["error"])
            rows += [f["attributes"] for f in j["features"]]
            if len(j["features"]) < 2000:
                break
            off += len(j["features"])
        DEST.write_text(json.dumps(rows))
    return pd.DataFrame(json.loads(DEST.read_text()))


def main():
    t = fetch_tavg()
    t["GEOID"] = t["GEOID"].astype(str).str.zfill(5)
    base = t[t["DECADE"].isin(BASE_DECADES)].groupby("GEOID")["TAVG"].mean()
    fut = t[t["DECADE"].isin(FUTURE_DECADES)].groupby("GEOID")["TAVG"].mean()
    delta = ((fut - base) / 1.8).rename("haz_tavg_delta_2050_c").reset_index()
    delta = table_join(delta, "GEOID", {"haz_tavg_delta_2050_c": "mean"}, source="loca2_temperature")

    rows = []
    for fips, d_c in zip(delta["fips"], delta["haz_tavg_delta_2050_c"]):
        p = TMY_DIR / f"{fips}.csv"
        if not p.exists() or pd.isna(d_c):
            continue
        df = pd.read_csv(p, skiprows=2)
        if len(df) != 8760:
            continue
        free = (df["Temperature"] + d_c <= FREE_COOLING_MAX_DRYBULB_C) & \
               (df["Dew Point"] + d_c <= FREE_COOLING_MAX_DEWPOINT_C)
        rows.append({"fips": fips, "haz_free_cooling_pct_hours_2050": 100.0 * free.mean()})
    out = delta.merge(pd.DataFrame(rows, columns=["fips", "haz_free_cooling_pct_hours_2050"]), on="fips",
                      how="left")[["fips", *FEATURES]]
    write_interim(out, "free_cooling_2050")
    register_source(
        "loca2_temperature", raw_files=[DEST],
        name="NOAA/CMRA LOCA2-Ensemble SSP2-4.5 Temperature Variables 1950-2100, County layer",
        url=SERVICE, landing_page=f"https://resilience.climate.gov/ ; {ITEM_SEARCH}",
        vintage="LOCA2 (CMIP6) ensemble, SSP2-4.5, decadal means", license="Public (NOAA / US federal; CMRA)",
        notes=(f"haz_tavg_delta_2050_c = mean annual-average daily temperature (TAVG) of decades {FUTURE_DECADES} "
               f"minus decades {BASE_DECADES}, converted F -> C. haz_free_cooling_pct_hours_2050 (delta method): "
               "every TMY hour's dry-bulb AND dew point are raised by the delta (constant-relative-humidity "
               "approximation, as in standard weather-file morphing), then the Phase A free-cooling rule "
               f"(dry-bulb <= {FREE_COOLING_MAX_DRYBULB_C} C and dew point <= {FREE_COOLING_MAX_DEWPOINT_C} C) is "
               "re-applied. A uniform annual shift ignores seasonal/diurnal differences in warming."),
    )
    n = int(out["haz_free_cooling_pct_hours_2050"].notna().sum())
    set_status("free_cooling_2050", "OK" if n == len(out) else "PARTIAL",
               f"{n}/{len(out)} counties (needs the NSRDB TMY cache; re-run after nsrdb_free_cooling completes). "
               f"Delta range {out['haz_tavg_delta_2050_c'].min():.2f}-{out['haz_tavg_delta_2050_c'].max():.2f} C.",
               FEATURES)


if __name__ == "__main__":
    main()
