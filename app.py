"""Streamlit demo: recompute ranks from cached pillar scores (no raw table re-read)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.score.score import CONFIG_PATH, OUTPUTS, geometric_mean, load_config, pillar_list, rank_with_veto, weight_vector
from src.score.tradeoff import sacrifice

st.set_page_config(page_title="Data center siting", layout="wide")


@st.cache_data(show_spinner=False)
def load_artifacts() -> tuple[dict, pd.DataFrame, pd.DataFrame, dict]:
    cfg = load_config()
    cache = OUTPUTS / "score_cache.parquet"
    if cache.exists():
        scored = pd.read_parquet(cache)
    else:
        scored = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"fips": str})
        rob = pd.read_csv(OUTPUTS / "robustness.csv", dtype={"fips": str})
        scored = scored.merge(rob[["fips", "pct_top10_nudged", "pct_top10_agnostic",
                                   "median_rank_nudged"]], on="fips", how="left")
    scored["fips"] = scored["fips"].astype(str).str.zfill(5)
    excl_path = OUTPUTS / "exclusions.csv"
    excluded = pd.read_csv(excl_path, dtype={"fips": str}) if excl_path.exists() else pd.DataFrame()
    if not excluded.empty:
        excluded["fips"] = excluded["fips"].astype(str).str.zfill(5)
    geo_path = OUTPUTS / "counties.geojson"
    geo = json.loads(geo_path.read_text()) if geo_path.exists() else None
    return cfg, scored, excluded, geo


def apply_weights(scored: pd.DataFrame, cfg: dict, weights: dict) -> pd.DataFrame:
    cols = pillar_list(cfg)
    pillars = scored[cols]
    scores = geometric_mean(pillars, weight_vector(cfg, weights), floor=float(cfg.get("geo_mean_floor", 0.01)))
    rank, veto = rank_with_veto(scores, pillars, float(cfg.get("veto_threshold", 0.15)),
                               weight_vector(cfg, weights))
    out = scored.copy()
    out["final_score"] = scores.values
    out["rank"] = rank.values
    out["flag_veto"] = veto.values
    return out.sort_values(["rank", "fips"]).reset_index(drop=True)


def choropleth(df: pd.DataFrame, geo: dict, excluded: pd.DataFrame, show_excluded: bool, color: str) -> go.Figure:
    fig = px.choropleth(
        df, geojson=geo, locations="fips", featureidkey="properties.fips",
        color=color, hover_name="county",
        hover_data={"fips": True, "state": True, "rank": True, color: ":.3f"},
        color_continuous_scale="Viridis", scope="usa",
    )
    fig.update_traces(marker_line_width=0, marker_line_color="rgba(0,0,0,0)")
    fig.update_geos(showlakes=False, showocean=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=560, coloraxis_colorbar=dict(title="Score"))
    if show_excluded and not excluded.empty:
        gray = excluded[["fips", "county", "state"]].copy()
        gray["val"] = 0
        gfig = px.choropleth(
            gray, geojson=geo, locations="fips", featureidkey="properties.fips",
            color="val", hover_name="county", hover_data={"state": True, "fips": True},
            color_continuous_scale=[[0, "#c8c8c8"], [1, "#c8c8c8"]], scope="usa",
        )
        gfig.update_traces(marker_line_width=0, showscale=False, name="excluded")
        fig.add_trace(gfig.data[0])
        fig.data = (fig.data[-1],) + fig.data[:-1]
    return fig


def radar(row: pd.Series, cols: list[str]) -> go.Figure:
    fig = go.Figure(go.Scatterpolar(
        r=[float(row[c]) for c in cols] + [float(row[cols[0]])],
        theta=cols + [cols[0]],
        fill="toself",
        name=f"{row['county']}, {row['state']}",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 1], showticklabels=True, tickfont=dict(size=10))),
        margin=dict(l=40, r=40, t=30, b=20), height=320, showlegend=False,
    )
    return fig


def main() -> None:
    if not (OUTPUTS / "rankings.csv").exists() and not (OUTPUTS / "score_cache.parquet").exists():
        st.error("No scoring outputs yet. Run `python -m src.score.score` from the repo root.")
        return

    cfg, scored, excluded, geo = load_artifacts()
    cols = pillar_list(cfg)
    personas = cfg["personas"]

    st.title("AI data center siting")
    st.caption("Scores recompute from cached pillars. Exclusions and feature anchors stay fixed.")

    with st.sidebar:
        st.header("Weights")
        persona_names = list(personas)
        choice = st.selectbox("Persona", persona_names, index=persona_names.index("base"))
        if st.session_state.get("_persona") != choice:
            for p, v in personas[choice].items():
                st.session_state[f"w_{p}"] = float(v)
            st.session_state._persona = choice
        for p in cols:
            st.session_state.setdefault(f"w_{p}", float(personas[choice][p]))
        raw_w = {}
        for p in cols:
            raw_w[p] = st.slider(p, 0.0, 1.0, step=0.01, key=f"w_{p}")
        total = sum(raw_w.values()) or 1.0
        weights = {p: v / total for p, v in raw_w.items()}
        st.caption("Sliders are auto-normalized to 1.00")
        st.write({p: round(v, 3) for p, v in weights.items()})

        st.header("Trade-off")
        sacrifice_choice = st.selectbox("Sacrifice a pillar", ["(none)"] + cols)
        floor_pct = st.slider("Percentile floor on remaining pillars", 0, 90, 50, 5)
        show_excluded = st.toggle("Show excluded counties in gray", value=False)

    if sacrifice_choice != "(none)":
        view = sacrifice(scored, scored[cols], cfg, sacrifice_choice, floor_pct=floor_pct, weights=weights)
        title = f"Sacrificing {sacrifice_choice} · {len(view):,} counties pass p{floor_pct}"
    else:
        view = apply_weights(scored, cfg, weights)
        title = f"{len(view):,} counties · weighted geometric mean"

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        st.subheader(title)
        if geo is None:
            st.warning("Missing outputs/counties.geojson. Re-run `python -m src.score.score`.")
        else:
            fig = choropleth(view, geo, excluded, show_excluded, "final_score")
            event = st.plotly_chart(fig, width="stretch", on_select="rerun",
                                    selection_mode="points", key="map")
            clicked = None
            sel = getattr(event, "selection", None)
            points = getattr(sel, "points", None) if sel is not None else None
            if points:
                clicked = points[0].get("location") or points[0].get("hovertext")
            if clicked:
                st.session_state["picked"] = str(clicked).zfill(5)

    options = [f"{r.county}, {r.state} ({r.fips})" for r in view.itertuples()]
    default_fips = st.session_state.get("picked", view.iloc[0]["fips"] if len(view) else None)
    default_idx = 0
    if default_fips is not None:
        hits = np.where(view["fips"].to_numpy() == default_fips)[0]
        if len(hits):
            default_idx = int(hits[0])
    with right:
        st.subheader("Top 10")
        show_cols = ["rank", "county", "state", "final_score"] + cols
        if "pct_top10_nudged" in view.columns:
            show_cols.append("pct_top10_nudged")
        table = view.head(10)[show_cols].copy()
        for c in table.columns:
            if c not in ("rank", "county", "state") and pd.api.types.is_numeric_dtype(table[c]):
                table[c] = table[c].round(3)
        st.dataframe(table, width="stretch", hide_index=True,
                     column_config={"pct_top10_nudged": st.column_config.NumberColumn("% top-10 (nudged)")})

        if options:
            pick = st.selectbox("County", options, index=min(default_idx, len(options) - 1))
            fips = pick.rsplit("(", 1)[-1].rstrip(")")
            row = view[view["fips"] == fips].iloc[0]
            st.plotly_chart(radar(row, cols), width="stretch")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Strongest features**")
                for i in range(1, 4):
                    val = row.get(f"strongest_{i}", "")
                    if val:
                        st.write(f"{i}. `{val}`")
            with c2:
                st.markdown("**Weakest features**")
                for i in range(1, 4):
                    val = row.get(f"weakest_{i}", "")
                    if val:
                        st.write(f"{i}. `{val}`")
            flags = [c for c in view.columns if c.startswith("flag_") and int(row.get(c, 0) or 0) == 1]
            if flags:
                st.warning("Flags: " + ", ".join(flags))


if __name__ == "__main__":
    main()
