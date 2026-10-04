"""Merge every data/interim/*.parquet onto the county base -> data/processed/county_features.{parquet,csv}.

Left joins only, no imputation. Row count and fips uniqueness are asserted after every merge. Columns in the
data dictionary whose source is BLOCKED/FAILED (no interim file) are added as all-NaN so the schema is stable.
"""
import json

import numpy as np
import pandas as pd
import yaml

from src.build.feature_specs import PILLARS, S
from src.common.io import INTERIM, PROCESSED, SOURCES_YAML, STATUS_JSON

BASE = "meta_base.parquet"


def merge_all() -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_parquet(INTERIM / BASE)
    n = len(df)
    assert n == 3109 and df["fips"].is_unique and df["fips"].str.fullmatch(r"\d{5}").all()
    log = []
    for f in sorted(INTERIM.glob("[!_]*.parquet")):
        if f.name == BASE:
            continue
        part = pd.read_parquet(f)
        assert part["fips"].is_unique, f"duplicate fips in {f.name}"
        dup = [c for c in part.columns if c != "fips" and c in df.columns]
        assert not dup, f"{f.name} repeats columns {dup}"
        df = df.merge(part, on="fips", how="left")
        assert len(df) == n and df["fips"].is_unique, f"row count/uniqueness broken after {f.name}"
        log.append(f"{f.name}: +{part.shape[1] - 1} cols, {part['fips'].isin(df['fips']).sum()} matched rows")
    return df, log


def build() -> pd.DataFrame:
    df, log = merge_all()
    df["prm_pop_density_km2"] = df["meta_pop_2023"] / df["meta_land_area_km2"].replace(0, np.nan)

    missing = [c for c in S if c not in df.columns]
    for c in missing:
        df[c] = np.nan
    extra = [c for c in df.columns if c not in S]
    if extra:
        raise ValueError(f"columns without a data dictionary entry: {extra}")
    df = df[list(S)]

    for c in df.columns:
        if df[c].dtype == object and c not in ("fips",):
            num = pd.to_numeric(df[c], errors="coerce")
            if num.notna().sum() == df[c].notna().sum() and df[c].notna().any():
                df[c] = num
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED / "county_features.parquet", index=False)
    df.to_csv(PROCESSED / "county_features.csv", index=False)
    write_dictionary(missing)
    print("\n".join(log))
    print(f"[build] county_features: {df.shape[0]} rows x {df.shape[1]} cols; all-NaN (blocked) columns: {missing}")
    return df


def write_dictionary(missing: list[str]) -> None:
    src = yaml.safe_load(SOURCES_YAML.read_text()) or {}
    status = json.loads(STATUS_JSON.read_text()) if STATUS_JSON.exists() else {}
    rows = []
    for col, (desc, unit, key, join, higher, notes) in S.items():
        meta = src.get(key, {})
        st = status.get(key, {}).get("status")
        if col in missing:
            notes = f"ALL NaN: source {key} status {st or 'not run'}. {notes}".strip()
        rows.append({
            "column": col,
            "pillar": PILLARS.get(col.split("_")[0], "key"),
            "description": desc,
            "unit": unit,
            "source": meta.get("name", key),
            "vintage": meta.get("vintage", ""),
            "join_method": join,
            "higher_is": higher,
            "notes": notes,
        })
    pd.DataFrame(rows).to_csv(PROCESSED / "data_dictionary.csv", index=False)


if __name__ == "__main__":
    build()
