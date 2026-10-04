"""FIPS normalisation and boundary-change fixes applied to every table-based source.

Usage:
    df = normalize_fips(df, "GEOID")                     # -> df["fips"], 5-char str
    df = apply_fips_fixes(df, {"col_a": "sum", "col_b": "mean"}, source="laus")

`how` per value column:
    "sum"   extensive quantity (counts, MW, gallons). Renamed FIPS are summed; old CT
            counties are split to planning regions by share of the old county's area.
    "mean"  intensive quantity (rates, scores, %). Renamed FIPS are averaged; CT planning
            regions get the area-weighted mean of the old counties that overlap them.
    "max"   flags (0/1). Renamed FIPS take the max; CT regions take the value of the old
            county covering most of the region.
    "first" categorical. Same as "max" for CT, first for renames.
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from .io import INTERIM

# Old FIPS -> current FIPS (2025 vintage)
FIPS_RENAMES = {
    "46113": "46102",  # Shannon County SD -> Oglala Lakota County (2015)
    "51515": "51019",  # Bedford City VA merged into Bedford County (2013)
    "51560": "51005",  # Clifton Forge City VA merged into Alleghany County (2001)
    "12025": "12086",  # Dade County FL -> Miami-Dade (1997)
}

CT_OLD_COUNTIES = {f"090{c:02d}" for c in range(1, 16, 2)}  # 09001..09015
CT_NEW_REGIONS = {f"09{c}" for c in range(110, 200, 10)}  # 09110..09190

STATE_FIPS_TO_ABBR = {
    "01": "AL", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC",
    "12": "FL", "13": "GA", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO",
    "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC",
    "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "02": "AK", "15": "HI", "60": "AS", "66": "GU", "69": "MP", "72": "PR", "78": "VI",
}
STATE_ABBR_TO_FIPS = {v: k for k, v in STATE_FIPS_TO_ABBR.items()}
EXCLUDED_STATE_FIPS = {"02", "15", "60", "66", "69", "72", "78"}

CT_LOG = INTERIM / "_ct_crosswalk_log.json"


def zfill_fips(x) -> str | None:
    """Turn 6037, 6037.0, '6037', ' 06037 ' into '06037'. Returns None for blanks."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return None
    s = re.sub(r"\.0+$", "", s)
    if not s.isdigit():
        return None
    return s.zfill(5)


def normalize_fips(df: pd.DataFrame, col: str | None = None, state_col: str | None = None,
                   county_col: str | None = None) -> pd.DataFrame:
    """Create a 5-char string `fips` column from one combined column or state+county parts."""
    df = df.copy()
    if col is not None:
        df["fips"] = df[col].map(zfill_fips)
    else:
        st = df[state_col].map(lambda v: str(int(float(v))).zfill(2) if pd.notna(v) else None)
        co = df[county_col].map(lambda v: str(int(float(v))).zfill(3) if pd.notna(v) else None)
        df["fips"] = [s + c if s and c else None for s, c in zip(st, co)]
    return df


def _log_ct(source: str, cols: list[str]) -> None:
    log = json.loads(CT_LOG.read_text()) if CT_LOG.exists() else {}
    log[source] = sorted(cols)
    CT_LOG.write_text(json.dumps(log, indent=2))


def apply_fips_fixes(df: pd.DataFrame, how: dict[str, str], source: str) -> pd.DataFrame:
    """Rename retired FIPS, convert old CT counties, drop out-of-scope rows, dedupe by fips."""
    df = df[df["fips"].notna()].copy()
    df["fips"] = df["fips"].replace(FIPS_RENAMES)
    df = df[~df["fips"].str[:2].isin(EXCLUDED_STATE_FIPS)]
    df = df[~df["fips"].str.endswith("000")]  # state / national totals

    has_old_ct = df["fips"].isin(CT_OLD_COUNTIES).any()
    has_new_ct = df["fips"].isin(CT_NEW_REGIONS).any()
    if has_old_ct and not has_new_ct:
        ct = df[df["fips"].isin(CT_OLD_COUNTIES)]
        rest = df[~df["fips"].str.startswith("09")]
        df = pd.concat([rest, ct_old_to_new(ct, how)], ignore_index=True)
        _log_ct(source, list(how))
    elif has_old_ct and has_new_ct:
        df = df[~df["fips"].isin(CT_OLD_COUNTIES)]

    agg = {}
    for c, h in how.items():
        agg[c] = {"sum": lambda s: s.sum(min_count=1), "mean": "mean", "max": "max", "first": "first"}[h]
    keep = ["fips", *how.keys()]
    out = df[keep].groupby("fips", as_index=False).agg(agg)
    return out


def ct_crosswalk() -> pd.DataFrame:
    """Overlay of 2020 CT counties with 2025 planning regions in EPSG:5070.

    Columns: old_fips, new_fips, overlap_km2, w_old (share of the old county inside the
    region), w_new (share of the region covered by the old county).
    """
    path = INTERIM / "_ct_crosswalk.parquet"
    if path.exists():
        return pd.read_parquet(path)
    from .counties import load_counties_2020, load_counties
    import geopandas as gpd

    old = load_counties_2020()
    old = old[old["fips"].isin(CT_OLD_COUNTIES)].to_crs(5070)[["fips", "geometry"]]
    new = load_counties()
    new = new[new["fips"].isin(CT_NEW_REGIONS)].to_crs(5070)[["fips", "geometry"]]
    old["old_area"] = old.area
    new["new_area"] = new.area
    ov = gpd.overlay(old.rename(columns={"fips": "old_fips"}), new.rename(columns={"fips": "new_fips"}),
                     how="intersection", keep_geom_type=True)
    ov["overlap"] = ov.area
    ov = ov[ov["overlap"] > 1e6]  # drop slivers < 1 km2 from boundary generalisation
    ov["w_old"] = ov["overlap"] / ov["old_area"]
    ov["w_new"] = ov.groupby("new_fips")["overlap"].transform(lambda s: s / s.sum())
    out = pd.DataFrame({
        "old_fips": ov["old_fips"], "new_fips": ov["new_fips"],
        "overlap_km2": ov["overlap"] / 1e6, "w_old": ov["w_old"], "w_new": ov["w_new"],
    }).reset_index(drop=True)
    out.to_parquet(path, index=False)
    return out


def ct_old_to_new(ct: pd.DataFrame, how: dict[str, str]) -> pd.DataFrame:
    xw = ct_crosswalk()
    m = xw.merge(ct, left_on="old_fips", right_on="fips", how="inner")
    rows = []
    for new, g in m.groupby("new_fips"):
        rec = {"fips": new}
        for c, h in how.items():
            v = pd.to_numeric(g[c], errors="coerce") if h in ("sum", "mean") else g[c]
            if h == "sum":
                rec[c] = (v * g["w_old"]).sum(min_count=1)
            elif h == "mean":
                ok = v.notna()
                rec[c] = np.average(v[ok], weights=g["w_new"][ok]) if ok.any() else np.nan
            else:
                rec[c] = g.loc[g["w_new"].idxmax(), c]
        rows.append(rec)
    return pd.DataFrame(rows)
