"""Pillar scores stay fixed; only weights are resampled. Reads outputs/pillars.parquet."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.score.score import OUTPUTS, geometric_mean, pillar_list, veto_matrix, weight_vector


def _sample_weights(n: int, alpha: np.ndarray, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).dirichlet(alpha, size=n)


def _ranks(scores: np.ndarray, veto: np.ndarray) -> np.ndarray:
    key = scores.copy()
    key[veto] -= 10.0
    return np.argsort(np.argsort(-key, axis=0), axis=0) + 1


def run_robustness(cfg: dict, path=None, df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = pd.read_parquet(path or (OUTPUTS / "pillars.parquet"))
    if "excluded" in df.columns:
        df = df[df["excluded"] == 0].copy().reset_index(drop=True)
    else:
        df = df.copy().reset_index(drop=True)
    rcfg = cfg["robustness"]
    seed = int(rcfg.get("seed", 42))
    n = int(rcfg.get("n_samples", 1000))
    scale = float(rcfg.get("nudged_alpha_scale", 50))
    floor = float(cfg.get("geo_mean_floor", 0.01))
    cols = pillar_list(cfg)
    P = df[cols].to_numpy(dtype=float)
    base = weight_vector(cfg).to_numpy()

    w_nudged = _sample_weights(n, scale * base, seed)
    w_agnostic = _sample_weights(n, np.ones(len(base)), seed + 1)

    p_safe = np.maximum(np.nan_to_num(P, nan=floor), floor)
    s_nudged = np.exp(np.log(p_safe) @ w_nudged.T)
    s_agnostic = np.exp(np.log(p_safe) @ w_agnostic.T)
    r_nudged = _ranks(s_nudged, veto_matrix(P, w_nudged, cols, cfg))
    r_agnostic = _ranks(s_agnostic, veto_matrix(P, w_agnostic, cols, cfg))

    out = df[["fips", "county", "state"]].copy()
    out["pct_top10_nudged"] = 100.0 * (r_nudged <= 10).mean(axis=1)
    out["pct_top10_agnostic"] = 100.0 * (r_agnostic <= 10).mean(axis=1)
    out["median_rank_nudged"] = np.median(r_nudged, axis=1)
    out["rank_p10"] = np.percentile(r_nudged, 10, axis=1)
    out["rank_p90"] = np.percentile(r_nudged, 90, axis=1)

    print("\n[robustness] highest pct_top10_nudged:")
    show = out.sort_values("pct_top10_nudged", ascending=False).head(10)
    print(show[["county", "state", "pct_top10_nudged", "pct_top10_agnostic",
                "median_rank_nudged"]].to_string(index=False, float_format=lambda v: f"{v:.1f}"))

    durable = out[out["pct_top10_agnostic"] > 50].sort_values("pct_top10_agnostic", ascending=False)
    print(f"\n[robustness] pct_top10_agnostic > 50% ({len(durable)} counties):")
    if durable.empty:
        print("  (none)")
    else:
        print(durable[["county", "state", "pct_top10_agnostic", "pct_top10_nudged"]]
              .to_string(index=False, float_format=lambda v: f"{v:.1f}"))
    return out


def score_with_weights(pillars: pd.DataFrame, cfg: dict, weights: dict, floor: float | None = None) -> pd.Series:
    w = weight_vector(cfg, weights)
    return geometric_mean(pillars, w, floor=float(cfg.get("geo_mean_floor", 0.01) if floor is None else floor))
