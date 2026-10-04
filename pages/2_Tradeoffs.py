"""Constraint / relax trade-offs on real-unit metrics. Reads cached outputs only."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.score.metrics import better_is_lower, load_tradeoff_config, metric_meta, metric_names
from src.score.score import OUTPUTS, load_config, pillar_list
from src.score.tradeoff import load_metrics, pareto2, solve, summarize, sweep

st.set_page_config(page_title="Trade-offs", layout="wide")


@st.cache_data(show_spinner=False)
def load_page() -> tuple[dict, dict, pd.DataFrame, list[str]]:
    tcfg = load_tradeoff_config()
    scfg = load_config()
    metrics = load_metrics()
    pillars_path = OUTPUTS / "pillars.parquet"
    if pillars_path.exists():
        pillars = pd.read_parquet(pillars_path)
        names = [p for p in pillar_list(scfg) if p in pillars.columns]
    else:
        names = pillar_list(scfg)
    return tcfg, scfg, metrics, names


def _label(name: str, tcfg: dict) -> str:
    meta = metric_meta(name, tcfg)
    verb = "Minimize" if meta["better"] == "lower" else "Maximize"
    return f"{verb} {meta['label']}"


def _style_compare(table: pd.DataFrame) -> pd.io.formats.style.Styler:
    show = table[["label", "unit", "best", "reference", "abs_change", "pct_change", "change"]].copy()
    show = show.rename(columns={
        "label": "Metric", "unit": "Unit", "best": "Best", "reference": "Cowlitz",
        "abs_change": "Δ", "pct_change": "%", "change": "Vs Cowlitz",
    })

    def _row(row):
        color = {"better": "#c6f6d5", "worse": "#fed7d7", "same": "#edf2f7"}.get(row["Vs Cowlitz"], "")
        return [f"background-color: {color}" if color else ""] * len(row)

    return (
        show.style
        .apply(_row, axis=1)
        .format({"Best": "{:.3g}", "Cowlitz": "{:.3g}", "Δ": "{:+.3g}", "%": "{:+.1f}"}, na_rep="—")
    )


def _sweep_values(df: pd.DataFrame, metric: str, tcfg: dict, n: int = 12) -> np.ndarray:
    s = pd.to_numeric(df[metric], errors="coerce").dropna()
    if s.empty:
        return np.array([])
    if better_is_lower(metric, tcfg):
        return np.linspace(float(s.quantile(0.90)), float(s.min()), n)
    return np.linspace(float(s.quantile(0.10)), float(s.max()), n)


def main() -> None:
    if not (OUTPUTS / "metrics.parquet").exists():
        st.error("No `outputs/metrics.parquet` yet. Run `python -m src.score.tradeoff` from the repo root.")
        return

    tcfg, scfg, metrics, pillars = load_page()
    names = metric_names(tcfg)
    ref_fips = str(tcfg["reference_fips"]).zfill(5)
    ref = metrics.loc[metrics["fips"] == ref_fips]
    ref_name = f"{ref.iloc[0]['county']}, {ref.iloc[0]['state']}" if len(ref) else "reference"

    st.title("Trade-offs")
    st.caption(
        "One 100 MW campus (load factor 0.8). PUE and WUE are judgment assumptions that rise with "
        "cooling degree days. Energy cost is electricity only — not land or construction. "
        "Only surviving, non-vetoed counties are candidates; hard exclusions stay on."
    )

    with st.sidebar:
        st.header("Question")
        obj_options = ["score"] + [n for n in names if n != "score"]
        objective = st.selectbox(
            "Objective",
            obj_options,
            format_func=lambda n: "Maximize overall score" if n == "score" else _label(n, tcfg),
        )
        ignore = st.multiselect(
            "Ignore pillars in score",
            pillars,
            disabled=objective != "score",
            help="Recompute the geometric mean without these pillars. Use a hazard floor below to say how much climate risk you still accept.",
        )
        default_floor = float(tcfg.get("min_score") if tcfg.get("min_score") is not None else 0.60)
        min_score = st.slider(
            "Minimum overall score",
            min_value=0.0, max_value=1.0, value=default_floor, step=0.01,
            disabled=objective == "score",
            help="keeps answers among buildable sites",
        )
        st.caption("keeps answers among buildable sites")
        score_floor = None if objective == "score" else float(min_score)

        st.header("Limits (up to 3)")
        constraints = []
        for i in range(3):
            cols = st.columns([1.4, 1])
            with cols[0]:
                metric = st.selectbox(
                    f"Constraint {i + 1}",
                    ["(none)"] + names,
                    key=f"c_metric_{i}",
                    format_func=lambda n: "None" if n == "(none)" else metric_meta(n, tcfg)["label"],
                )
            if metric == "(none)":
                continue
            series = pd.to_numeric(metrics[metric], errors="coerce")
            lo, hi = float(series.min()), float(series.max())
            if lo == hi:
                lo, hi = lo - 1.0, hi + 1.0
            step = (hi - lo) / 100.0
            default = hi if better_is_lower(metric, tcfg) else lo
            op = "<=" if better_is_lower(metric, tcfg) else ">="
            with cols[1]:
                val = st.slider(
                    f"{op} ({metric_meta(metric, tcfg)['unit']})",
                    min_value=lo, max_value=hi, value=float(default),
                    step=step, key=f"c_val_{i}", format="%.3g",
                )
            constraints.append((metric, op, float(val)))

        st.caption(f"{len(metrics):,} candidate counties. Reference: {ref_name}.")

    result = solve(
        objective, constraints, ignore_pillars=ignore,
        metrics=metrics, tcfg=tcfg, scoring_cfg=scfg,
        min_score=score_floor,
    )

    if result["n_feasible"] == 0:
        b = result["binding"] or {}
        st.error(summarize(result, constraints, tcfg))
        st.write(
            f"Binding constraint: `{b.get('metric')}` {b.get('op')} {b.get('asked')}. "
            f"It removes {b.get('removes')} of {b.get('n_candidates')} counties. "
            f"Loosen it to **{b.get('loosest_feasible')}** to get at least one feasible county."
        )
        return

    best = result["best"]
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.subheader(f"{best['county']}, {best['state']}")
        st.caption(
            f"`{best['fips']}` · {result['n_feasible']:,} feasible · "
            f"objective `{result['objective']}` = {result['objective_value']:.4g}"
        )
        st.info(summarize(result, constraints, tcfg))
        if result["compare"] is not None:
            st.markdown(f"**Versus {ref_name}**")
            st.dataframe(_style_compare(result["compare"]), width="stretch")

    with right:
        st.subheader("Top 10")
        show = [c for c in [
            "pick_rank", "county", "state", "objective_value", "score",
            "co2_t", "energy_cost_musd", "time_to_power_yrs", "water_ml",
            "water_stress_2050", "hazard", "pct_top10_nudged",
        ] if c in result["top"].columns]
        table = result["top"][show].copy()
        st.dataframe(table, width="stretch", hide_index=True)

    st.divider()
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.subheader("Trade-off curve")
        sweep_metric = st.selectbox(
            "Sweep this limit", names, index=names.index("co2_t") if "co2_t" in names else 0,
            format_func=lambda n: metric_meta(n, tcfg)["label"], key="sweep_metric",
        )
        y_metric = st.selectbox(
            "Plot this as y", names, index=names.index("energy_cost_musd") if "energy_cost_musd" in names else 0,
            format_func=lambda n: metric_meta(n, tcfg)["label"], key="sweep_y",
        )
        values = _sweep_values(metrics, sweep_metric, tcfg)
        curve = sweep(
            sweep_metric, values, objective, constraints, ignore,
            metrics=metrics, tcfg=tcfg, scoring_cfg=scfg,
            min_score=score_floor,
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=curve["limit"], y=curve[y_metric] if y_metric in curve.columns else [None] * len(curve),
            mode="lines+markers", name="best county",
            hovertext=[f"{r.county}, {r.state}" if pd.notna(getattr(r, "county", None)) else "—" for r in curve.itertuples()],
            hoverinfo="text+x+y",
        ))
        ch = curve.loc[curve["best_changed"]]
        if len(ch):
            fig.add_trace(go.Scatter(
                x=ch["limit"], y=ch[y_metric],
                mode="markers", name="winner changes",
                marker=dict(size=14, symbol="diamond", color="#e53e3e"),
                hovertext=[f"{r.county}, {r.state}" for r in ch.itertuples()],
                hoverinfo="text+x+y",
            ))
        fig.update_layout(
            height=380, margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title=f"{metric_meta(sweep_metric, tcfg)['label']} limit",
            yaxis_title=metric_meta(y_metric, tcfg)["label"],
        )
        st.plotly_chart(fig, width="stretch")
        if int(curve["fips"].nunique()) <= 1:
            st.caption("The best county does not change across this sweep.")

    with c2:
        st.subheader("Pareto front")
        px_m = st.selectbox(
            "x", names, index=names.index("co2_t") if "co2_t" in names else 0,
            format_func=lambda n: metric_meta(n, tcfg)["label"], key="pareto_x",
        )
        py_m = st.selectbox(
            "y", names, index=names.index("energy_cost_musd") if "energy_cost_musd" in names else 1,
            format_func=lambda n: metric_meta(n, tcfg)["label"], key="pareto_y",
        )
        front = pareto2(px_m, py_m, metrics=metrics, tcfg=tcfg)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=metrics[px_m], y=metrics[py_m],
            mode="markers", name="candidates",
            marker=dict(size=5, color="#a0aec0", opacity=0.45),
            hovertext=metrics["county"] + ", " + metrics["state"],
            hoverinfo="text",
        ))
        fig.add_trace(go.Scatter(
            x=front[px_m], y=front[py_m],
            mode="markers+lines", name="Pareto front",
            marker=dict(size=9, color="#2b6cb0"),
            line=dict(color="#2b6cb0", width=1),
            hovertext=front["county"] + ", " + front["state"],
            hoverinfo="text",
        ))
        if len(ref):
            fig.add_trace(go.Scatter(
                x=ref[px_m], y=ref[py_m],
                mode="markers+text", name=ref_name,
                marker=dict(size=13, color="#38a169", symbol="star"),
                text=["Cowlitz"], textposition="top right",
            ))
        fig.add_trace(go.Scatter(
            x=[best[px_m]], y=[best[py_m]],
            mode="markers+text", name="current best",
            marker=dict(size=13, color="#c53030", symbol="diamond"),
            text=[f"{best['county']}"], textposition="bottom right",
        ))
        fig.update_layout(
            height=380, margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title=metric_meta(px_m, tcfg)["label"],
            yaxis_title=metric_meta(py_m, tcfg)["label"],
        )
        st.plotly_chart(fig, width="stretch")
        on_front = bool((front["fips"] == ref_fips).any()) if len(ref) else False
        st.caption(
            f"{len(front)} counties on the front. {ref_name} is "
            f"{'on' if on_front else 'not on'} the front. Current best is {best['county']}, {best['state']}."
        )


if __name__ == "__main__":
    main()
