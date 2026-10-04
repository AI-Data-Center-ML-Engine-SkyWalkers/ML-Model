"""Constraint / relax trade-offs on real-unit county metrics.

`sacrifice` / `pareto_front` stay so the existing Streamlit home page keeps working.
The new engine is solve / sweep / pareto2 / compare.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.common.io import ROOT
from src.score.metrics import (
    better_is_lower,
    build_metrics,
    load_tradeoff_config,
    metric_meta,
    metric_names,
    metrics_summary,
    write_metrics,
)
from src.score.score import OUTPUTS, geometric_mean, load_config, pillar_list, weight_vector

Constraint = tuple[str, str, float]
OPS = {
    "<=": lambda s, v: s.notna() & (s <= v),
    "<": lambda s, v: s.notna() & (s < v),
    ">=": lambda s, v: s.notna() & (s >= v),
    ">": lambda s, v: s.notna() & (s > v),
    "==": lambda s, v: s.notna() & (s == v),
}

HIGHLIGHT = ["energy_cost_musd", "time_to_power_yrs", "water_ml", "co2_t", "score"]
_UNSET = object()


def _constraints_with_min_score(
    objective: str,
    constraints: list[Constraint] | None,
    min_score,
    tcfg: dict,
) -> list[Constraint]:
    cons = list(constraints or [])
    if objective == "score":
        return cons
    floor = tcfg.get("min_score", 0.60) if min_score is _UNSET else min_score
    if floor is None:
        return cons
    if any(c[0] == "score" for c in cons):
        return cons
    return cons + [("score", ">=", float(floor))]


def load_metrics(path: Path | None = None, rebuild: bool = False) -> pd.DataFrame:
    dest = path or (OUTPUTS / "metrics.parquet")
    if rebuild or not dest.exists():
        return write_metrics(path=dest)
    df = pd.read_parquet(dest)
    df["fips"] = df["fips"].astype(str).str.zfill(5)
    return df


def _frame(metrics: pd.DataFrame | None) -> pd.DataFrame:
    df = metrics if metrics is not None else load_metrics()
    out = df.copy()
    out["fips"] = out["fips"].astype(str).str.zfill(5)
    return out


def _constraint_mask(df: pd.DataFrame, constraints: list[Constraint] | None) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for col, op, val in constraints or []:
        if col not in df.columns:
            raise KeyError(f"unknown constraint metric: {col}")
        if op not in OPS:
            raise ValueError(f"unsupported constraint op: {op}")
        mask = mask & OPS[op](pd.to_numeric(df[col], errors="coerce"), val)
    return mask


def _objective_values(
    df: pd.DataFrame,
    objective: str,
    ignore_pillars: list[str] | None,
    weights: dict | None,
    scoring_cfg: dict,
) -> pd.Series:
    if objective != "score":
        if objective not in df.columns:
            raise KeyError(f"unknown objective: {objective}")
        return pd.to_numeric(df[objective], errors="coerce")
    drop = list(ignore_pillars or [])
    cols = [p for p in pillar_list(scoring_cfg) if p in df.columns and p not in drop]
    if not cols:
        raise ValueError("cannot ignore every pillar")
    w = weight_vector(scoring_cfg, weights)[cols]
    w = w / w.sum()
    floor = float(scoring_cfg.get("geo_mean_floor", 0.01))
    return geometric_mean(df[cols], w, floor=floor)


def _sort_idx(values: pd.Series, fips: pd.Series, minimize: bool) -> np.ndarray:
    val = values.to_numpy(dtype=float)
    key = np.where(np.isfinite(val), val, np.inf if minimize else -np.inf)
    signed = key if minimize else -key
    return np.lexsort((fips.to_numpy(), signed))


def compare(best: pd.Series, ref: pd.Series, tcfg: dict | None = None) -> pd.DataFrame:
    tcfg = tcfg if tcfg is not None else load_tradeoff_config()
    rows = []
    for name in metric_names(tcfg):
        meta = metric_meta(name, tcfg)
        b = pd.to_numeric(pd.Series([best.get(name)]), errors="coerce").iloc[0]
        r = pd.to_numeric(pd.Series([ref.get(name)]), errors="coerce").iloc[0]
        delta = b - r if np.isfinite(b) and np.isfinite(r) else np.nan
        if not np.isfinite(delta):
            pct, verdict = np.nan, "n/a"
        elif abs(delta) < 1e-9 or (abs(r) < 1e-3 and abs(b) < 1e-3):
            pct = 0.0 if abs(r) < 1e-12 else 100.0 * delta / abs(r)
            verdict = "same"
        elif abs(r) < 1e-12:
            pct = np.nan
            verdict = "better" if (delta < 0) == (meta["better"] == "lower") else "worse"
        else:
            pct = 100.0 * delta / abs(r)
            verdict = "better" if ((delta < 0) == (meta["better"] == "lower")) else "worse"
        rows.append({
            "metric": name,
            "label": meta["label"],
            "unit": meta["unit"],
            "better": meta["better"],
            "best": b,
            "reference": r,
            "abs_change": delta,
            "pct_change": pct,
            "change": verdict,
        })
    return pd.DataFrame(rows)


def _binding(df: pd.DataFrame, constraints: list[Constraint]) -> dict | None:
    if not constraints:
        return None
    n = len(df)
    scored = []
    for i, (col, op, val) in enumerate(constraints):
        removed = int((~_constraint_mask(df, [(col, op, val)])).sum())
        scored.append((removed, i, col, op, val))
    scored.sort(key=lambda x: (-x[0], x[1]))
    removed, i, col, op, val = scored[0]
    others = [c for j, c in enumerate(constraints) if j != i]
    other_ok = df.loc[_constraint_mask(df, others)]
    pool = other_ok if len(other_ok) else df
    series = pd.to_numeric(pool[col], errors="coerce")
    if op in ("<=", "<"):
        loose = float(series.min()) if series.notna().any() else np.nan
    else:
        loose = float(series.max()) if series.notna().any() else np.nan
    return {
        "metric": col,
        "op": op,
        "asked": val,
        "removes": removed,
        "n_candidates": n,
        "loosest_feasible": loose,
        "n_other_feasible": int(len(other_ok)),
    }


def _best_record(row: pd.Series) -> dict:
    return {k: (v.item() if isinstance(v, (np.generic,)) else v) for k, v in row.items()}


def _energy_cost_in_play(objective: str, constraints: list[Constraint] | None) -> bool:
    return objective == "energy_cost_musd" or any(c[0] == "energy_cost_musd" for c in (constraints or []))


def _drop_nan_energy_cost(df: pd.DataFrame, objective: str, constraints: list[Constraint] | None) -> tuple[pd.DataFrame, int]:
    if "energy_cost_musd" not in df.columns or not _energy_cost_in_play(objective, constraints):
        return df, 0
    ok = pd.to_numeric(df["energy_cost_musd"], errors="coerce").notna()
    n = int((~ok).sum())
    return (df.loc[ok].copy(), n) if n else (df, 0)


def solve(
    objective: str = "score",
    constraints: list[Constraint] | None = None,
    ignore_pillars: list[str] | None = None,
    weights: dict | None = None,
    top_n: int = 10,
    metrics: pd.DataFrame | None = None,
    tcfg: dict | None = None,
    scoring_cfg: dict | None = None,
    min_score=_UNSET,
) -> dict:
    tcfg = tcfg if tcfg is not None else load_tradeoff_config()
    scoring_cfg = scoring_cfg if scoring_cfg is not None else load_config()
    constraints = _constraints_with_min_score(objective, constraints, min_score, tcfg)
    df = _frame(metrics)
    df, n_dropped = _drop_nan_energy_cost(df, objective, constraints)
    ref_fips = str(tcfg["reference_fips"]).zfill(5)
    ref_hit = df["fips"] == ref_fips
    ref = df.loc[ref_hit].iloc[0] if ref_hit.any() else None

    mask = _constraint_mask(df, constraints)
    feasible = df.loc[mask].copy()
    n_feasible = int(len(feasible))
    empty = {
        "best": None,
        "top": feasible,
        "n_feasible": 0,
        "compare": None,
        "binding": _binding(df, list(constraints or [])),
        "objective": objective,
        "objective_value": None,
        "n_dropped_energy_cost": n_dropped,
    }
    if n_feasible == 0:
        return empty

    obj = _objective_values(feasible, objective, ignore_pillars, weights, scoring_cfg)
    feasible = feasible.assign(objective_value=obj.to_numpy())
    minimize = objective != "score" and better_is_lower(objective, tcfg)
    order = _sort_idx(feasible["objective_value"], feasible["fips"], minimize)
    ranked = feasible.iloc[order].reset_index(drop=True)
    ranked.insert(0, "pick_rank", np.arange(1, len(ranked) + 1))
    best = ranked.iloc[0]
    return {
        "best": _best_record(best),
        "top": ranked.head(int(top_n)).copy(),
        "n_feasible": n_feasible,
        "compare": compare(best, ref, tcfg) if ref is not None else None,
        "binding": None,
        "objective": objective,
        "objective_value": float(best["objective_value"]) if pd.notna(best["objective_value"]) else np.nan,
        "n_dropped_energy_cost": n_dropped,
    }


def sweep(
    metric: str,
    values,
    objective: str = "score",
    constraints: list[Constraint] | None = None,
    ignore_pillars: list[str] | None = None,
    weights: dict | None = None,
    metrics: pd.DataFrame | None = None,
    tcfg: dict | None = None,
    scoring_cfg: dict | None = None,
    min_score=_UNSET,
) -> pd.DataFrame:
    tcfg = tcfg if tcfg is not None else load_tradeoff_config()
    scoring_cfg = scoring_cfg if scoring_cfg is not None else load_config()
    df = _frame(metrics)
    op = "<=" if better_is_lower(metric, tcfg) else ">="
    extra = list(constraints or [])
    names = metric_names(tcfg)
    rows = []
    for v in list(values):
        result = solve(
            objective, extra + [(metric, op, float(v))], ignore_pillars, weights,
            top_n=1, metrics=df, tcfg=tcfg, scoring_cfg=scoring_cfg,
            min_score=min_score,
        )
        rec = {"limit": float(v), "n_feasible": result["n_feasible"], "fips": None, "county": None, "state": None}
        if result["best"] is not None:
            best = result["best"]
            rec["fips"] = best["fips"]
            rec["county"] = best["county"]
            rec["state"] = best["state"]
            rec["objective_value"] = result["objective_value"]
            for name in names:
                rec[name] = best.get(name)
        rows.append(rec)
    out = pd.DataFrame(rows)
    prev = out["fips"].shift(1)
    out["best_changed"] = out["fips"].notna() & prev.notna() & (out["fips"] != prev)
    return out


def pareto2(
    metric_x: str,
    metric_y: str,
    metrics: pd.DataFrame | None = None,
    tcfg: dict | None = None,
) -> pd.DataFrame:
    tcfg = tcfg if tcfg is not None else load_tradeoff_config()
    df = _frame(metrics)
    x = pd.to_numeric(df[metric_x], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(df[metric_y], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    work = df.loc[ok].copy().reset_index(drop=True)
    px = pd.to_numeric(work[metric_x], errors="coerce").to_numpy(dtype=float)
    py = pd.to_numeric(work[metric_y], errors="coerce").to_numpy(dtype=float)
    if better_is_lower(metric_x, tcfg):
        px = -px
    if better_is_lower(metric_y, tcfg):
        py = -py
    p = np.column_stack([px, py])
    ge = p[:, None, :] >= p[None, :, :]
    gt = p[:, None, :] > p[None, :, :]
    dominates = ge.all(axis=2) & gt.any(axis=2)
    keep = dominates.sum(axis=0) == 0
    front = work.loc[keep].copy()
    front = front.sort_values(metric_x, ascending=True).reset_index(drop=True)
    front["pareto_rank"] = np.arange(1, len(front) + 1)
    return front


def nearest_front(ref: pd.Series, front: pd.DataFrame, metric_x: str, metric_y: str, pool: pd.DataFrame) -> pd.Series | None:
    if front.empty:
        return None
    rx, ry = float(ref[metric_x]), float(ref[metric_y])
    x = pd.to_numeric(front[metric_x], errors="coerce")
    y = pd.to_numeric(front[metric_y], errors="coerce")
    sx = float(pd.to_numeric(pool[metric_x], errors="coerce").max() - pd.to_numeric(pool[metric_x], errors="coerce").min()) or 1.0
    sy = float(pd.to_numeric(pool[metric_y], errors="coerce").max() - pd.to_numeric(pool[metric_y], errors="coerce").min()) or 1.0
    dist = np.sqrt(((x - rx) / sx) ** 2 + ((y - ry) / sy) ** 2)
    return front.iloc[int(dist.to_numpy().argmin())]


def summarize(result: dict, constraints: list[Constraint] | None = None, tcfg: dict | None = None) -> str:
    tcfg = tcfg if tcfg is not None else load_tradeoff_config()
    if result["n_feasible"] == 0:
        b = result.get("binding") or {}
        return (
            f"No county is feasible. {b.get('metric')} {b.get('op')} {b.get('asked')} "
            f"removes the most counties ({b.get('removes')} of {b.get('n_candidates')}); "
            f"the loosest value that admits one county is {b.get('loosest_feasible')}."
        )
    best = result["best"]
    name = f"{best['county']}, {best['state']}"
    bits = []
    for col, op, val in constraints or []:
        meta = metric_meta(col, tcfg)
        bits.append(f"{meta['label']} {op} {val:g} {meta['unit']}")
    head = f"Picks {name}"
    if bits:
        head = f"{'; '.join(bits)} picks {name}"
    cmp = result.get("compare")
    if cmp is None:
        return f"{head} ({result['n_feasible']:,} feasible)."
    deltas = []
    for _, row in cmp.iterrows():
        if row["metric"] not in HIGHLIGHT or row["change"] == "same":
            continue
        sign = "+" if row["abs_change"] > 0 else ""
        if row["metric"] == "energy_cost_musd":
            deltas.append(f"energy cost {sign}{row['abs_change']:.1f} $M/yr")
        elif row["metric"] == "time_to_power_yrs":
            deltas.append(f"grid wait {sign}{row['abs_change']:.1f} yrs")
        elif row["metric"] == "water_ml":
            deltas.append(f"water {row['pct_change']:+.0f}%")
        elif row["metric"] == "co2_t":
            deltas.append(f"CO2 {sign}{row['abs_change']:.0f} t/yr")
        elif row["metric"] == "score":
            deltas.append(f"score {row['abs_change']:+.3f}")
    tail = (", ".join(deltas) + " vs Cowlitz.") if deltas else "same as Cowlitz on cost, wait, water, CO2 and score."
    dropped = result.get("n_dropped_energy_cost") or 0
    extra = f" Dropped {dropped} counties with missing energy cost." if dropped else ""
    return f"{head}. {tail}{extra}"


def one_liner(result: dict, want: str, give: str) -> str:
    if result["n_feasible"] == 0:
        return summarize(result)
    best = result["best"]
    return f"To get {want}, you give up {give} — pick is {best['county']}, {best['state']}."


# ---------------------------------------------------------------------------
# Kept for app.py (home page "sacrifice a pillar")
# ---------------------------------------------------------------------------

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


def _fmt(v, digits=3) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "n/a"
    if abs(v) >= 100:
        return f"{v:,.1f}"
    return f"{v:.{digits}f}"


def _example_block(title: str, result: dict, line: str, tcfg: dict) -> list[str]:
    lines = [f"## {title}", "", f"**{line}**", ""]
    if result["n_feasible"] == 0:
        b = result["binding"]
        lines.append(
            f"No feasible county. Binding: `{b['metric']}` {b['op']} {b['asked']:g} "
            f"removes {b['removes']} of {b['n_candidates']}; loosest feasible value is "
            f"{b['loosest_feasible']:g}."
        )
        lines.append("")
        return lines
    best = result["best"]
    lines.append(
        f"Best: **{best['county']}, {best['state']}** (`{best['fips']}`). "
        f"{result['n_feasible']:,} feasible. Objective `{result['objective']}` = "
        f"{_fmt(result['objective_value'])}."
    )
    lines.append("")
    cmp = result["compare"]
    if cmp is not None:
        lines.append("| Metric | Best | Cowlitz | Change | Verdict |")
        lines.append("|---|---:|---:|---:|---|")
        for _, row in cmp.iterrows():
            chg = _fmt(row["abs_change"]) if pd.notna(row["abs_change"]) else "n/a"
            pct = f" ({row['pct_change']:+.1f}%)" if pd.notna(row["pct_change"]) else ""
            lines.append(
                f"| {row['label']} | {_fmt(row['best'])} | {_fmt(row['reference'])} "
                f"| {chg}{pct} | {row['change']} |"
            )
        lines.append("")
    top = result["top"]
    show = [c for c in ["pick_rank", "county", "state", "score", "co2_t", "energy_cost_musd",
                        "time_to_power_yrs", "water_ml", "hazard"] if c in top.columns]
    lines.append("Top picks:")
    lines.append("")
    lines.append("| " + " | ".join(show) + " |")
    lines.append("|" + "|".join("---" if c in ("county", "state") else "---:" for c in show) + "|")
    for _, row in top.iterrows():
        cells = []
        for c in show:
            v = row[c]
            cells.append(v if c in ("county", "state") else _fmt(v, 2 if c != "pick_rank" else 0))
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    lines.append("")
    return lines


def run_examples(metrics: pd.DataFrame | None = None, tcfg: dict | None = None) -> tuple[str, list[str]]:
    tcfg = tcfg if tcfg is not None else load_tradeoff_config()
    df = _frame(metrics)
    answers: list[str] = []
    md = [
        "# Trade-off examples",
        "",
        "One 100 MW campus (load factor 0.8). PUE and WUE are judgment assumptions that rise with "
        "cooling degree days. Energy cost is electricity only (no land or construction). "
        "Candidates are surviving, non-vetoed counties. Hard exclusions stay on.",
        "",
        f"Reference county: Cowlitz County, WA (`{tcfg['reference_fips']}`).",
        "",
    ]

    r1 = solve("score", [("co2_t", "<=", 25000)], metrics=df, tcfg=tcfg)
    cmp1 = r1["compare"]
    cost = cmp1.loc[cmp1["metric"] == "energy_cost_musd"].iloc[0] if cmp1 is not None else None
    wait = cmp1.loc[cmp1["metric"] == "time_to_power_yrs"].iloc[0] if cmp1 is not None else None
    if r1["best"] and r1["best"]["fips"] == str(tcfg["reference_fips"]).zfill(5):
        line1 = (
            "To keep CO2 under 25,000 t/yr, you give up nothing versus the unconstrained ranking: "
            "Cowlitz already clears the cap and stays first."
        )
    else:
        line1 = (
            f"To keep CO2 under 25,000 t/yr, you give up "
            f"{_fmt(cost['abs_change']) if cost is not None else '?'} $M/yr energy cost and "
            f"{_fmt(wait['abs_change']) if wait is not None else '?'} years of grid wait "
            f"relative to Cowlitz."
        )
    answers.append(line1)
    md.extend(_example_block("1. CO2 cap at 25,000 t/yr", r1, line1, tcfg))

    r2 = solve("co2_t", [("time_to_power_yrs", "<=", 4)], metrics=df, tcfg=tcfg)
    r2_open = solve("co2_t", [("time_to_power_yrs", "<=", 4)], metrics=df, tcfg=tcfg, min_score=None)
    if r2["best"] is None:
        line2 = summarize(r2, [("time_to_power_yrs", "<=", 4)], tcfg)
    else:
        b = r2["best"]
        ref = df.loc[df["fips"] == str(tcfg["reference_fips"]).zfill(5)].iloc[0]
        line2 = (
            f"To get the lowest long-run CO2 with power in ≤4 years, you give up "
            f"Cowlitz (wait {ref['time_to_power_yrs']:g} yrs, {ref['co2_t']:.0f} t/yr) and pick "
            f"{b['county']}, {b['state']} at {b['co2_t']:.0f} t/yr (score {b['score']:.3f})."
        )
    answers.append(line2)
    md.extend(_example_block("2. Lowest CO2 that still gets power in ≤4 years", r2, line2, tcfg))
    if r2_open["best"] is not None:
        o = r2_open["best"]
        md.append(
            f"*Without the floor:* {o['county']}, {o['state']} at {o['co2_t']:.0f} t/yr "
            f"(score {o['score']:.3f})."
        )
        md.append("")

    floors = np.linspace(0.8, 0.3, 8)
    sw3 = sweep("hazard", floors, objective="score", ignore_pillars=["hazard"], metrics=df, tcfg=tcfg)
    first3, last3 = sw3.iloc[0], sw3.iloc[-1]
    start = f"{first3['county']}, {first3['state']}" if pd.notna(first3.get("county")) else "no feasible county"
    end = f"{last3['county']}, {last3['state']}" if pd.notna(last3.get("county")) else "no feasible county"
    line3 = (
        f"To accept more climate risk (hazard floor {first3['limit']:.2f} → {last3['limit']:.2f}, "
        f"hazard ignored in the score), you give up {start} and move to {end}: "
        f"CO2 {_fmt(first3.get('co2_t'))} → {_fmt(last3.get('co2_t'))} t/yr, "
        f"energy ${_fmt(first3.get('energy_cost_musd'))}M → ${_fmt(last3.get('energy_cost_musd'))}M/yr, "
        f"score {_fmt(first3.get('score'))} → {_fmt(last3.get('score'))}."
    )
    answers.append(line3)
    md += [
        "## 3. Accept more climate risk (hazard floor 0.8 → 0.3)",
        "",
        f"**{line3}**",
        "",
        "Score ignores hazard; each row adds `hazard >= floor`. What extra risk buys:",
        "",
        "| Hazard floor | Feasible | Best | CO2 t/yr | Energy $M/yr | Score | Changed |",
        "|---:|---:|---|---:|---:|---:|---|",
    ]
    for _, row in sw3.iterrows():
        who = f"{row['county']}, {row['state']}" if pd.notna(row.get("county")) else "—"
        md.append(
            f"| {row['limit']:.2f} | {int(row['n_feasible'])} | {who} | "
            f"{_fmt(row.get('co2_t'))} | {_fmt(row.get('energy_cost_musd'))} | "
            f"{_fmt(row.get('score'))} | {'yes' if bool(row['best_changed']) else ''} |"
        )
    md.append("")

    r4 = solve("energy_cost_musd", [("water_stress_2050", "<=", 1)], metrics=df, tcfg=tcfg)
    r4_open = solve("energy_cost_musd", [("water_stress_2050", "<=", 1)], metrics=df, tcfg=tcfg, min_score=None)
    if r4["best"] is None:
        line4 = summarize(r4, [("water_stress_2050", "<=", 1)], tcfg)
    else:
        b = r4["best"]
        ref = df.loc[df["fips"] == str(tcfg["reference_fips"]).zfill(5)].iloc[0]
        dropped = r4.get("n_dropped_energy_cost") or 0
        drop_bit = f" Dropped {dropped} counties with missing energy cost." if dropped else ""
        line4 = (
            f"To get the cheapest electricity in a low-stress basin (BWS 2050 ≤ 1), you give up "
            f"{100 * (1 - b['score'] / ref['score']):.0f}% of overall score "
            f"and pick {b['county']}, {b['state']} — "
            f"energy cost ${b['energy_cost_musd']:.1f}M/yr vs Cowlitz ${ref['energy_cost_musd']:.1f}M/yr "
            f"(score {b['score']:.3f})."
            f"{drop_bit}"
        )
    answers.append(line4)
    md.extend(_example_block("4. Cheapest energy with low water stress", r4, line4, tcfg))
    if r4_open["best"] is not None:
        o = r4_open["best"]
        md.append(
            f"*Without the floor:* {o['county']}, {o['state']} at ${o['energy_cost_musd']:.1f}M/yr "
            f"(score {o['score']:.3f})."
        )
        md.append("")

    sw5 = sweep("time_to_power_yrs", [6, 5, 4], metrics=df, tcfg=tcfg)
    row6 = sw5.loc[sw5["limit"] == 6].iloc[0]
    row4 = sw5.loc[sw5["limit"] == 4].iloc[0]
    extra_co2 = float(row4["co2_t"] - row6["co2_t"]) if pd.notna(row4.get("co2_t")) and pd.notna(row6.get("co2_t")) else np.nan
    line5 = f"Power in 4 years costs {extra_co2:.0f} more tCO2/yr than power in 6 years."
    answers.append(line5)
    md += [
        "## 5. Faster power (wait ≤ 6, 5, 4 years)",
        "",
        f"**{line5}**",
        "",
        "How CO2, water and score change as you demand faster power:",
        "",
        "| Wait ≤ yrs | Feasible | Best | CO2 t/yr | Water ML | Score | Changed |",
        "|---:|---:|---|---:|---:|---:|---|",
    ]
    for _, row in sw5.iterrows():
        who = f"{row['county']}, {row['state']}" if pd.notna(row.get("county")) else "—"
        md.append(
            f"| {row['limit']:g} | {int(row['n_feasible'])} | {who} | "
            f"{_fmt(row.get('co2_t'))} | {_fmt(row.get('water_ml'))} | "
            f"{_fmt(row.get('score'))} | {'yes' if bool(row['best_changed']) else ''} |"
        )
    md.append("")
    md.append(
        "Time to power is a judgment value (6 yrs) for NorthernGrid_West and the national 4-yr default "
        "for most other utilities, including Linn IA. Treat the carbon cost of speed as indicative."
    )
    md.append("")

    floor = tcfg.get("min_score", 0.60)
    front_open = pareto2("co2_t", "energy_cost_musd", metrics=df, tcfg=tcfg)
    front_df = df if floor is None else df.loc[pd.to_numeric(df["score"], errors="coerce") >= float(floor)]
    front = pareto2("co2_t", "energy_cost_musd", metrics=front_df, tcfg=tcfg)
    ref = df.loc[df["fips"] == str(tcfg["reference_fips"]).zfill(5)].iloc[0]
    on_front = bool((front["fips"] == ref["fips"]).any())
    near = nearest_front(ref, front, "co2_t", "energy_cost_musd", df)
    if on_front:
        line6 = (
            f"To move along the CO2–energy-cost front ({len(front)} counties), Cowlitz is already on it; "
            "you give up one of those two to improve the other."
        )
    else:
        line6 = (
            f"To sit on the CO2–energy-cost front ({len(front)} counties), you give up Cowlitz "
            f"(not on the front). Nearest front county: {near['county']}, {near['state']} "
            f"(CO2 {near['co2_t']:.0f} t/yr, energy ${near['energy_cost_musd']:.1f}M/yr)."
        )
    answers.append(line6)
    md += [
        "## 6. Pareto: CO2 vs energy cost",
        "",
        f"**{line6}**",
        "",
        (
            f"Front size: **{len(front)}** of {len(df):,} candidates. "
            f"Cowlitz is {'on' if on_front else 'not on'} the front"
            + ("" if on_front else f"; nearest is {near['county']}, {near['state']} (`{near['fips']}`)")
            + "."
        ),
        "",
        "| County | State | CO2 t/yr | Energy $M/yr | Score |",
        "|---|---|---:|---:|---:|",
    ]
    for _, row in front.iterrows():
        mark = " ← Cowlitz" if row["fips"] == ref["fips"] else ""
        md.append(
            f"| {row['county']}{mark} | {row['state']} | {_fmt(row['co2_t'])} | "
            f"{_fmt(row['energy_cost_musd'])} | {_fmt(row['score'])} |"
        )
    md.append("")
    if floor is not None:
        open_names = ", ".join(f"{r.county} {r.state} ({r.score:.3f})" for r in front_open.itertuples())
        md.append(
            f"*Without the floor:* front has {len(front_open)} counties: {open_names}."
        )
        md.append("")
    return "\n".join(md) + "\n", answers


def suspicious_notes(df: pd.DataFrame, sweep_df: pd.DataFrame | None, tcfg: dict) -> list[str]:
    notes = []
    for name in metric_names(tcfg):
        n = int(pd.to_numeric(df[name], errors="coerce").isna().sum())
        if n:
            notes.append(f"{name}: {n} NaN of {len(df)} candidates.")
    if sweep_df is not None and len(sweep_df) and int(sweep_df["fips"].nunique()) <= 1:
        who = sweep_df.iloc[0]
        if pd.notna(who.get("county")):
            notes.append(f"Sweep winner never changes ({who['county']}, {who['state']}).")
    ref = df.loc[df["fips"] == str(tcfg["reference_fips"]).zfill(5)]
    if len(ref):
        r = ref.iloc[0]
        if r["co2_t"] < df["co2_t"].quantile(0.05) and r["co2_avg_grid_t"] > df["co2_avg_grid_t"].median():
            notes.append(
                "Cowlitz long-run marginal CO2 is near the national minimum, but today's average-grid CO2 is above the candidate median. "
                "The two carbon metrics are answering different questions; do not treat co2_avg_grid_t as the decision metric."
            )
    notes.append(
        "NorthernGrid_West (WA/OR) counties share TTP = 6 years and large-load price 7.75 ¢/kWh. "
        "A 4-year power constraint excludes that whole Cambium region."
    )
    n_nan = int(pd.to_numeric(df["energy_cost_musd"], errors="coerce").isna().sum()) if "energy_cost_musd" in df.columns else 0
    if n_nan:
        notes.append(
            f"{n_nan} candidates have NaN energy_cost_musd (missing industrial price). "
            "They stay in the pool unless energy cost is the objective or a constraint."
        )
    front = pareto2("co2_t", "energy_cost_musd", metrics=df, tcfg=tcfg)
    if len(front) <= 5:
        who = ", ".join(f"{r.county} {r.state}" for r in front.itertuples())
        notes.append(
            f"The CO2–energy-cost Pareto front is only {len(front)} counties ({who})."
        )
    return notes or ["None."]


def main() -> None:
    tcfg = load_tradeoff_config()
    df = write_metrics()
    summary = metrics_summary(df, tcfg)
    md, answers = run_examples(df, tcfg)
    dest = OUTPUTS / "tradeoff_examples.md"
    dest.write_text(md)
    print(f"[tradeoff] wrote {dest.relative_to(ROOT)}")

    sw = sweep("time_to_power_yrs", [6, 5, 4], metrics=df, tcfg=tcfg)
    notes = suspicious_notes(df, sw, tcfg)

    print("\n=== Metrics among candidates (min / median / max) + Cowlitz ===")
    print(summary.to_string(index=False, float_format=lambda v: f"{v:g}"))
    print("\n=== Six example answers ===")
    for i, line in enumerate(answers, 1):
        print(f"{i}. {line}")
    print("\n=== Suspicious ===")
    for n in notes:
        print(f"  - {n}")


if __name__ == "__main__":
    main()
