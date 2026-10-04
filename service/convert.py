"""Map our county rows onto the platform SiteScore / /meta shapes. No scoring math lives here."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.score.score import feat_col

PILLAR_META = [
    {"id": "power", "label": "Power", "hint": "Grid access, price, reliability and time to connect"},
    {"id": "carbon", "label": "Carbon", "hint": "Long-run marginal grid emissions and clean supply"},
    {"id": "water", "label": "Water", "hint": "Water stress now and in 2050, and water used by power plants"},
    {"id": "permission", "label": "Permission", "hint": "Moratoria, past local fights, zoning and incentives"},
    {"id": "hazard", "label": "Climate risk", "hint": "Floods, wildfire, quakes, storms and future heat"},
    {"id": "land", "label": "Land", "hint": "Buildable land, fiber, highways, brownfields and materials"},
    {"id": "cobenefit", "label": "Co-benefits", "hint": "Local economic need and waste-heat demand"},
]

PRESET_LABELS = {
    "base": ("base", "Balanced"),
    "carbon-first": ("carbon_first", "Carbon first"),
    "cost-first": ("cost_first", "Cost first"),
    "community-first": ("community_first", "Community first"),
}

FACTOR_META = [
    {"id": "co2_t", "pillar": "carbon", "label": "CO2 for a 100 MW campus", "better": "low", "unit": "tCO2/yr"},
    {"id": "co2_avg_grid_t", "pillar": "carbon", "label": "CO2 from today's average grid (reference only)", "better": "low", "unit": "tCO2/yr"},
    {"id": "water_ml", "pillar": "water", "label": "Water (direct + grid-indirect)", "better": "low", "unit": "million L/yr"},
    {"id": "energy_cost_musd", "pillar": "power", "label": "Energy cost (electricity only)", "better": "low", "unit": "$M/yr"},
    {"id": "time_to_power_yrs", "pillar": "power", "label": "Time to power", "better": "low", "unit": "years"},
    {"id": "water_stress_2050", "pillar": "water", "label": "Water stress 2050", "better": "low", "unit": "0-5"},
    {"id": "pue", "pillar": "carbon", "label": "PUE (assumption)", "better": "low", "unit": "ratio"},
    {"id": "crb_lrmer_2035_kg_mwh", "pillar": "carbon", "label": "Long-run marginal grid CO2", "better": "low", "unit": "kg/MWh"},
    {"id": "crb_grid_co2_kg_mwh", "pillar": "carbon", "label": "Average-grid CO2", "better": "low", "unit": "kg/MWh"},
    {"id": "wtr_bws_score", "pillar": "water", "label": "Baseline water stress", "better": "low", "unit": "0-5"},
    {"id": "wtr_grid_water_l_kwh", "pillar": "water", "label": "Power-plant water use", "better": "low", "unit": "L/kWh"},
    {"id": "pwr_ind_price_cents_kwh", "pillar": "power", "label": "Industrial electricity price", "better": "low", "unit": "¢/kWh"},
    {"id": "pwr_dist_hv230_line_km", "pillar": "power", "label": "Distance to 230 kV line", "better": "low", "unit": "km"},
    {"id": "haz_days_gt95f_2050", "pillar": "hazard", "label": "Days above 95°F in 2050", "better": "low", "unit": "days"},
    {"id": "cob_unemp_rate", "pillar": "cobenefit", "label": "Unemployment rate", "better": "high", "unit": "%"},
]

CAMPUS_FACTORS = (
    "co2_t", "co2_avg_grid_t", "water_ml", "energy_cost_musd",
    "time_to_power_yrs", "water_stress_2050", "pue", "pct_top10_nudged",
)

FEATURE_TEXT = {
    "pwr_ind_price_cents_kwh": ("Industrial electricity price", "¢/kWh"),
    "pwr_saidi_min": ("Grid reliability (SAIDI)", "min/yr"),
    "pwr_dist_hv230_line_km": ("Distance to 230 kV line", "km"),
    "pwr_dist_hv345_line_km": ("Distance to 345 kV line", "km"),
    "pwr_substations_230kv_n": ("230 kV substations", ""),
    "pwr_time_to_power_yrs": ("Time to power", "years"),
    "pwr_dist_retired_plant_km": ("Distance to retired plant", "km"),
    "crb_lrmer_2035_kg_mwh": ("Long-run grid CO2", "kg/MWh"),
    "crb_grid_co2_kg_mwh": ("Average-grid CO2", "kg/MWh"),
    "crb_wind_cf": ("Wind capacity factor", ""),
    "crb_solar_cf": ("Solar capacity factor", ""),
    "crb_clean_gen_mw": ("Clean generation", "MW"),
    "crb_queue_clean_mw": ("Clean queue", "MW"),
    "wtr_bws_score": ("Water stress", "0-5"),
    "wtr_bws_2050_score": ("Water stress 2050", "0-5"),
    "wtr_grid_water_l_kwh": ("Power-plant water use", "L/kWh"),
    "wtr_drought_d2plus_pct_weeks": ("Drought weeks D2+", "%"),
    "wtr_wwtp_flow_mgd": ("WWTP flow", "MGD"),
    "haz_alr_riverine_flood": ("Riverine flood risk", "percentile"),
    "haz_alr_wildfire": ("Wildfire risk", "percentile"),
    "haz_alr_earthquake": ("Earthquake risk", "percentile"),
    "haz_alr_tornado": ("Tornado risk", "percentile"),
    "haz_alr_hurricane": ("Hurricane risk", "percentile"),
    "haz_alr_coastal_flood": ("Coastal flood risk", "percentile"),
    "haz_days_gt95f_2050": ("Days above 95°F in 2050", "days"),
    "haz_cdd_annual": ("Cooling degree days", "CDD"),
    "haz_karst_exposed_pct": ("Exposed karst", "%"),
    "lnd_pct_buildable": ("Buildable land", "%"),
    "lnd_dist_ixp_km": ("Distance to internet exchange", "km"),
    "lnd_dist_interstate_km": ("Distance to interstate", "km"),
    "lnd_dist_brownfield_or_retired_km": ("Distance to brownfield or retired plant", "km"),
    "lnd_dist_eaf_steel_km": ("Distance to EAF steel", "km"),
    "lnd_dist_cement_km": ("Distance to cement plant", "km"),
    "prm_moratorium_active": ("Active moratorium", ""),
    "prm_moratorium_proposed": ("Proposed moratorium", ""),
    "prm_contested_total": ("Contested projects nearby", ""),
    "prm_nonattainment": ("Air nonattainment", ""),
    "prm_pct_tribal": ("Tribal land share", "%"),
    "prm_price_growth_pct": ("Electricity price growth", "%"),
    "lnd_pct_cropland": ("Cropland", "%"),
    "prm_pop_density_km2": ("Population density", "/km²"),
    "prm_tax_exemption_status": ("Data-center tax status", ""),
    "prm_county_can_zone": ("County zoning authority", ""),
    "cob_unemp_rate": ("Unemployment rate", "%"),
    "cob_poverty_pct": ("Poverty rate", "%"),
    "cob_energy_community": ("Energy community", ""),
    "cob_persistent_poverty": ("Persistent poverty", ""),
    "cob_heat_demand": ("Heat demand", ""),
    "cob_ghgrp_combustion_facilities_n": ("Combustion facilities", ""),
    "cob_lowtemp_ind_heat_tbtu": ("Low-temperature industrial heat", "TBtu"),
}

FLAG_FEATURES = frozenset({
    "prm_moratorium_active", "prm_moratorium_proposed", "prm_nonattainment",
    "prm_county_can_zone", "cob_energy_community", "cob_persistent_poverty",
})

JUDGMENT_METRICS = frozenset({"pue", "wue", "time_to_power_yrs"})


def model_version_from(path: Path) -> str:
    day = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    return f"siting-geomean-{day}"


def presets_from_config(cfg: dict) -> list[dict]:
    out = []
    for key, (pid, label) in PRESET_LABELS.items():
        raw = (cfg.get("personas") or {}).get(key) or (cfg.get("weights") if key == "base" else None)
        if not raw:
            continue
        out.append({
            "id": pid,
            "label": label,
            "weights": {p: int(round(float(w) * 100)) for p, w in raw.items()},
        })
    return out


def metrics_from_config(tcfg: dict, frame: pd.DataFrame | None = None) -> list[dict]:
    rows = []
    for mid, meta in (tcfg.get("metrics") or {}).items():
        better = meta.get("better", "lower")
        rec = {
            "id": mid,
            "label": meta.get("label", mid),
            "unit": meta.get("unit", ""),
            "better": "low" if better == "lower" else "high",
            "judgment": bool(meta.get("judgment")) or mid in JUDGMENT_METRICS or "judgment" in str(meta.get("label", "")).lower(),
        }
        if frame is not None and mid in frame.columns:
            series = pd.to_numeric(frame[mid], errors="coerce")
            rec["min"] = fnum(series.min())
            rec["max"] = fnum(series.max())
        rows.append(rec)
    return rows


def normalize_slider_weights(weights: dict | None, pillar_ids: list[str]) -> dict | None:
    """Slider values (0-100) → unit weights that sum to 1. None means use base weights."""
    if not weights:
        return None
    known = set(pillar_ids)
    cleaned = {k: float(v) for k, v in weights.items() if k in known}
    if not cleaned or sum(cleaned.values()) <= 0:
        return None
    total = sum(cleaned.values())
    return {k: v / total for k, v in cleaned.items()}


def fnum(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(out) else out


def jsonable(obj):
    """Convert pandas / numpy / NaN into plain JSON types."""
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        return [jsonable(rec) for rec in obj.to_dict(orient="records")]
    if isinstance(obj, pd.Series):
        return jsonable(obj.to_dict())
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        val = float(obj)
        return None if not np.isfinite(val) else val
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(obj, "item") and not isinstance(obj, (bytes, str, dict, list)):
        try:
            return jsonable(obj.item())
        except (ValueError, AttributeError):
            pass
    return obj


def _fmt_number(value: float) -> str:
    av = abs(value)
    if av >= 100:
        return f"{value:,.1f}"
    if av >= 10:
        return f"{value:.1f}"
    if av >= 1:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:.3g}"


def format_feature(col: str, raw_row: pd.Series) -> str | None:
    if not col:
        return None
    label, unit = FEATURE_TEXT.get(col, (col.replace("_", " "), ""))
    raw = raw_row[col] if col in raw_row.index else None
    if raw is None or (not isinstance(raw, str) and pd.isna(raw)):
        return f"{label}: n/a"
    if isinstance(raw, str):
        text = raw.strip()
        return f"{label}: {text}" if text else f"{label}: n/a"
    num = fnum(raw)
    if num is None:
        return f"{label}: n/a"
    if col in FLAG_FEATURES:
        word = "no" if num == 0 else ("yes" if num == 1 else "partial")
        return f"{label}: {word}"
    pretty = _fmt_number(num)
    return f"{label}: {pretty} {unit}".strip() if unit else f"{label}: {pretty}"


def time_to_power_tag(source: str | None) -> str | None:
    if not source or source in ("none", "nan"):
        return None
    if source == "constrained_judgment":
        return "judgment"
    if source == "national":
        return "national default"
    return source


def feature_score_cols(cfg: dict, columns) -> list[str]:
    have = set(columns)
    return [feat_col(spec) for spec in cfg["features"] if feat_col(spec) in have]


def pillar_pct(row: pd.Series, pillar_ids: list[str]) -> dict[str, float]:
    out = {}
    for p in pillar_ids:
        val = fnum(row.get(p))
        out[p] = round(100.0 * val, 1) if val is not None else 0.0
    return out


def row_factors(raw: pd.Series) -> dict[str, float | None]:
    return {key: fnum(raw.get(key)) for key in CAMPUS_FACTORS}


def row_attributes(raw: pd.Series, pillar_row: pd.Series, heat_score: float | None) -> dict[str, float | str | None]:
    hazard = fnum(pillar_row.get("hazard"))
    days = fnum(raw.get("haz_days_gt95f_2050"))
    cdd = fnum(raw.get("haz_cdd_annual"))
    contested = (fnum(raw.get("prm_contested_n")) or 0.0) + (fnum(raw.get("prm_contested_neighbors_n")) or 0.0)
    source = raw.get("pwr_time_to_power_source")
    source_s = None if source is None or (not isinstance(source, str) and pd.isna(source)) else str(source)
    ttp = fnum(raw.get("pwr_time_to_power_yrs"))
    return {
        "carbon": fnum(raw.get("crb_grid_co2_kg_mwh")),
        "tx_km": fnum(raw.get("pwr_dist_hv230_line_km")),
        "time_to_power": ttp,
        "time_to_power_years": ttp,
        "time_to_power_source": source_s,
        "time_to_power_tag": time_to_power_tag(source_s),
        "water_stress": fnum(raw.get("wtr_bws_score")),
        "plant_water": fnum(raw.get("wtr_grid_water_l_kwh")),
        "hazard_risk": None if hazard is None else 100.0 * (1.0 - hazard),
        "reuse_km": fnum(raw.get("lnd_dist_brownfield_or_retired_km")),
        "opposition": contested,
        "unemployment": fnum(raw.get("cob_unemp_rate")),
        "heat_need": None if heat_score is None else 100.0 * heat_score,
        "climate_adversity": None if days is None else 100.0 * min(1.0, days / 120.0),
        "free_cooling": None if cdd is None else 100.0 * (1.0 - min(1.0, cdd / 4000.0)),
        "free_cooling_basis": "proxy from cooling degree days",
    }


def to_site_score(
    fips: str,
    raw: pd.Series,
    pillar_row: pd.Series,
    strongest: list[str],
    weakest: list[str],
    pillar_ids: list[str],
    score: float | None,
    rank: int | None,
) -> dict:
    county = str(raw.get("meta_county_name") or pillar_row.get("county") or fips)
    state = str(raw.get("meta_state_abbr") or pillar_row.get("state") or "")
    excluded = bool(int(pillar_row.get("excluded") or 0))
    reason = pillar_row.get("failed_rules")
    if reason is not None and not isinstance(reason, str) and pd.isna(reason):
        reason = None
    reason_s = str(reason).strip() if reason else None
    heat = fnum(pillar_row.get("cob_heat_demand"))
    final = fnum(score)
    return {
        "site_id": fips,
        "name": f"{county}, {state}".strip().rstrip(","),
        "state": state,
        "county_fips": fips,
        "lat": float(raw.get("meta_pop_centroid_lat")),
        "lon": float(raw.get("meta_pop_centroid_lon")),
        "score": round(100.0 * final, 1) if final is not None else 0.0,
        "rank": rank,
        "pillars": pillar_pct(pillar_row, pillar_ids),
        "factors": row_factors(raw),
        "pros": [t for t in (format_feature(c, raw) for c in strongest) if t],
        "cons": [t for t in (format_feature(c, raw) for c in weakest) if t],
        "excluded": excluded,
        "exclusion_reason": reason_s if excluded else None,
        "attributes": row_attributes(raw, pillar_row, heat),
    }
