"""Hard exclusions, fixed-anchor normalization, pillar scores, weighted geometric mean."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.common.io import INTERIM, PROCESSED, RAW, ROOT

CONFIG_PATH = ROOT / "config" / "scoring.yaml"
OUTPUTS = ROOT / "outputs"
FEATURES_PATH = PROCESSED / "county_features.parquet"
NEVER_VETO = frozenset({"cobenefit", "cobenefit_econ", "cobenefit_heat"})

OPS = {
    ">": lambda s, v: s > v,
    ">=": lambda s, v: s >= v,
    "<": lambda s, v: s < v,
    "<=": lambda s, v: s <= v,
    "==": lambda s, v: s == v,
}


def load_config(path: Path | None = None) -> dict:
    return yaml.safe_load((path or CONFIG_PATH).read_text())


def feat_col(spec: dict) -> str:
    return spec.get("col") or spec.get("column")


def pillar_list(cfg: dict) -> list[str]:
    return list(cfg["pillars"])


def veto_floor(cfg: dict) -> float:
    return float(cfg.get("veto", {}).get("floor", cfg.get("veto_threshold", 0.15)))


def veto_pillars(cfg: dict) -> list[str]:
    listed = (cfg.get("veto") or {}).get("pillars")
    if listed:
        return list(listed)
    return [p for p in cfg.get("pillars", []) if p not in NEVER_VETO]


def weight_vector(cfg: dict, weights: dict | None = None) -> pd.Series:
    w = pd.Series(weights if weights is not None else cfg["weights"], dtype=float)
    w = w.reindex(pillar_list(cfg)).fillna(0.0)
    total = float(w.sum())
    if total <= 0:
        raise ValueError("weights must sum to a positive number")
    return w / total


def pnw_judgment_fips(cfg: dict) -> set[str]:
    ids = set(int(x) for x in (cfg.get("manual_adjustments") or {}).get("pnw_constrained_ttp", {}).get("utility_ids", []))
    if not ids:
        return set()
    path = INTERIM / "_utility_county_map.parquet"
    if path.exists():
        m = pd.read_parquet(path)
        return set(m.loc[m["utility_id_eia"].isin(ids), "fips"].astype(str).str.zfill(5))
    return set()


def apply_manual_adjustments(df: pd.DataFrame, cfg: dict, ttp_years: float | None = None) -> pd.DataFrame:
    """County tax overrides and PNW constrained time-to-power from config/manual CSVs."""
    out = df.copy()
    adj = cfg.get("manual_adjustments") or {}
    for fips, status in (adj.get("tax_status_overrides") or {}).items():
        out.loc[out["fips"] == str(fips).zfill(5), "prm_tax_exemption_status"] = status
    ttp = adj.get("pnw_constrained_ttp") or {}
    ids = {int(x) for x in ttp.get("utility_ids", [])}
    fips = pnw_judgment_fips(cfg)
    if not fips and ids and "pwr_main_utility_id" in out.columns:
        uid = pd.to_numeric(out["pwr_main_utility_id"], errors="coerce")
        fips = set(out.loc[uid.isin(ids), "fips"].astype(str))
    if fips:
        years = float(ttp_years if ttp_years is not None else ttp.get("years", 6))
        hit = out["fips"].isin(fips)
        out.loc[hit, "pwr_time_to_power_yrs"] = years
        out.loc[hit, "pwr_time_to_power_source"] = ttp.get("basis", "constrained_judgment")
        print(f"[score] PNW constrained TTP = {years:g} yrs on {int(hit.sum())} counties")
    if adj.get("tax_status_overrides"):
        print(f"[score] tax overrides: {adj['tax_status_overrides']}")
    return out


def apply_computed(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    out = df.copy()
    for spec in cfg.get("computed", []):
        name = spec["name"]
        if "sum" in spec:
            out[name] = out[spec["sum"]].sum(axis=1, min_count=1)
        elif "copy" in spec:
            out[name] = out[spec["copy"]]
        elif "product" in spec:
            cols = spec["product"]
            prod = out[cols[0]].astype(float)
            for c in cols[1:]:
                prod = prod * out[c].astype(float)
            out[name] = prod
        else:
            raise ValueError(f"unknown computed spec: {spec}")
        if "scale" in spec:
            out[name] = out[name] * float(spec["scale"])
        if "times" in spec:
            out[name] = out[name] * out[spec["times"]].astype(float)
    return out


def attach_nri_alr(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, str]:
    """Join NRI annual-loss-rate national percentiles from the cached county table."""
    spec = cfg.get("nri_alr") or {}
    path = ROOT / spec.get("path", "data/raw/fema_nri/NRI_Table_Counties.csv")
    mapping = spec.get("columns") or {
        "RFLD_ALR_NPCTL": "haz_alr_riverine_flood",
        "WFIR_ALR_NPCTL": "haz_alr_wildfire",
        "ERQK_ALR_NPCTL": "haz_alr_earthquake",
        "TRND_ALR_NPCTL": "haz_alr_tornado",
    }
    if not path.exists():
        note = (f"NRI raw table not found at {path.relative_to(ROOT)}; "
                "hazard pillar uses haz_eal_* (EAL scores grow with building value).")
        print(f"[score] {note}")
        return df, note
    src = pd.read_csv(path, usecols=["STCOFIPS", *mapping.keys()], dtype={"STCOFIPS": str})
    have = [c for c in mapping if c in src.columns]
    if not have:
        afreq = {"RFLD_AFREQ": "haz_alr_riverine_flood", "WFIR_AFREQ": "haz_alr_wildfire",
                 "ERQK_AFREQ": "haz_alr_earthquake", "TRND_AFREQ": "haz_alr_tornado",
                 "HRCN_AFREQ": "haz_alr_hurricane", "CFLD_AFREQ": "haz_alr_coastal_flood"}
        src = pd.read_csv(path, usecols=["STCOFIPS", *afreq.keys()], dtype={"STCOFIPS": str})
        for raw, dest in afreq.items():
            src[dest] = src[raw].rank(method="average", pct=True) * 100.0
        mapping = {dest: dest for dest in afreq.values()}
        have = list(mapping)
        note = "NRI ALR_NPCTL columns missing; used national percentile of annualized frequency (AFREQ)."
    else:
        note = ("Hazard pillar uses NRI expected-annual-loss-rate national percentiles "
                f"({', '.join(have)}) from cached {path.relative_to(ROOT)}.")
    from src.common.geo import table_join

    how = {c: "mean" for c in have}
    joined = table_join(src, "STCOFIPS", how, source="fema_nri").rename(columns=mapping)
    out = df.merge(joined, on="fips", how="left")
    print(f"[score] {note}")
    return out, note


def _predicate(df: pd.DataFrame, pred: dict) -> pd.Series:
    col = pred.get("column") or pred.get("col")
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    return OPS[pred["op"]](df[col], pred["value"]).fillna(False)


def apply_exclusions(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int], pd.DataFrame]:
    flags = {}
    for rule in cfg["exclusions"]:
        if "all" in rule:
            mask = pd.Series(True, index=df.index)
            for pred in rule["all"]:
                mask = mask & _predicate(df, pred)
        else:
            mask = _predicate(df, rule)
        flags[rule["id"]] = mask.astype(int)
    flag_df = pd.DataFrame(flags, index=df.index)
    failed_any = flag_df.any(axis=1)
    counts = {rule["id"]: int(flag_df[rule["id"]].sum()) for rule in cfg["exclusions"]}
    labels = {rule["id"]: rule["label"] for rule in cfg["exclusions"]}

    excl = df.loc[failed_any, ["fips", "meta_county_name", "meta_state_abbr"]].copy()
    excl = excl.rename(columns={"meta_county_name": "county", "meta_state_abbr": "state"})
    excl = excl.join(flag_df.loc[failed_any])
    excl["failed_rules"] = [
        "; ".join(labels[c] for c in flag_df.columns if row[c] == 1) for _, row in flag_df.loc[failed_any].iterrows()
    ]
    excl["n_failed"] = flag_df.loc[failed_any].sum(axis=1).astype(int)
    excl = excl.sort_values(["state", "county"]).reset_index(drop=True)

    kept = df.loc[~failed_any].copy().reset_index(drop=True)
    n_surv = len(kept)
    print(f"[score] surviving counties: {n_surv:,} / {len(df):,}")
    for rule in cfg["exclusions"]:
        print(f"  {rule['label']}: {counts[rule['id']]:,}")
    warn_below = int(cfg.get("survive_warn_below", 500))
    if n_surv < warn_below:
        worst = max(counts, key=counts.get)
        print(f"[score] WARNING: only {n_surv} survived (expected 1,500–2,500). "
              f"Most-removing rule: {labels[worst]} ({counts[worst]} counties).")

    reasons = pd.Series("", index=df.index, dtype=object)
    reasons.loc[failed_any] = [
        "; ".join(labels[c] for c in flag_df.columns if row[c] == 1) for _, row in flag_df.loc[failed_any].iterrows()
    ]
    print("\n[score] hub check:")
    for hub in cfg.get("hubs", []):
        fips = str(hub["fips"]).zfill(5)
        hit = df["fips"] == fips
        if not hit.any():
            print(f"  {hub['name']} ({fips}): not in table")
            continue
        i = df.index[hit][0]
        if failed_any.loc[i]:
            print(f"  {hub['name']} ({fips}): EXCLUDED — {reasons.loc[i]}")
        else:
            print(f"  {hub['name']} ({fips}): survives")
    return kept, excl, counts, flag_df.assign(failed_rules=reasons, excluded=failed_any.astype(int))


def _map_series(x: pd.Series, mapping: dict) -> pd.Series:
    out = pd.Series(np.nan, index=x.index, dtype=float)
    num = pd.to_numeric(x, errors="coerce")
    text = x.astype(str).str.strip().str.lower()
    for k, v in mapping.items():
        if isinstance(k, bool):
            continue
        if isinstance(k, (int, float)) and not isinstance(k, bool):
            out = out.where(num != float(k), float(v))
        out = out.where(text != str(k).strip().lower(), float(v))
    return out


def _normalize_one(x: pd.Series, spec: dict) -> pd.Series:
    if "map" in spec:
        return _map_series(x, spec["map"])
    lo, hi = float(spec["lo"]), float(spec["hi"])
    vals = pd.to_numeric(x, errors="coerce")
    if spec.get("transform") == "log":
        vals, lo, hi = np.log1p(vals), np.log1p(lo), np.log1p(hi)
    score = ((vals - lo) / (hi - lo)).clip(0, 1)
    direction = spec.get("direction", "higher")
    if direction in ("lower", "lower_is_better"):
        score = 1.0 - score
    return score


def resolve_feature_col(df: pd.DataFrame, spec: dict) -> str | None:
    col = feat_col(spec)
    if col in df.columns:
        return col
    fb = spec.get("fallback")
    if fb and fb in df.columns:
        print(f"[score] {col} missing; using fallback {fb}")
        return fb
    print(f"[score] skip {col}: column not in table")
    return None


def normalize_features(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, list[dict]]:
    used = []
    cols = {}
    for spec in cfg["features"]:
        src = resolve_feature_col(df, spec)
        if src is None:
            continue
        name = feat_col(spec)
        cols[name] = _normalize_one(df[src], spec)
        used.append({**spec, "col": name, "source": src, "weight": float(spec.get("weight", 1))})
    scores = pd.DataFrame(cols, index=df.index)
    print(f"[score] normalized {len(used)} features on {len(df):,} counties")
    return scores, used


def weighted_row_mean(frame: pd.DataFrame, weights: list[float]) -> pd.Series:
    x = frame.to_numpy(dtype=float)
    w = np.asarray(weights, dtype=float)
    ok = np.isfinite(x)
    ww = np.where(ok, w, 0.0)
    num = np.nansum(np.where(ok, x, 0.0) * w, axis=1)
    den = ww.sum(axis=1)
    out = np.divide(num, den, out=np.full(len(frame), np.nan), where=den > 0)
    return pd.Series(out, index=frame.index)


def pillar_from_features(feat_scores: pd.DataFrame, used: list[dict], pillar: str,
                         skip: set[str] | None = None) -> pd.Series:
    specs = [s for s in used if s["pillar"] == pillar and feat_col(s) not in (skip or set())]
    if not specs:
        return pd.Series(np.nan, index=feat_scores.index)
    cols = [feat_col(s) for s in specs]
    return weighted_row_mean(feat_scores[cols], [float(s.get("weight", 1)) for s in specs])


def compute_pillars(feat_scores: pd.DataFrame, used: list[dict], cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_pillar: dict[str, list[dict]] = {}
    for spec in used:
        by_pillar.setdefault(spec["pillar"], []).append(spec)

    raw = {p: pillar_from_features(feat_scores, used, p) for p in by_pillar}

    mix = cfg["cobenefit_mix"]
    econ, heat = raw.get("cobenefit_econ"), raw.get("cobenefit_heat")
    if econ is not None and heat is not None:
        cob = mix["cobenefit_econ"] * econ + mix["cobenefit_heat"] * heat
        cob = cob.where(econ.notna() | heat.notna())
        cob = cob.where(econ.notna(), heat)
        cob = cob.where(heat.notna(), econ)
        raw["cobenefit"] = cob
    elif econ is not None:
        raw["cobenefit"] = econ
    elif heat is not None:
        raw["cobenefit"] = heat

    pillars = pd.DataFrame({p: raw[p] for p in pillar_list(cfg)})

    cob_cols = [feat_col(s) for s in by_pillar.get("cobenefit_econ", []) + by_pillar.get("cobenefit_heat", [])]
    feature_groups = {p: [feat_col(s) for s in by_pillar.get(p, [])] for p in pillar_list(cfg)}
    feature_groups["cobenefit"] = cob_cols

    frac = float(cfg.get("sparse_fraction", 0.5))
    flags = pd.DataFrame(index=feat_scores.index)
    for p, cols in feature_groups.items():
        if not cols:
            flags[f"flag_sparse_{p}"] = 1
            continue
        n_ok = feat_scores[cols].notna().sum(axis=1)
        flags[f"flag_sparse_{p}"] = (n_ok < frac * len(cols)).astype(int)
    return pillars, flags


def geometric_mean(pillars: pd.DataFrame, weights: pd.Series, floor: float = 0.01) -> pd.Series:
    cols = [c for c in weights.index if c in pillars.columns]
    w = weights[cols].astype(float)
    w = w / w.sum()
    p = pillars[cols].to_numpy(dtype=float)
    p = np.maximum(np.nan_to_num(p, nan=floor), floor)
    return pd.Series(np.exp(np.log(p) @ w.to_numpy()), index=pillars.index, name="final_score")


def active_veto_pillars(cfg: dict, weights: pd.Series | dict | None, pillars: pd.DataFrame) -> list[str]:
    allowed = [p for p in veto_pillars(cfg) if p in pillars.columns and p not in NEVER_VETO]
    if weights is None:
        return allowed
    w = pd.Series(weights, dtype=float)
    return [p for p in allowed if float(w.get(p, 0.0) or 0.0) > 0]


def veto_flags(
    pillars: pd.DataFrame,
    cfg: dict,
    weights: pd.Series | dict | None = None,
    apply_veto: bool = True,
) -> tuple[pd.Series, pd.Series]:
    if not apply_veto:
        z = pd.Series(0, index=pillars.index, dtype=int)
        return z.rename("flag_veto"), pd.Series("", index=pillars.index, dtype=object).rename("veto_pillar")
    check = active_veto_pillars(cfg, weights, pillars)
    floor = veto_floor(cfg)
    if not check:
        z = pd.Series(0, index=pillars.index, dtype=int)
        return z.rename("flag_veto"), pd.Series("", index=pillars.index, dtype=object).rename("veto_pillar")
    low = pillars[check] < floor
    flag = low.any(axis=1).astype(int)
    reason = low.apply(lambda r: ";".join(r.index[r.astype(bool)]), axis=1).where(flag == 1, "")
    return flag.rename("flag_veto"), reason.rename("veto_pillar")


def veto_matrix(pillars: np.ndarray, weights: np.ndarray, names: list[str], cfg: dict) -> np.ndarray:
    """(n, k) veto flags for k weight vectors. Co-benefits never veto."""
    allowed = set(veto_pillars(cfg)) - NEVER_VETO
    idx = [i for i, name in enumerate(names) if name in allowed]
    floor = veto_floor(cfg)
    if not idx:
        return np.zeros((pillars.shape[0], weights.shape[0]), dtype=bool)
    low = pillars[:, idx] < floor
    active = weights[:, idx] > 0
    return (low[:, None, :] & active[None, :, :]).any(axis=2)


def rank_with_veto(
    scores: pd.Series,
    pillars: pd.DataFrame,
    threshold: float,
    weights: pd.Series | dict | None = None,
    apply_veto: bool = True,
    veto_cols: list[str] | None = None,
) -> tuple[pd.Series, pd.Series]:
    """Keep the 2-tuple return that app.py / tradeoff callers unpack."""
    cfg = {"veto": {"floor": threshold, "pillars": veto_cols or [c for c in pillars.columns if c not in NEVER_VETO]}}
    flag, _ = veto_flags(pillars, cfg, weights, apply_veto=apply_veto)
    order = np.lexsort((-scores.to_numpy(), flag.to_numpy()))
    rank = pd.Series(0, index=scores.index, dtype=int)
    rank.iloc[order] = np.arange(1, len(scores) + 1)
    return rank, flag


def strongest_weakest(feat_scores: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    names = list(feat_scores.columns)
    x = feat_scores.to_numpy(dtype=float)
    n = len(feat_scores)
    hi_idx = np.argsort(np.where(np.isnan(x), -np.inf, x), axis=1)[:, ::-1]
    lo_idx = np.argsort(np.where(np.isnan(x), np.inf, x), axis=1)
    rows = []
    for i in range(n):
        strong, weak = [], []
        for j in hi_idx[i]:
            if np.isnan(x[i, j]):
                break
            strong.append(names[j])
            if len(strong) == k:
                break
        for j in lo_idx[i]:
            if np.isnan(x[i, j]):
                break
            weak.append(names[j])
            if len(weak) == k:
                break
        strong += [""] * (k - len(strong))
        weak += [""] * (k - len(weak))
        rec = {f"strongest_{a + 1}": strong[a] for a in range(k)}
        rec.update({f"weakest_{a + 1}": weak[a] for a in range(k)})
        rows.append(rec)
    return pd.DataFrame(rows, index=feat_scores.index)


def score_from_raw(
    raw: pd.DataFrame,
    cfg: dict,
    feat_scores: pd.DataFrame | None = None,
    used: list[dict] | None = None,
) -> dict:
    if feat_scores is None or used is None:
        feat_scores, used = normalize_features(raw, cfg)
    pillars, flags = compute_pillars(feat_scores, used, cfg)
    kept, excl, counts, excl_all = apply_exclusions(raw, cfg)
    kept_idx = raw.index[raw["fips"].isin(kept["fips"])]
    ranked = assemble_rankings(
        raw.loc[kept_idx].reset_index(drop=True),
        pillars.loc[kept_idx].reset_index(drop=True),
        flags.loc[kept_idx].reset_index(drop=True),
        feat_scores.loc[kept_idx].reset_index(drop=True),
        cfg,
    )
    cache = pd.DataFrame({
        "fips": raw["fips"].values,
        "county": raw["meta_county_name"].values,
        "state": raw["meta_state_abbr"].values,
        "excluded": excl_all["excluded"].values,
        "failed_rules": excl_all["failed_rules"].values,
    }, index=raw.index)
    for p in pillar_list(cfg):
        cache[p] = pillars[p].values
    return {
        "ranked": ranked,
        "pillars": pillars,
        "flags": flags,
        "feat_scores": feat_scores,
        "used": used,
        "kept": kept,
        "excl": excl,
        "counts": counts,
        "excl_all": excl_all,
        "cache": cache,
    }


def median_industrial_price_score(raw: pd.DataFrame, cfg: dict) -> tuple[float, float]:
    spec = next(s for s in cfg["features"] if feat_col(s) == "pwr_ind_price_cents_kwh")
    med = float(pd.to_numeric(raw["pwr_ind_price_cents_kwh"], errors="coerce").median())
    return med, float(_normalize_one(pd.Series([med]), spec).iloc[0])


def print_top10_and_cowlitz(label: str, ranked: pd.DataFrame, robustness: pd.DataFrame,
                            cfg: dict, cowlitz: str = "53015") -> None:
    pillars = pillar_list(cfg)
    cols = ["rank", "county", "state", "final_score", "flag_veto"] + pillars
    print(f"\n=== {label}: top 10 ===")
    print(ranked.head(10)[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    row = robustness.loc[robustness["fips"].astype(str).str.zfill(5) == cowlitz]
    if row.empty:
        print(f"\n=== {label}: Cowlitz WA not in robustness table ===")
        return
    r = row.iloc[0]
    print(f"\n=== {label}: Cowlitz County WA top-10 share ===")
    print(f"  nudged:   {float(r['pct_top10_nudged']):.1f}%")
    print(f"  agnostic: {float(r['pct_top10_agnostic']):.1f}%")


def run_sensitivities(base_raw: pd.DataFrame, cfg: dict) -> None:
    from src.score.robustness import run_robustness

    fips = pnw_judgment_fips(cfg)
    print("\n========== Sensitivities ==========")

    for years in (5, 7):
        raw = apply_manual_adjustments(base_raw, cfg, ttp_years=years)
        out = score_from_raw(raw, cfg)
        rob = run_robustness(cfg, df=out["cache"])
        print_top10_and_cowlitz(f"Sensitivity (a) PNW TTP = {years} yrs", out["ranked"], rob, cfg)

    raw = apply_manual_adjustments(base_raw, cfg)
    feat_scores, used = normalize_features(raw, cfg)
    med_price, med_score = median_industrial_price_score(raw, cfg)
    hit = raw["fips"].isin(fips)
    feat_scores = feat_scores.copy()
    feat_scores.loc[hit, "pwr_ind_price_cents_kwh"] = med_score
    print(f"[score] industrial price → national-median price score "
          f"({med_price:.3f} ¢/kWh → {med_score:.3f}) on {int(hit.sum())} PNW-utility counties")
    out = score_from_raw(raw, cfg, feat_scores=feat_scores, used=used)
    rob = run_robustness(cfg, df=out["cache"])
    print_top10_and_cowlitz("Sensitivity (b) PNW industrial price = national median", out["ranked"], rob, cfg)

    raw = apply_manual_adjustments(base_raw, cfg, ttp_years=7)
    feat_scores, used = normalize_features(raw, cfg)
    med_price, med_score = median_industrial_price_score(raw, cfg)
    hit = raw["fips"].isin(fips)
    feat_scores = feat_scores.copy()
    feat_scores.loc[hit, "pwr_ind_price_cents_kwh"] = med_score
    print(f"[score] combined stress: TTP=7 and industrial price → national-median score "
          f"({med_price:.3f} ¢/kWh → {med_score:.3f}) on {int(hit.sum())} PNW-utility counties")
    out = score_from_raw(raw, cfg, feat_scores=feat_scores, used=used)
    rob = run_robustness(cfg, df=out["cache"])
    print_top10_and_cowlitz(
        "Combined stress: PNW TTP = 7 and industrial price = national median",
        out["ranked"], rob, cfg,
    )


IMPACT_METRICS = [
    "crb_lrmer_2035_kg_mwh", "crb_grid_co2_kg_mwh",
    "wtr_grid_water_l_kwh", "wtr_bws_score", "wtr_bws_2050_score",
    "haz_cdd_annual", "haz_days_gt95f_2050", "cob_hdd_annual",
    "pwr_dist_hv230_line_km", "lnd_dist_brownfield_or_retired_km",
    "cob_lowtemp_ind_heat_tbtu", "cob_ghgrp_combustion_facilities_n",
    "prm_pop_density_km2", "prm_contested_total",
]
IMPACT_COUNTIES = [
    ("53015", "Cowlitz WA"),
    ("19113", "Linn IA"),
    ("40097", "Mayes OK"),
    ("51107", "Loudoun VA"),
]


def write_impact_inputs(raw: pd.DataFrame, kept: pd.DataFrame, path: Path | None = None) -> pd.DataFrame:
    """Raw (unnormalized) values for the impact-estimate comparison."""
    dest = path or (OUTPUTS / "impact_inputs.csv")
    surv = raw.loc[raw["fips"].isin(set(kept["fips"]))]
    rows = []
    for col in IMPACT_METRICS:
        rec = {"metric": col}
        series = pd.to_numeric(raw[col], errors="coerce") if col in raw.columns else None
        for fips, label in IMPACT_COUNTIES:
            if series is None:
                rec[label] = np.nan
            else:
                hit = series.loc[raw["fips"] == fips]
                rec[label] = float(hit.iloc[0]) if len(hit) and pd.notna(hit.iloc[0]) else np.nan
        rec["median_survivors"] = (
            float(pd.to_numeric(surv[col], errors="coerce").median()) if col in surv.columns else np.nan
        )
        rows.append(rec)
    table = pd.DataFrame(rows)
    dest.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(dest, index=False)
    print(f"\n=== Impact inputs (raw values) ===")
    print(table.to_string(index=False))
    print(f"[score] wrote {dest.relative_to(ROOT)}")
    return table


def assemble_rankings(
    kept: pd.DataFrame,
    pillars: pd.DataFrame,
    flags: pd.DataFrame,
    feat_scores: pd.DataFrame,
    cfg: dict,
    weights: dict | None = None,
) -> pd.DataFrame:
    w = weight_vector(cfg, weights)
    floor = float(cfg.get("geo_mean_floor", 0.01))
    scores = geometric_mean(pillars, w, floor=floor)
    flag, reason = veto_flags(pillars, cfg, w, apply_veto=True)
    order = np.lexsort((-scores.to_numpy(), flag.to_numpy()))
    rank = pd.Series(0, index=scores.index, dtype=int)
    rank.iloc[order] = np.arange(1, len(scores) + 1)
    sw = strongest_weakest(feat_scores)
    out = pd.DataFrame({
        "fips": kept["fips"].values,
        "county": kept["meta_county_name"].values,
        "state": kept["meta_state_abbr"].values,
        "final_score": scores.values,
        "rank": rank.values,
    }, index=kept.index)
    for p in pillar_list(cfg):
        out[p] = pillars[p].values
    out["flag_veto"] = flag.values
    out["veto_pillar"] = reason.values
    for c in flags.columns:
        out[c] = flags[c].values
    for c in sw.columns:
        out[c] = sw[c].values
    return out.sort_values(["rank", "fips"]).reset_index(drop=True)


def utility_name_lookup() -> pd.Series:
    """EIA utility id -> latest name from the cached PUDL 861 sales table (no download)."""
    path = RAW / "pudl" / "core_eia861__yearly_sales.parquet"
    if not path.exists():
        return pd.Series(dtype=object)
    s = pd.read_parquet(path, columns=["utility_id_eia", "utility_name_eia", "report_date"])
    s = s.dropna(subset=["utility_id_eia", "utility_name_eia"]).sort_values("report_date")
    return s.drop_duplicates("utility_id_eia", keep="last").set_index("utility_id_eia")["utility_name_eia"]


def print_top15_utilities(ranked: pd.DataFrame, raw: pd.DataFrame) -> None:
    names = utility_name_lookup()
    top = ranked.head(15)[["rank", "fips", "county", "state"]].merge(
        raw[["fips", "pwr_main_utility_id", "pwr_time_to_power_yrs", "pwr_time_to_power_source"]],
        on="fips", how="left")
    top["utility_name"] = pd.to_numeric(top["pwr_main_utility_id"], errors="coerce").map(names)
    print("\n=== Base top 15 utilities / time-to-power ===")
    print(top[["rank", "county", "state", "pwr_main_utility_id", "utility_name",
               "pwr_time_to_power_yrs", "pwr_time_to_power_source"]]
          .to_string(index=False, float_format=lambda v: f"{v:.2f}"))


def print_top5_pillar_features(ranked: pd.DataFrame, feat_scores: pd.DataFrame, used: list[dict],
                               raw: pd.DataFrame) -> None:
    by = {}
    for spec in used:
        by.setdefault(spec["pillar"], []).append(feat_col(spec))
    feats = feat_scores.copy()
    feats["fips"] = raw["fips"].values
    print("\n=== Top 5 power and carbon feature scores ===")
    for _, row in ranked.head(5).iterrows():
        fs = feats.loc[feats["fips"] == row["fips"]].iloc[0]
        print(f"\n  {int(row['rank'])}. {row['county']}, {row['state']}  "
              f"final={row['final_score']:.3f}  power={row['power']:.3f}  carbon={row['carbon']:.3f}")
        for pillar in ("power", "carbon"):
            bits = [f"{c}={float(fs[c]):.3f}" for c in by.get(pillar, []) if c in fs.index and pd.notna(fs[c])]
            print(f"     {pillar}: " + "  ".join(bits))


def print_veto_counts(ranked: pd.DataFrame, cfg: dict) -> dict[str, int]:
    counts = {p: int(ranked["veto_pillar"].fillna("").str.contains(fr"(?:^|;){p}(?:;|$)", regex=True).sum())
              for p in veto_pillars(cfg)}
    print("\n=== Veto counts by pillar ===")
    print(f"  vetoed counties: {int(ranked['flag_veto'].sum()):,} / {len(ranked):,}")
    for p, n in counts.items():
        print(f"  {p}: {n:,}")
    return counts


def write_county_geojson(path: Path | None = None) -> Path:
    """Simplified Census county polygons for the Streamlit choropleth (no download)."""
    from src.common.counties import load_counties

    dest = path or (OUTPUTS / "counties.geojson")
    g = load_counties()[["fips", "geometry"]].to_crs(5070)
    g["geometry"] = g.geometry.simplify(2000)
    g = g.to_crs(4326)
    dest.parent.mkdir(parents=True, exist_ok=True)
    geo = json.loads(g.to_json())
    dest.write_text(json.dumps(geo))
    print(f"[score] wrote {dest.relative_to(ROOT)} ({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


def _print_summary(ranked: pd.DataFrame, excl: pd.DataFrame, counts: dict, cfg: dict,
                   robustness: pd.DataFrame | None, sanity_text: str) -> None:
    labels = {r["id"]: r["label"] for r in cfg["exclusions"]}
    print("\n=== Excluded counties by rule ===")
    for rid, n in counts.items():
        print(f"  {labels[rid]}: {n:,}")
    print(f"  unique excluded: {len(excl):,}")
    print(f"  surviving: {len(ranked):,}")

    pillars = pillar_list(cfg)
    cols = ["rank", "county", "state", "final_score", "flag_veto"] + pillars
    print("\n=== Base top 10 ===")
    print(ranked.head(10)[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    if robustness is not None:
        top15 = ranked.head(15)[["fips"]].merge(robustness, on="fips", how="left")
        print("\n=== Robustness (base top 15) ===")
        show = ["county", "state", "pct_top10_nudged", "pct_top10_agnostic",
                "median_rank_nudged", "rank_p10", "rank_p90"]
        print(top15[show].to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    print("\n=== Sanity ===")
    print(sanity_text)

    print("\n=== Suspicious ===")
    notes = []
    top = ranked.head(10)
    state_counts = top["state"].value_counts()
    if int(state_counts.iloc[0]) > 3:
        notes.append(f"More than 3 of the top 10 in {state_counts.index[0]} ({int(state_counts.iloc[0])} of 10).")
    sparse_cols = [c for c in ranked.columns if c.startswith("flag_sparse_")]
    sparse_top = top[sparse_cols].sum(axis=1) if sparse_cols else pd.Series(0, index=top.index)
    if (sparse_top > 0).any():
        names = top.loc[sparse_top > 0, "county"] + " " + top.loc[sparse_top > 0, "state"]
        notes.append("Sparse pillars in top 10: " + ", ".join(names))
    if int(top["flag_veto"].sum()) > 0:
        notes.append("Vetoed counties appeared in the top 10 (should not happen).")
    for p in pillars:
        sd = float(ranked[p].std())
        if sd < 0.05:
            notes.append(f"Pillar {p} is nearly constant across survivors (std={sd:.3f}).")
    if not notes:
        notes.append("None: top 10 is multi-state, no sparse/veto flags, no flat pillars.")
    for n in notes:
        print(f"  - {n}")


def main() -> None:
    from src.score.robustness import run_robustness
    from src.score.sanity import run_sanity

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    raw0 = pd.read_parquet(FEATURES_PATH)
    raw0["fips"] = raw0["fips"].astype(str).str.zfill(5)
    raw0, nri_note = attach_nri_alr(raw0, cfg)
    raw0 = apply_computed(raw0, cfg)
    raw = apply_manual_adjustments(raw0, cfg)

    out = score_from_raw(raw, cfg)
    feat_scores, used = out["feat_scores"], out["used"]
    pillars, flags = out["pillars"], out["flags"]
    kept, excl, counts, excl_all = out["kept"], out["excl"], out["counts"], out["excl_all"]
    ranked = out["ranked"]

    cache = out["cache"]
    for rid in [r["id"] for r in cfg["exclusions"]]:
        cache[rid] = excl_all[rid].values
    for c in flags.columns:
        cache[c] = flags[c].values
    for c in feat_scores.columns:
        cache[c] = feat_scores[c].values
    for extra in ("cand_land_km2", "pwr_main_utility_id", "pwr_time_to_power_yrs", "pwr_time_to_power_source",
                  "lbl_dc_existing_n", "lbl_frontier_ai_dc_n", "lbl_contested_n"):
        if extra in raw.columns:
            cache[extra] = raw[extra].values
    cache.to_parquet(OUTPUTS / "pillars.parquet", index=False)
    ranked.to_csv(OUTPUTS / "rankings.csv", index=False)
    ranked.head(10).to_csv(OUTPUTS / "top10.csv", index=False)
    excl.to_csv(OUTPUTS / "exclusions.csv", index=False)
    print_veto_counts(ranked, cfg)

    robustness = run_robustness(cfg)
    robustness.to_csv(OUTPUTS / "robustness.csv", index=False)

    sanity_md, sanity_text = run_sanity(cfg, nri_note=nri_note)
    (OUTPUTS / "sanity_report.md").write_text(sanity_md)

    print_top15_utilities(ranked, raw)
    print_top5_pillar_features(ranked, feat_scores, used, raw)
    _print_summary(ranked, excl, counts, cfg, robustness, sanity_text)
    write_impact_inputs(raw, kept)
    run_sensitivities(raw0, cfg)
    print(f"\n[score] wrote {OUTPUTS}")


if __name__ == "__main__":
    main()
