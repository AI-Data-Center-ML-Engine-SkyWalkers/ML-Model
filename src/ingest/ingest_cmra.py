"""CMRA Climate Assessment Data (2025 version, LOCA2): days with Tmax > 95F, SSP2-4.5 mid-century, by county."""
import json

import pandas as pd
import requests

from src.common.geo import table_join
from src.common.io import RAW, register_source, set_status, write_interim

SERVICE = "https://services3.arcgis.com/0Fs3HcaFfvzXvm7w/arcgis/rest/services/CMRA_Tool_Dev/FeatureServer/0"
ITEM = "https://www.arcgis.com/home/item.html?id=54f4e2343500422bbddf1f5dafb30bbd"
FIELD = "RCP45MID_MEAN_TMAX95F"  # alias: "Days with a maximum temperature > 95degF - SSP2-4.5 Mid-century - Mean"
DEST = RAW / "cmra" / "cmra_counties_2025_all_attributes.json"


def fetch() -> list[dict]:
    """Cache every attribute of every county (no geometry); the portal's future is uncertain."""
    if DEST.exists():
        print(f"[download] cached {DEST}")
        return json.loads(DEST.read_text())
    DEST.parent.mkdir(parents=True, exist_ok=True)
    rows, offset = [], 0
    while True:
        params = {"where": "1=1", "outFields": "*", "returnGeometry": "false", "f": "json",
                  "resultOffset": offset, "resultRecordCount": 1000, "orderByFields": "GEOID"}
        print(f"[download] {SERVICE}/query offset={offset}")
        j = requests.get(SERVICE + "/query", params=params, timeout=300).json()
        if "error" in j:
            raise RuntimeError(j["error"])
        feats = [f["attributes"] for f in j["features"]]
        rows += feats
        if not j.get("exceededTransferLimit") and len(feats) < 1000:
            break
        offset += len(feats)
    DEST.write_text(json.dumps(rows))
    return rows


def main():
    rows = fetch()
    df = pd.DataFrame(rows)
    df["fips"] = df["GEOID"].astype(str).str.zfill(5)
    df["haz_days_gt95f_2050"] = pd.to_numeric(df[FIELD], errors="coerce")
    out = table_join(df[["fips", "haz_days_gt95f_2050"]], "fips", {"haz_days_gt95f_2050": "mean"}, source="cmra")
    write_interim(out, "cmra")
    register_source(
        "cmra_2025", raw_files=[DEST], name="CMRA Climate Assessment Data (2025 Version) - Counties layer",
        url=SERVICE, landing_page=f"https://resilience.climate.gov/ ; {ITEM}",
        vintage="CMRA 2025 version (LOCA2 / CMIP6); Census 2019 county geography", license="CC BY 4.0 (item license)",
        notes=(f"{FIELD} = ensemble-mean annual days with Tmax > 95F, SSP2-4.5 mid-century (field names keep the "
               f"'RCP45' prefix; aliases say SSP2-4.5). All {len(df.columns) - 2} attributes cached to raw for Phase B "
               "(delta method). 2019 counties: old CT counties area-weighted to planning regions; 46113/51515 fixed."),
    )
    set_status("cmra_2025", "OK", f"{out['haz_days_gt95f_2050'].notna().sum()} counties.", ["haz_days_gt95f_2050"])


if __name__ == "__main__":
    main()
