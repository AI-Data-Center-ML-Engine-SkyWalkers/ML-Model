"""NREL ReEDS 2024 county-level hourly capacity factors (reference land-use scenario): annual mean UPV and onshore wind CF."""
import h5py
import numpy as np
import pandas as pd
from remotezip import RemoteZip

from src.common.geo import table_join
from src.common.io import RAW, register_source, set_status, write_interim

BASE = "https://data.openei.org/files/8379/"
FILES = {
    "crb_solar_cf": ("upv_county_20250325.zip", "upv/upv-reference_county.h5"),
    "crb_wind_cf": ("wind-ons_county_20250325.zip", "wind-ons/wind-ons-reference_county.h5"),
}
DEST = RAW / "nrel_reeds_cf"
BLOCK_COLS = 260


def fetch(zip_name: str, member: str):
    """Extract only the reference-scenario member from the multi-GB zip via HTTP range requests."""
    out = DEST / member
    if out.exists():
        print(f"[download] cached {out}")
        return out
    print(f"[download] {BASE + zip_name} (member {member})")
    with RemoteZip(BASE + zip_name) as z:
        z.extract(member, DEST)
    return out


def county_mean_cf(path) -> tuple[pd.Series, dict]:
    with h5py.File(path) as h:
        cols = [c.decode() for c in h["columns"][:]]
        ds = h["data"]
        means = np.empty(len(cols))
        for i in range(0, len(cols), BLOCK_COLS):
            means[i:i + BLOCK_COLS] = ds[:, i:i + BLOCK_COLS].mean(axis=0)
        idx = h["index_0"]
        span = (idx[0].decode()[:10], idx[-1].decode()[:10], len(idx))
    s = pd.DataFrame({"col": cols, "cf": means})
    s["fips"] = s["col"].str.split("|").str[1].str.lstrip("p").str.zfill(5)
    by = s.groupby("fips")["cf"]
    return by.mean(), {"classes_per_county_max": int(by.size().max()), "hours": span}


def main():
    frames, info, paths = [], {}, []
    for col, (zname, member) in FILES.items():
        p = fetch(zname, member)
        paths.append(p)
        cf, meta = county_mean_cf(p)
        info[col] = meta
        frames.append(cf.rename(col))
    df = pd.concat(frames, axis=1).reset_index().rename(columns={"index": "fips"})
    out = table_join(df, "fips", {c: "mean" for c in FILES}, source="nrel_reeds_cf")
    write_interim(out, "nrel_reeds_cf")
    register_source(
        "nrel_reeds_county_cf", raw_files=paths, name="2024 County-Level Hourly Renewable Capacity Factor Dataset for the ReEDS Model",
        url=" ; ".join(BASE + z for z, _ in FILES.values()), landing_page="https://data.openei.org/submissions/8379",
        vintage="2024 dataset (files dated 2025-03-25; UPV supply curve 2024_07_09, wind 2025_03_21); weather years 2007-2013 + 2016-2023",
        license="CC BY 4.0 (OEDI)",
        notes=(f"Reference land-use scenario only (open/limited not used), extracted from the zip with HTTP range reads. "
               f"Per column (resource class x county) mean over all hours, then UNWEIGHTED mean across the resource classes "
               f"present in the county (no capacity weights in the file; ambiguous - capacity-weighted or best-class would "
               f"differ). {info}. Counties with no developable class in the reference scenario are NaN. Most "
               "missing rows are Virginia independent cities, which ReEDS folds into surrounding counties; they are "
               "left NaN rather than borrowing the parent county's value."),
    )
    set_status("nrel_reeds_county_cf", "OK",
               f"solar CF for {out['crb_solar_cf'].notna().sum()} counties, wind CF for {out['crb_wind_cf'].notna().sum()}.",
               list(FILES))


if __name__ == "__main__":
    main()
