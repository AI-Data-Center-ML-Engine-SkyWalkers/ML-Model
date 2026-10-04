"""Sanity checks. Reads outputs/pillars.parquet only."""
from __future__ import annotations

import pandas as pd

from src.score.score import (
    OUTPUTS,
    feat_col,
    geometric_mean,
    pillar_from_features,
    pillar_list,
    rank_with_veto,
    veto_flags,
    veto_floor,
    weight_vector,
)


def _manual_adjustment_lines(cfg: dict) -> list[str]:
    adj = cfg.get("manual_adjustments") or {}
    ttp = adj.get("pnw_constrained_ttp") or {}
    names = ", ".join(f"{u['name']} ({u['id']})" for u in ttp.get("utilities", []))
    tax = adj.get("tax_status_overrides") or {}
    tax_rows = ", ".join(f"{str(k).zfill(5)}={v}" for k, v in tax.items())
    return [
        "These are judgment values, not published interconnection waits or statutory county tax codes.",
        "",
        f"- **PNW time-to-power = {ttp.get('years', 6)} years**, `basis={ttp.get('basis', 'constrained_judgment')}` "
        f"for: {names or 'see utility_time_to_power.csv'}.",
        f"  Source: {(ttp.get('source') or '').strip()}",
        f"- **Tax status overrides** (`not_eligible` → 0.2): {tax_rows or '(none)'}.",
        f"  Source: {(adj.get('tax_status_source') or '').strip()}",
        "- Sensitivities (not the base table): PNW wait at 5 and 7 years; replace industrial price "
        "scores for those utilities' counties with the national-median price score.",
        "",
    ]


def _top_block(df: pd.DataFrame, n: int = 10) -> str:
    cols = [c for c in ["rank", "county", "state", "final_score",
                        "power", "carbon", "water", "permission", "hazard", "land", "cobenefit"] if c in df.columns]
    return df.head(n)[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}")


def _used_from_cfg(cfg: dict, available: set[str]) -> list[dict]:
    used = []
    for spec in cfg["features"]:
        col = feat_col(spec)
        src = col if col in available else spec.get("fallback")
        if src in available or col in available:
            used.append({**spec, "col": col if col in available else src, "weight": float(spec.get("weight", 1))})
    return used


def _rank_persona(surv: pd.DataFrame, cfg: dict, weights: dict, apply_veto: bool = True) -> pd.DataFrame:
    w = weight_vector(cfg, weights)
    cols = pillar_list(cfg)
    scores = geometric_mean(surv[cols], w, floor=float(cfg.get("geo_mean_floor", 0.01)))
    flag, reason = veto_flags(surv[cols], cfg, w, apply_veto=apply_veto)
    rank, flag = rank_with_veto(scores, surv[cols], veto_floor(cfg), w, apply_veto=apply_veto,
                                veto_cols=list(cfg.get("veto", {}).get("pillars", cols)))
    out = surv[["fips", "county", "state", *cols]].copy()
    out["final_score"] = scores.values
    out["rank"] = rank.values
    out["flag_veto"] = flag.values
    out["veto_pillar"] = reason.values
    return out.sort_values("rank")


