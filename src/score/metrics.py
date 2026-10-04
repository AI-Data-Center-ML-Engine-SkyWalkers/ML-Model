"""County-level metrics in real units for one reference campus."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.common.io import PROCESSED, ROOT
from src.score.score import OUTPUTS, apply_manual_adjustments, load_config

TRADEOFF_CONFIG = ROOT / "config" / "tradeoff.yaml"
FEATURES_PATH = PROCESSED / "county_features.parquet"
HOURS_PER_YEAR = 8760.0

RAW_COLS = [
    "fips",
    "haz_cdd_annual",
    "crb_lrmer_2035_kg_mwh",
    "crb_grid_co2_kg_mwh",
    "wtr_grid_water_l_kwh",
    "wtr_bws_2050_score",
    "pwr_ind_price_cents_kwh",
    "pwr_time_to_power_yrs",
]
PILLAR_COLS = ["power", "carbon", "water", "permission", "hazard", "land", "cobenefit"]
RANK_COLS = ["fips", "county", "state", "final_score", "flag_veto", *PILLAR_COLS]


def load_tradeoff_config(path: Path | None = None) -> dict:
    return yaml.safe_load((path or TRADEOFF_CONFIG).read_text())


def metric_names(tcfg: dict | None = None) -> list[str]:
    cfg = tcfg if tcfg is not None else load_tradeoff_config()
    return list(cfg["metrics"])


def metric_meta(name: str, tcfg: dict | None = None) -> dict:
    cfg = tcfg if tcfg is not None else load_tradeoff_config()
    if name not in cfg["metrics"]:
        raise KeyError(f"unknown metric: {name}")
    return cfg["metrics"][name]


def better_is_lower(name: str, tcfg: dict | None = None) -> bool:
    return metric_meta(name, tcfg).get("better", "lower") == "lower"


def it_energy_mwh(campus: dict) -> float:
    return float(campus["it_mw"]) * HOURS_PER_YEAR * float(campus["load_factor"])


def _capped_linear(cdd: pd.Series, spec: dict) -> pd.Series:
    raw = float(spec["base"]) + float(spec["per_cdd"]) * pd.to_numeric(cdd, errors="coerce")
    return np.minimum(raw, float(spec["max"]))


def add_campus_metrics(df: pd.DataFrame, tcfg: dict) -> pd.DataFrame:
    """Add real-unit campus metrics. `df` must already have the raw feature columns."""
    out = df.copy()
    campus = tcfg["campus"]
    it_mwh = it_energy_mwh(campus)
    cdd = out["haz_cdd_annual"]
    out["pue"] = _capped_linear(cdd, campus["pue"])
    out["wue"] = _capped_linear(cdd, campus["wue_l_per_kwh_it"])
    out["facility_mwh"] = it_mwh * out["pue"]
    out["co2_t"] = out["facility_mwh"] * pd.to_numeric(out["crb_lrmer_2035_kg_mwh"], errors="coerce") / 1000.0
    out["co2_avg_grid_t"] = (
        out["facility_mwh"] * pd.to_numeric(out["crb_grid_co2_kg_mwh"], errors="coerce") / 1000.0
    )
    out["water_ml"] = (
        it_mwh * 1000.0 * out["wue"]
        + out["facility_mwh"] * 1000.0 * pd.to_numeric(out["wtr_grid_water_l_kwh"], errors="coerce")
    ) / 1e6
    out["water_stress_2050"] = pd.to_numeric(out["wtr_bws_2050_score"], errors="coerce")
    out["energy_cost_musd"] = (
        out["facility_mwh"] * pd.to_numeric(out["pwr_ind_price_cents_kwh"], errors="coerce") * 1e-5
    )
    out["time_to_power_yrs"] = pd.to_numeric(out["pwr_time_to_power_yrs"], errors="coerce")
    return out


def candidates_from_rankings(ranked: pd.DataFrame) -> pd.DataFrame:
    """Surviving, non-vetoed counties. Hard exclusions are already applied in rankings."""
    out = ranked.copy()
    out["fips"] = out["fips"].astype(str).str.zfill(5)
    keep = out["flag_veto"].fillna(0).astype(int) == 0
    return out.loc[keep, [c for c in RANK_COLS if c in out.columns]].reset_index(drop=True)


def build_metrics(
    tcfg: dict | None = None,
    scoring_cfg: dict | None = None,
    features: pd.DataFrame | None = None,
    ranked: pd.DataFrame | None = None,
    robustness: pd.DataFrame | None = None,
) -> pd.DataFrame:
    tcfg = tcfg if tcfg is not None else load_tradeoff_config()
    scoring_cfg = scoring_cfg if scoring_cfg is not None else load_config()
    if features is None:
        features = pd.read_parquet(FEATURES_PATH)
    if ranked is None:
        ranked = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"fips": str})
    if robustness is None:
        robustness = pd.read_csv(OUTPUTS / "robustness.csv", dtype={"fips": str})

    feat = features.copy()
    feat["fips"] = feat["fips"].astype(str).str.zfill(5)
    feat = apply_manual_adjustments(feat, scoring_cfg)

    cand = candidates_from_rankings(ranked)
    raw = feat[[c for c in RAW_COLS if c in feat.columns]].copy()
    df = cand.merge(raw, on="fips", how="left")
    df = add_campus_metrics(df, tcfg)
    df["score"] = pd.to_numeric(df["final_score"], errors="coerce")

    rob = robustness.copy()
    rob["fips"] = rob["fips"].astype(str).str.zfill(5)
    if "pct_top10_nudged" in rob.columns:
        df = df.merge(rob[["fips", "pct_top10_nudged"]], on="fips", how="left")
    else:
        df["pct_top10_nudged"] = np.nan

    cols = ["fips", "county", "state", *metric_names(tcfg), "pct_top10_nudged"]
    return df[cols]


def metrics_summary(df: pd.DataFrame, tcfg: dict | None = None) -> pd.DataFrame:
    tcfg = tcfg if tcfg is not None else load_tradeoff_config()
    ref = str(tcfg["reference_fips"]).zfill(5)
    names = metric_names(tcfg)
    ref_row = df.loc[df["fips"] == ref]
    rows = []
    for name in names:
        s = pd.to_numeric(df[name], errors="coerce")
        rec = {
            "metric": name,
            "unit": metric_meta(name, tcfg)["unit"],
            "n": int(s.notna().sum()),
            "n_nan": int(s.isna().sum()),
            "min": float(s.min()) if s.notna().any() else np.nan,
            "median": float(s.median()) if s.notna().any() else np.nan,
            "max": float(s.max()) if s.notna().any() else np.nan,
            "cowlitz": float(ref_row[name].iloc[0]) if len(ref_row) and pd.notna(ref_row[name].iloc[0]) else np.nan,
        }
        rows.append(rec)
    return pd.DataFrame(rows)


def write_metrics(df: pd.DataFrame | None = None, path: Path | None = None) -> pd.DataFrame:
    out = df if df is not None else build_metrics()
    dest = path or (OUTPUTS / "metrics.parquet")
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(dest, index=False)
    print(f"[metrics] {dest.relative_to(ROOT)}: {len(out):,} candidates, {len(out.columns)} cols")
    return out


def main() -> None:
    tcfg = load_tradeoff_config()
    df = write_metrics()
    summary = metrics_summary(df, tcfg)
    print("\n=== Metrics among candidates (min / median / max) + Cowlitz ===")
    print(summary.to_string(index=False, float_format=lambda v: f"{v:g}"))


if __name__ == "__main__":
    main()
