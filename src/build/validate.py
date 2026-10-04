"""Validation report (reports/validation_report.md) and one quantile choropleth per feature (reports/maps/)."""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.build.feature_specs import S  # noqa: E402
from src.common.counties import load_counties  # noqa: E402
from src.common.io import PROCESSED, REPORTS, STATUS_JSON  # noqa: E402

SPOT = {"51107": "Loudoun VA", "04013": "Maricopa AZ", "17031": "Cook IL", "48201": "Harris TX",
        "53033": "King WA", "13097": "Douglas GA", "22083": "Richland LA", "48441": "Taylor TX",
        "56021": "Laramie WY", "19153": "Polk IA"}
MISSING_FLAG_PCT = 20.0
TOL = 1e-9  # area-weighted means can exceed a bound by float rounding (e.g. 5 + 9e-16)
MAPS = REPORTS / "maps"


def range_rules(col: str, unit: str) -> tuple[float | None, float | None]:
    if "percent 0-100" in unit or "percentile 0-100" in unit or "score 0-100" in unit:
        return 0, 100
    if col in ("crb_grid_co2_kg_mwh", "crb_lrmer_2035_kg_mwh"):
        return 0, 1200
    if "score 0-5" in unit:
        return 0, 5
    if "fraction 0-1" in unit or unit in ("0/1", "0/0.5/1"):
        return 0, 1
    if col.endswith("_km") or unit in ("count", "MW", "km", "Mgal/d", "TBtu/yr", "t CO2e/yr", "sq ft", "hours/yr",
                                       "days/yr", "people", "km2", "people/km2", "years", "minutes/yr",
                                       "interruptions/yr", "degree-days F", "cents/kWh", "L/kWh", "deg C"):
        return 0, None
    return None, None


def _fmt(v) -> str:
    if pd.isna(v):
        return "NaN"
    if isinstance(v, (int, np.integer)) or (isinstance(v, float) and v.is_integer() and abs(v) < 1e9):
        return f"{v:,.0f}"
    return f"{v:,.3g}" if abs(v) < 1000 else f"{v:,.0f}"


def column_stats(df: pd.DataFrame, names: pd.Series) -> tuple[list[str], list[str], list[str]]:
    rows, flags, violations = [], [], []
    for col, (desc, unit, *_rest) in S.items():
        if col == "fips":
            continue
        s = df[col]
        miss = 100 * s.isna().mean()
        if miss > MISSING_FLAG_PCT:
            flags.append(f"| `{col}` | {miss:.1f}% | {_rest[0]} |")
        if not pd.api.types.is_numeric_dtype(s):
            vc = s.value_counts().head(5)
            top = ", ".join(f"{k} ({v})" for k, v in vc.items())
            rows.append(f"| `{col}` | {unit} | {miss:.1f} | | | | {top} | |")
            continue
        lo, hi = range_rules(col, unit)
        if s.notna().any():
            if lo is not None and (s < lo - TOL).any():
                violations.append(f"- `{col}`: {(s < lo - TOL).sum()} values < {lo} (min {_fmt(s.min())})")
            if hi is not None and (s > hi + TOL).any():
                violations.append(f"- `{col}`: {(s > hi + TOL).sum()} values > {hi} (max {_fmt(s.max())})")
            srt = s.dropna().sort_values()
            top = ", ".join(f"{names[i]} {_fmt(srt[i])}" for i in srt.index[::-1][:5])
            bot = ", ".join(f"{names[i]} {_fmt(srt[i])}" for i in srt.index[:5])
            rows.append(f"| `{col}` | {unit} | {miss:.1f} | {_fmt(s.min())} | {_fmt(s.max())} | {_fmt(s.mean())} "
                        f"| {top} | {bot} |")
        else:
            rows.append(f"| `{col}` | {unit} | {miss:.1f} | | | | | |")
    return rows, flags, violations


def spot_table(df: pd.DataFrame) -> list[str]:
    sub = df.set_index("fips").loc[list(SPOT)]
    lines = ["| column | " + " | ".join(f"{v} ({k})" for k, v in SPOT.items()) + " |",
             "|---|" + "---|" * len(SPOT)]
    for col in S:
        if col in ("fips", "meta_county_name", "meta_state_abbr", "meta_state_fips"):
            continue
        lines.append(f"| `{col}` | " + " | ".join(_fmt(v) if not isinstance(v, str) else v for v in sub[col]) + " |")
    return lines