def run_sanity(cfg: dict, path=None, nri_note: str = "") -> tuple[str, str]:
    df = pd.read_parquet(path or (OUTPUTS / "pillars.parquet"))
    df["fips"] = df["fips"].astype(str).str.zfill(5)
    surv = df[df["excluded"] == 0].copy().reset_index(drop=True)
    used = _used_from_cfg(cfg, set(df.columns))

    # 1. Legacy: no veto; power pillar without time-to-power
    legacy_surv = surv.copy()
    legacy_surv["power"] = pillar_from_features(surv, used, "power", skip={"pwr_time_to_power_yrs"})
    legacy = _rank_persona(legacy_surv, cfg, cfg["personas"]["legacy"], apply_veto=False)
    if "lbl_dc_existing_n" in surv.columns:
        legacy = legacy.merge(surv[["fips", "lbl_dc_existing_n", "lbl_contested_n"]], on="fips", how="left")
    else:
        legacy["lbl_dc_existing_n"] = 0
        legacy["lbl_contested_n"] = 0

    top100 = legacy.head(100)
    share = float((top100["lbl_dc_existing_n"] > 0).mean())
    base_rate = float((surv["lbl_dc_existing_n"] > 0).mean()) if "lbl_dc_existing_n" in surv.columns else 0.0
    spearman = legacy["final_score"].corr(legacy["lbl_dc_existing_n"], method="spearman")

    hub_lines = []
    for hub in cfg.get("hubs", []):
        fips = str(hub["fips"]).zfill(5)
        row = df[df["fips"] == fips]
        if row.empty:
            hub_lines.append(f"- {hub['name']} (`{fips}`): not in table")
            continue
        r = row.iloc[0]
        if int(r["excluded"]) == 1:
            hub_lines.append(f"- {hub['name']} (`{fips}`): excluded ({r['failed_rules']})")
            continue
        lg = legacy[legacy["fips"] == fips]
        if lg.empty:
            hub_lines.append(f"- {hub['name']} (`{fips}`): survived but missing from legacy ranking")
        else:
            g = lg.iloc[0]
            hub_lines.append(
                f"- {hub['name']} (`{fips}`): legacy rank {int(g['rank'])}, score {g['final_score']:.3f}, "
                f"existing DCs {int(g.get('lbl_dc_existing_n', 0))}"
            )

    # 2. Contested: permission without contested feature
    perm_wo = pillar_from_features(surv, used, "permission", skip={"prm_contested_total"})
    contested = surv["lbl_contested_n"] > 0
    n_c = int(contested.sum())
    perm_c = float(perm_wo.loc[contested].mean()) if n_c else float("nan")
    perm_o = float(perm_wo.loc[~contested].mean())
    q25 = float(perm_wo.quantile(0.25))
    risky = perm_wo <= q25
    risky_share = float((contested & risky).sum() / n_c) if n_c else float("nan")

    # 3. Exclusion recall
    frontier = df["lbl_frontier_ai_dc_n"] > 0 if "lbl_frontier_ai_dc_n" in df.columns else pd.Series(False, index=df.index)
    existing = df["lbl_dc_existing_n"] > 0 if "lbl_dc_existing_n" in df.columns else pd.Series(False, index=df.index)
    has_dc = existing | frontier
    excld = df["excluded"] == 1

    def _recall(mask: pd.Series, title: str) -> list[str]:
        n, rem = int(mask.sum()), int((mask & excld).sum())
        pct = rem / n if n else 0.0
        lines = [f"**{title}:** {rem} / {n} removed (**{pct:.1%}**)"]
        for rule in cfg["exclusions"]:
            rid = rule["id"]
            k = int((mask & (df[rid] == 1)).sum()) if rid in df.columns else 0
            lines.append(f"  - {rule['label']}: {k}")
        return lines

    groups = cfg.get("exclusion_groups") or {
        "feasibility": {"label": "feasibility (land, grid, protected)",
                        "rules": ["too_little_candidate_land", "far_from_grid", "protected_land"]},
        "sustainability_risk": {"label": "sustainability/risk (water, hurricane, coastal flood)",
                                "rules": ["extreme_water_stress", "extreme_hurricane", "extreme_coastal_flood"]},
        "policy": {"label": "policy (moratoria)",
                   "rules": ["active_county_moratorium", "statewide_moratorium"]},
    }
    group_lines = []
    for g in groups.values():
        rids = [r for r in g["rules"] if r in df.columns]
        any_rule = df[rids].eq(1).any(axis=1) if rids else pd.Series(False, index=df.index)
        rem = int((has_dc & any_rule).sum())
        n = int(has_dc.sum())
        group_lines.append(f"- {g['label']}: **{rem}** of {n} DC counties "
                           f"({rem / n if n else 0:.1%})")
        for rid in rids:
            label = next((r["label"] for r in cfg["exclusions"] if r["id"] == rid), rid)
            group_lines.append(f"  - {label}: {int((has_dc & (df[rid] == 1)).sum())}")

    land_id = "too_little_candidate_land"
    land_rows = df[df[land_id] == 1][["fips", "county", "state"]].copy() if land_id in df.columns else pd.DataFrame()
    if "cand_land_km2" in df.columns and not land_rows.empty:
        land_rows["cand_land_km2"] = df.loc[land_rows.index, "cand_land_km2"].values
        land_rows = land_rows.sort_values("cand_land_km2")
    land_block = land_rows.to_string(index=False, float_format=lambda v: f"{v:.3f}") if not land_rows.empty else "(none)"

    recall_a = _recall(frontier, "(a) Frontier AI sites only (`lbl_frontier_ai_dc_n` > 0)")
    recall_b = _recall(has_dc, "(b) All DC counties (existing or frontier)")
    n_dc = int(has_dc.sum())
    n_removed = int((has_dc & excld).sum())
    recall = n_removed / n_dc if n_dc else 0.0
    n_front = int(frontier.sum())
    n_front_rem = int((frontier & excld).sum())
    recall_front = n_front_rem / n_front if n_front else 0.0
    recall_lines = [
        *recall_a, "",
        *recall_b, "",
        "**(c) All DC counties grouped by rule type** (a county can count in more than one group)",
        *group_lines, "",
        f"Counties removed by **too little candidate land** ({len(land_rows)}), with `cand_land_km2`:",
        "",
        "```",
        land_block,
        "```",
    ]

    # 4. Personas
    persona_blocks, persona_text = [], []
    for name, weights in cfg["personas"].items():
        if name == "legacy":
            top = legacy
        else:
            top = _rank_persona(surv, cfg, weights, apply_veto=True)
        persona_blocks.append(f"### {name}\n\n```\n{_top_block(top)}\n```\n")
        names = ", ".join(f"{r.county} {r.state}" for r in top.head(10).itertuples())
        persona_text.append(f"  {name}: {names}")

    md = [
        "# Sanity report",
        "",
        "## Step 0 notes",
        "",
        "- `lnd_pct_buildable` is NLCD barren / shrub / grassland / pasture (31, 52, 71, 81) and does **not** "
        "include cropland (82). The land exclusion therefore uses "
        "`cand_land_km2 = (lnd_pct_buildable + lnd_pct_cropland) / 100 × meta_land_area_km2`.",
        f"- {nri_note or 'NRI ALR status not recorded.'}",
        "",
        "## 1. Legacy persona (power 0.5, land 0.3, hazard 0.2; no veto; power without time-to-power)",
        "",
        f"- Share of top 100 with `lbl_dc_existing_n` > 0: **{share:.1%}** "
        f"({int((top100['lbl_dc_existing_n'] > 0).sum())} / 100)",
        f"- Base rate among surviving counties: **{base_rate:.1%}**",
        f"- Spearman correlation(score, `lbl_dc_existing_n`): **{spearman:.3f}**",
        "",
        "Hub counties (Step 1 list):",
        "",
        *hub_lines,
        "",
        "### Top 10 (legacy)",
        "",
        "```",
        _top_block(legacy),
        "```",
        "",
        "## 2. Contested projects vs permission (contested feature removed)",
        "",
        "Permission pillar recomputed without `prm_contested_total`. Moratorium flags may come from the same "
        "news sources as the contested list, so this is a soft check.",
        "",
        f"- Counties with `lbl_contested_n` > 0: **{n_c}**, mean permission (no contested feature) = **{perm_c:.3f}**",
        f"- All others: **{int((~contested).sum())}**, mean = **{perm_o:.3f}**",
        f"- Contested lower than others: **{'yes' if perm_c < perm_o else 'NO'}** (delta {perm_c - perm_o:+.3f})",
        f"- Share of contested counties in the riskiest permission quartile: **{risky_share:.1%}**",
        "",
        "## 3. Exclusion recall",
        "",
        *recall_lines,
        "",
        "## 4. Top 10 by persona",
        "",
        *persona_blocks,
        "## Manual adjustments",
        "",
        *_manual_adjustment_lines(cfg),
    ]
    text = (
        f"Legacy top-100 existing-DC share: {share:.1%} (base rate among survivors {base_rate:.1%})\n"
        f"Spearman(score, existing DCs): {spearman:.3f}\n"
        f"Permission without contested: contested {perm_c:.3f} vs others {perm_o:.3f}; "
        f"riskiest-quartile share {risky_share:.1%}\n"
        f"Exclusion recall (a) frontier: {recall_front:.1%} ({n_front_rem}/{n_front}); "
        f"(b) all DC: {recall:.1%} ({n_removed}/{n_dc})\n"
        + "\n".join(group_lines) + "\n"
        + f"Too little candidate land ({len(land_rows)} counties):\n{land_block}\n"
        + "\n".join(hub_lines) + "\n"
        + "Persona top 10:\n" + "\n".join(persona_text)
    )
    return "\n".join(md) + "\n", text
