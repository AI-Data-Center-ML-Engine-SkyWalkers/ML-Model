"""Thin FastAPI layer over the existing scoring and trade-off functions.

Run from the repo root:
    uvicorn service.main:app --port 8001
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.score.metrics import add_campus_metrics, load_tradeoff_config
from src.score.score import (
    OUTPUTS,
    apply_computed,
    apply_manual_adjustments,
    geometric_mean,
    load_config,
    pillar_list,
    strongest_weakest,
    veto_flags,
    weight_vector,
)
from src.score.tradeoff import _UNSET, load_metrics, pareto2, solve, sweep
from src.common.io import PROCESSED
from service.convert import (
    FACTOR_META,
    PILLAR_META,
    feature_score_cols,
    jsonable,
    metrics_from_config,
    model_version_from,
    normalize_slider_weights,
    presets_from_config,
    to_site_score,
)

FEATURES_PATH = PROCESSED / "county_features.parquet"
RANKINGS_PATH = OUTPUTS / "rankings.csv"


class RankBody(BaseModel):
    n: int = Field(default=10, ge=1, le=500)
    weights: dict[str, float] | None = None


class SolveBody(BaseModel):
    objective: str = "score"
    constraints: list[list] | None = None
    ignore_pillars: list[str] | None = None
    min_score: float | None = None
    top_n: int = 10
    weights: dict[str, float] | None = None


class SweepBody(BaseModel):
    metric: str
    values: list[float] | None = None
    steps: int = Field(default=12, ge=2, le=200)
    objective: str = "score"
    constraints: list[list] | None = None
    ignore_pillars: list[str] | None = None
    min_score: float | None = None
    weights: dict[str, float] | None = None


def _constraints(raw: list[list] | None) -> list[tuple[str, str, float]] | None:
    if not raw:
        return None
    out = []
    for item in raw:
        if len(item) != 3:
            raise HTTPException(400, "each constraint must be [metric, op, value]")
        out.append((str(item[0]), str(item[1]), float(item[2])))
    return out


def _min_score(body: BaseModel):
    return _UNSET if "min_score" not in body.model_fields_set else body.min_score


class Store:
    """Caches every table the routes need. Built once at import."""

    def __init__(self) -> None:
        self.cfg = load_config()
        self.tcfg = load_tradeoff_config()
        self.pillar_ids = pillar_list(self.cfg)
        self.model_version = model_version_from(RANKINGS_PATH)

        pillars = pd.read_parquet(OUTPUTS / "pillars.parquet")
        pillars["fips"] = pillars["fips"].astype(str).str.zfill(5)
        features = pd.read_parquet(FEATURES_PATH)
        features["fips"] = features["fips"].astype(str).str.zfill(5)
        features = apply_computed(features, self.cfg)
        features = apply_manual_adjustments(features, self.cfg)
        features = add_campus_metrics(features, self.tcfg)

        robustness = pd.read_csv(OUTPUTS / "robustness.csv", dtype={"fips": str})
        robustness["fips"] = robustness["fips"].astype(str).str.zfill(5)
        if "pct_top10_nudged" in robustness.columns:
            features = features.merge(robustness[["fips", "pct_top10_nudged"]], on="fips", how="left")

        self.metrics = load_metrics()
        self.features = features.set_index("fips", drop=False)
        self.pillars = pillars.set_index("fips", drop=False)

        feat_cols = feature_score_cols(self.cfg, pillars.columns)
        sw = strongest_weakest(pillars[feat_cols], k=3)
        sw.index = pillars["fips"].to_numpy()
        self.strongest = sw[[f"strongest_{i}" for i in range(1, 4)]]
        self.weakest = sw[[f"weakest_{i}" for i in range(1, 4)]]

        surviving = pillars["excluded"].fillna(0).astype(int) == 0
        self.surv_fips = pillars.loc[surviving, "fips"].tolist()
        self.surv_pillars = pillars.loc[surviving, self.pillar_ids].reset_index(drop=True)
        self.surv_index = pd.Index(self.surv_fips)

        self.templates: dict[str, dict] = {}
        for fips, prow in self.pillars.iterrows():
            if fips not in self.features.index:
                continue
            raw = self.features.loc[fips]
            strong = [str(self.strongest.loc[fips, c]) for c in self.strongest.columns] if fips in self.strongest.index else []
            weak = [str(self.weakest.loc[fips, c]) for c in self.weakest.columns] if fips in self.weakest.index else []
            strong = [c for c in strong if c and c != "nan"]
            weak = [c for c in weak if c and c != "nan"]
            self.templates[fips] = to_site_score(
                fips, raw, prow, strong, weak, self.pillar_ids, score=None, rank=None,
            )

        self.base_order, self.base_scores, self.base_ranks = self._rank_weights(None)
        w_base = weight_vector(self.cfg, None)
        floor = float(self.cfg.get("geo_mean_floor", 0.01))
        for fips, site in list(self.templates.items()):
            site = dict(site)
            if fips in self.base_scores:
                site["score"] = round(100.0 * float(self.base_scores[fips]), 1)
                site["rank"] = self.base_ranks[fips]
            else:
                row = self.pillars.loc[[fips], self.pillar_ids]
                site["score"] = round(100.0 * float(geometric_mean(row, w_base, floor=floor).iloc[0]), 1)
            self.templates[fips] = site

        self.meta_payload = {
            "model_version": self.model_version,
            "pillars": PILLAR_META,
            "presets": presets_from_config(self.cfg),
            "factors": FACTOR_META,
            "metrics": metrics_from_config(self.tcfg, self.metrics),
        }

    def _rank_weights(self, unit_weights: dict | None) -> tuple[list[str], dict[str, float], dict[str, int]]:
        w = weight_vector(self.cfg, unit_weights)
        floor = float(self.cfg.get("geo_mean_floor", 0.01))
        scores = geometric_mean(self.surv_pillars, w, floor=floor)
        flag, _ = veto_flags(self.surv_pillars, self.cfg, w, apply_veto=True)
        order = np.lexsort((-scores.to_numpy(), flag.to_numpy()))
        ranked_fips = [self.surv_fips[i] for i in order]
        score_map = {self.surv_fips[i]: float(scores.iloc[i]) for i in range(len(self.surv_fips))}
        rank_map = {fips: n for n, fips in enumerate(ranked_fips, start=1)}
        return ranked_fips, score_map, rank_map

    def rank(self, n: int, weights: dict | None) -> dict:
        unit = normalize_slider_weights(weights, self.pillar_ids)
        if unit is None and not weights:
            order, scores, ranks = self.base_order, self.base_scores, self.base_ranks
        else:
            order, scores, ranks = self._rank_weights(unit)
        sites = []
        for fips in order[:n]:
            site = dict(self.templates[fips])
            site["score"] = round(100.0 * scores[fips], 1)
            site["rank"] = ranks[fips]
            site["excluded"] = False
            site["exclusion_reason"] = None
            sites.append(site)
        return {
            "model_version": self.model_version,
            "illustrative": False,
            "sites": sites,
        }

    def site(self, fips: str) -> dict:
        key = str(fips).zfill(5)
        if key not in self.templates:
            raise HTTPException(404, "Site not found")
        site = dict(self.templates[key])
        if key in self.base_scores:
            site["score"] = round(100.0 * self.base_scores[key], 1)
            site["rank"] = self.base_ranks[key]
        elif site["score"] == 0.0:
            w = weight_vector(self.cfg, None)
            floor = float(self.cfg.get("geo_mean_floor", 0.01))
            row = self.pillars.loc[[key], self.pillar_ids]
            site["score"] = round(100.0 * float(geometric_mean(row, w, floor=floor).iloc[0]), 1)
        return site

    def _engine_weights(self, weights: dict | None) -> dict | None:
        return normalize_slider_weights(weights, self.pillar_ids)

    def _tag_rows(self, rows: list[dict] | None) -> None:
        for row in rows or []:
            site = self.templates.get(str(row.get("fips", "")).zfill(5))
            attrs = site["attributes"] if site else {}
            row["time_to_power_source"] = attrs.get("time_to_power_source")
            row["time_to_power_tag"] = attrs.get("time_to_power_tag")

    def solve(self, body: SolveBody) -> dict:
        result = solve(
            objective=body.objective,
            constraints=_constraints(body.constraints),
            ignore_pillars=body.ignore_pillars,
            weights=self._engine_weights(body.weights),
            top_n=body.top_n,
            metrics=self.metrics,
            tcfg=self.tcfg,
            scoring_cfg=self.cfg,
            min_score=_min_score(body),
        )
        out = jsonable(result)
        self._tag_rows(out.get("top"))
        self._tag_rows([out["best"]] if out.get("best") else None)
        return out

    def sweep(self, body: SweepBody) -> dict:
        series = pd.to_numeric(self.metrics[body.metric], errors="coerce") if body.metric in self.metrics.columns else None
        if series is None:
            raise HTTPException(400, f"unknown metric: {body.metric}")
        if body.values is None:
            ok = series.dropna()
            if ok.empty:
                raise HTTPException(400, f"no finite values for {body.metric}")
            values = np.linspace(float(ok.min()), float(ok.max()), int(body.steps)).tolist()
        else:
            values = body.values
        rows = sweep(
            metric=body.metric,
            values=values,
            objective=body.objective,
            constraints=_constraints(body.constraints),
            ignore_pillars=body.ignore_pillars,
            weights=self._engine_weights(body.weights),
            metrics=self.metrics,
            tcfg=self.tcfg,
            scoring_cfg=self.cfg,
            min_score=_min_score(body),
        )
        changed = rows.loc[rows["best_changed"] == True]  # noqa: E712
        out = jsonable({
            "metric": body.metric,
            "objective": body.objective,
            "rows": rows,
            "changes": changed,
        })
        self._tag_rows(out["rows"])
        self._tag_rows(out["changes"])
        return out

    def pareto(self, x: str, y: str, min_score: float | None) -> dict:
        df = self.metrics
        if min_score is not None:
            df = df.loc[pd.to_numeric(df["score"], errors="coerce") >= float(min_score)]
        front = pareto2(x, y, metrics=df, tcfg=self.tcfg)
        front_ids = set(front["fips"].astype(str))
        ref_fips = str(self.tcfg["reference_fips"]).zfill(5)
        points = []
        for rec in df[["fips", "county", "state", "score", x, y]].to_dict(orient="records"):
            rec["on_front"] = rec["fips"] in front_ids
            rec["is_reference"] = rec["fips"] == ref_fips
            points.append(rec)
        ref_hit = df.loc[df["fips"] == ref_fips]
        reference = None
        if len(ref_hit):
            reference = ref_hit.iloc[0][["fips", "county", "state", "score", x, y]].to_dict()
            reference["on_front"] = ref_fips in front_ids
            reference["is_reference"] = True
        out = jsonable({
            "x": x,
            "y": y,
            "min_score": min_score,
            "front": front,
            "points": points,
            "reference": reference,
        })
        self._tag_rows([out["reference"]] if out["reference"] else None)
        return out


store = Store()
app = FastAPI(title="Datacenter siting scoring service", version=store.model_version)


@app.get("/meta")
def meta() -> dict[str, Any]:
    return store.meta_payload


@app.post("/rank")
def rank(body: RankBody) -> dict[str, Any]:
    return store.rank(body.n, body.weights)


@app.get("/sites/{fips}")
def site(fips: str) -> dict[str, Any]:
    return store.site(fips)


@app.post("/engine/solve")
def engine_solve(body: SolveBody) -> dict[str, Any]:
    return store.solve(body)


@app.post("/engine/sweep")
def engine_sweep(body: SweepBody) -> dict[str, Any]:
    return store.sweep(body)


@app.get("/engine/pareto")
def engine_pareto(
    x: str = Query("co2_t"),
    y: str = Query("energy_cost_musd"),
    min_score: float | None = Query(0.6),
) -> dict[str, Any]:
    return store.pareto(x, y, min_score)