def maps(df: pd.DataFrame) -> int:
    MAPS.mkdir(parents=True, exist_ok=True)
    g = load_counties()[["fips", "geometry"]].to_crs(5070)
    g["geometry"] = g.geometry.simplify(2000)
    g = g.merge(df, on="fips", how="left")
    n = 0
    for col, (desc, unit, _src, _join, higher, _n) in S.items():
        if higher == "id" or not pd.api.types.is_numeric_dtype(df[col]) or df[col].notna().sum() == 0:
            continue
        s = g[col]
        fig, ax = plt.subplots(figsize=(11, 6.5))
        if s.isna().any():
            g[s.isna()].plot(ax=ax, color="#d9d9d9", linewidth=0)
        valid = g[s.notna()].copy()
        try:
            valid["_q"] = pd.qcut(valid[col].rank(method="first"), 5, labels=False)
            edges = valid.groupby("_q")[col].agg(["min", "max"])
            labels = [f"{_fmt(a)} – {_fmt(b)}" for a, b in edges.itertuples(index=False)]
        except ValueError:
            valid["_q"], labels = 0, [f"{_fmt(valid[col].min())} – {_fmt(valid[col].max())}"]
        cmap = plt.get_cmap("viridis", max(len(labels), 2))
        valid.plot(ax=ax, column="_q", cmap=cmap, linewidth=0, categorical=True)
        handles = [plt.Rectangle((0, 0), 1, 1, color=cmap(i)) for i in range(len(labels))]
        handles.append(plt.Rectangle((0, 0), 1, 1, color="#d9d9d9"))
        ax.legend(handles, labels + [f"NaN ({int(s.isna().sum())})"], loc="lower left", fontsize=8,
                  title=f"quintiles ({unit})", title_fontsize=8, frameon=False)
        ax.set_title(f"{col}\n{desc}", fontsize=10)
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(MAPS / f"{col}.png", dpi=90)
        plt.close(fig)
        n += 1
    return n


def main():
    df = pd.read_parquet(PROCESSED / "county_features.parquet")
    names = (df["meta_county_name"].str.replace(r" (County|Parish|city|City|Planning Region)$", "", regex=True)
             + " " + df["meta_state_abbr"])
    status = json.loads(STATUS_JSON.read_text()) if STATUS_JSON.exists() else {}
    rows, flags, violations = column_stats(df, names)
    n_maps = maps(df)

    fips_ok = df["fips"].str.fullmatch(r"\d{5}").all()
    out = ["# Validation report", "",
           f"- Rows: **{len(df)}** (expected 3,109 = CONUS + DC, CT planning regions) - "
           f"{'OK' if len(df) == 3109 else 'MISMATCH'}",
           f"- `fips`: unique = {df['fips'].is_unique}, all 5-digit strings = {fips_ok}, "
           f"dtype = {df['fips'].dtype}",
           f"- Columns: {df.shape[1]}; choropleth maps written: {n_maps} (reports/maps/)", "",
           "## Source status", "", "| Source | Status | Message |", "|---|---|---|"]
    order = {"FAILED": 0, "BLOCKED": 1, "PARTIAL": 2, "SKIPPED": 3, "OK": 4}
    for k, v in sorted(status.items(), key=lambda kv: (order.get(kv[1]["status"], 9), kv[0])):
        out.append(f"| `{k}` | {v['status']} | {v['message'][:220].replace('|', '/')} |")
    out += ["", f"## Columns with > {MISSING_FLAG_PCT:.0f}% missing", "", "| Column | Missing | Source |", "|---|---|---|",
            *(flags or ["| (none) | | |"]), "", "## Range checks", "",
            "Rules: percent/percentile/score-100 columns in [0, 100]; CO2 rates in [0, 1200]; Aqueduct scores in "
            "[0, 5]; fractions and flags in [0, 1]; distances, counts, MW, flows, etc. >= 0.", "",
            *(violations or ["All range checks passed."]), "",
            "## Spot checks", "", *spot_table(df), "",
            "## Per-column summary", "",
            "| Column | Unit | % missing | Min | Max | Mean | Top 5 | Bottom 5 |", "|---|---|---|---|---|---|---|---|",
            *rows, ""]
    (REPORTS / "validation_report.md").write_text("\n".join(out))
    print(f"[validate] report written; {len(flags)} columns > {MISSING_FLAG_PCT}% missing; "
          f"{len(violations)} range violations; {n_maps} maps")


if __name__ == "__main__":
    main()
