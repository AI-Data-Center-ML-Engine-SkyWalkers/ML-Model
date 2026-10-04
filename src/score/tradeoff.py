"""Sacrifice-one-criterion rankings and the 7-pillar Pareto front."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.score.score import geometric_mean, pillar_list, weight_vector


def sacrifice(
    ranked: pd.DataFrame,
    pillars: pd.DataFrame,
    cfg: dict,
    drop: str,
    floor_pct: float | None = None,
    weights: dict | None = None,
) -> pd.DataFrame:
    """Drop one pillar, keep counties at/above the percentile floor on every other, re-rank."""
    cols = [p for p in pillar_list(cfg) if p != drop]
    if not cols:
        raise ValueError("cannot sacrifice every pillar")
    q = float(cfg.get("tradeoff", {}).get("floor_pct", 50) if floor_pct is None else floor_pct)
    floors = pillars[cols].quantile(q / 100.0)
    ok = (pillars[cols] >= floors).all(axis=1)
    w = weight_vector(cfg, weights)[cols]
    w = w / w.sum()
    scores = geometric_mean(pillars.loc[ok, cols], w, floor=float(cfg.get("geo_mean_floor", 0.01)))
    out = ranked.iloc[np.flatnonzero(ok.to_numpy())].copy()
    out["final_score"] = scores.to_numpy()
    out["sacrificed"] = drop
    out["floor_pct"] = q
    out["n_eligible"] = int(ok.sum())
    out = out.sort_values("final_score", ascending=False).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    return out


def pareto_front(ranked: pd.DataFrame, pillars: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Non-dominated counties across the 7 pillars (higher is better)."""
    cols = pillar_list(cfg)
    p = pillars[cols].to_numpy(dtype=float)
    p = np.nan_to_num(p, nan=-np.inf)
    ge = p[:, None, :] >= p[None, :, :]
    gt = p[:, None, :] > p[None, :, :]
    dominates = ge.all(axis=2) & gt.any(axis=2)
    n_dominates = dominates.sum(axis=1)
    n_dominated_by = dominates.sum(axis=0)
    keep = n_dominated_by == 0
    out = ranked.iloc[np.flatnonzero(keep)].copy()
    out["n_dominates"] = n_dominates[keep]
    out = out.sort_values(["n_dominates", "final_score"], ascending=[False, False]).reset_index(drop=True)
    print(f"[tradeoff] Pareto front: {int(keep.sum())} of {len(ranked)} counties")
    return out
