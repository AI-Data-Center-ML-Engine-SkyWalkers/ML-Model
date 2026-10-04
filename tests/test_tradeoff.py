"""Synthetic-frame tests for real-unit metrics and the trade-off engine."""
from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from src.score.metrics import add_campus_metrics, better_is_lower, it_energy_mwh, load_tradeoff_config
from src.score.score import apply_manual_adjustments, load_config
from src.score.tradeoff import compare, pareto2, solve, sweep

TCFG = load_tradeoff_config()
SCFG = load_config()


def _campus_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "fips": ["00001", "00002", "00003"],
        "haz_cdd_annual": [0.0, 1000.0, 10_000.0],
        "crb_lrmer_2035_kg_mwh": [100.0, 100.0, 100.0],
        "crb_grid_co2_kg_mwh": [200.0, 200.0, 200.0],
        "wtr_grid_water_l_kwh": [0.5, 0.5, 0.5],
        "wtr_bws_2050_score": [0.0, 1.0, 2.0],
        "pwr_ind_price_cents_kwh": [5.0, 10.0, 15.0],
        "pwr_time_to_power_yrs": [4.0, 6.0, 4.0],
    })


def test_pnw_region_rule_sets_ttp_and_large_load_price():
    cfg = {
        "manual_adjustments": {
            "pnw_constrained_ttp": {
                "years": 6,
                "basis": "constrained_judgment",
                "gea": "NorthernGrid_West",
                "column": "crb_cambium_gea",
                "large_load_price_cents_kwh": 7.75,
            }
        }
    }
    df = pd.DataFrame({
        "fips": ["53015", "19113"],
        "crb_cambium_gea": ["NorthernGrid_West", "MISO_North"],
        "pwr_time_to_power_yrs": [4.0, 4.0],
        "pwr_time_to_power_source": ["national", "national"],
        "pwr_ind_price_cents_kwh": [3.4, 8.0],
    })
    out = apply_manual_adjustments(df, cfg)
    wa = out.loc[out["fips"] == "53015"].iloc[0]
    ia = out.loc[out["fips"] == "19113"].iloc[0]
    assert wa["pwr_time_to_power_yrs"] == 6
    assert wa["pwr_time_to_power_source"] == "constrained_judgment"
    assert wa["pwr_ind_price_cents_kwh"] == 7.75
    assert ia["pwr_time_to_power_yrs"] == 4
    assert ia["pwr_ind_price_cents_kwh"] == 8.0


def test_pue_wue_cap_and_campus_formulas():
    out = add_campus_metrics(_campus_frame(), TCFG)
    it_mwh = it_energy_mwh(TCFG["campus"])
    assert it_mwh == 700_800.0
    assert out.loc[0, "pue"] == 1.10
    assert out.loc[0, "wue"] == 0.10
    assert abs(out.loc[1, "pue"] - 1.22) < 1e-12
    assert abs(out.loc[1, "wue"] - 0.30) < 1e-12
    assert out.loc[2, "pue"] == 1.40
    assert out.loc[2, "wue"] == 0.60
    assert abs(out.loc[0, "facility_mwh"] - it_mwh * 1.10) < 1e-8
    assert abs(out.loc[0, "co2_t"] - out.loc[0, "facility_mwh"] * 0.1) < 1e-8
    assert abs(out.loc[0, "energy_cost_musd"] - out.loc[0, "facility_mwh"] * 5.0 * 1e-5) < 1e-8


def _toy() -> pd.DataFrame:
    return pd.DataFrame({
        "fips": ["53015", "11111", "22222", "33333"],
        "county": ["Cowlitz County", "Cheap Hot", "Clean Slow", "Dry Cheap"],
        "state": ["WA", "TX", "OR", "NV"],
        "pue": [1.12, 1.35, 1.15, 1.30],
        "wue": [0.13, 0.40, 0.15, 0.35],
        "facility_mwh": [780_000, 900_000, 800_000, 880_000],
        "co2_t": [20_000, 80_000, 22_000, 50_000],
        "co2_avg_grid_t": [200_000, 180_000, 190_000, 210_000],
        "water_ml": [500.0, 900.0, 520.0, 400.0],
        "water_stress_2050": [0.0, 3.0, 0.5, 0.2],
        "energy_cost_musd": [45.0, 20.0, 50.0, 18.0],
        "time_to_power_yrs": [6.0, 4.0, 7.0, 4.0],
        "power": [0.70, 0.80, 0.55, 0.85],
        "carbon": [0.60, 0.30, 0.70, 0.40],
        "water": [0.85, 0.40, 0.80, 0.90],
        "permission": [0.80, 0.50, 0.70, 0.60],
        "hazard": [0.70, 0.20, 0.65, 0.40],
        "land": [0.73, 0.60, 0.50, 0.55],
        "cobenefit": [0.42, 0.70, 0.40, 0.30],
        "score": [0.68, 0.50, 0.60, 0.55],
        "pct_top10_nudged": [90.0, 10.0, 20.0, 5.0],
    })


def test_solve_unconstrained_picks_highest_score():
    r = solve("score", metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG)
    assert r["n_feasible"] == 4
    assert r["best"]["fips"] == "53015"
    assert r["compare"].loc[r["compare"]["metric"] == "score", "change"].iloc[0] == "same"


def test_solve_co2_cap_filters_and_still_picks_cowlitz():
    r = solve("score", [("co2_t", "<=", 25000)], metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG)
    assert r["n_feasible"] == 2
    assert set(r["top"]["fips"]) == {"53015", "22222"}
    assert r["best"]["fips"] == "53015"


def test_solve_min_co2_with_fast_power():
    r = solve("co2_t", [("time_to_power_yrs", "<=", 4)], metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG,
              min_score=None)
    assert r["best"]["fips"] == "33333"
    assert r["n_feasible"] == 2


def test_metric_objective_applies_default_score_floor():
    r = solve("co2_t", [("time_to_power_yrs", "<=", 4)], metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG)
    assert r["n_feasible"] == 0
    r2 = solve("energy_cost_musd", metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG)
    assert r2["best"]["fips"] == "53015"
    assert r2["best"]["score"] >= 0.60


def test_ignore_hazard_recomputes_geometric_mean():
    r = solve("score", [("hazard", ">=", 0.3)], ignore_pillars=["hazard"],
              metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG)
    assert r["n_feasible"] == 3
    assert "11111" not in set(r["top"]["fips"])
    assert r["objective_value"] != r["best"]["score"]


def test_infeasible_reports_binding_and_loosest():
    r = solve("score", [("co2_t", "<=", 1000)], metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG)
    assert r["n_feasible"] == 0
    assert r["best"] is None
    assert r["binding"]["metric"] == "co2_t"
    assert r["binding"]["loosest_feasible"] == 20_000


def test_compare_marks_better_worse():
    toy = _toy()
    table = compare(toy.iloc[1], toy.iloc[0], TCFG)
    cost = table.loc[table["metric"] == "energy_cost_musd"].iloc[0]
    co2 = table.loc[table["metric"] == "co2_t"].iloc[0]
    score = table.loc[table["metric"] == "score"].iloc[0]
    assert cost["change"] == "better"
    assert co2["change"] == "worse"
    assert score["change"] == "worse"


def test_sweep_marks_winner_change():
    out = sweep("co2_t", [80_000, 50_000, 22_000, 20_000], metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG)
    assert list(out["fips"]) == ["53015", "53015", "53015", "53015"]
    assert not out["best_changed"].any()
    out2 = sweep("energy_cost_musd", [50.0, 20.0, 18.0], metrics=_toy(), tcfg=TCFG, scoring_cfg=SCFG,
                 min_score=None)
    assert list(out2["fips"]) == ["53015", "33333", "33333"]
    assert list(out2["best_changed"]) == [False, True, False]


def test_pareto2_respects_direction_and_sorts_x():
    front = pareto2("co2_t", "energy_cost_musd", metrics=_toy(), tcfg=TCFG)
    assert front["co2_t"].is_monotonic_increasing
    fips = set(front["fips"])
    assert fips == {"53015", "33333"}


def test_nan_energy_dropped_only_when_cost_is_in_play():
    toy = _toy()
    toy.loc[toy["fips"] == "11111", "energy_cost_musd"] = np.nan
    r = solve("score", metrics=toy, tcfg=TCFG, scoring_cfg=SCFG)
    assert r["n_feasible"] == 4
    assert r["n_dropped_energy_cost"] == 0
    r2 = solve("energy_cost_musd", metrics=toy, tcfg=TCFG, scoring_cfg=SCFG, min_score=None)
    assert r2["n_dropped_energy_cost"] == 1
    assert r2["n_feasible"] == 3
    assert r2["best"]["fips"] == "33333"
    r3 = solve("score", [("energy_cost_musd", "<=", 50)], metrics=toy, tcfg=TCFG, scoring_cfg=SCFG)
    assert r3["n_dropped_energy_cost"] == 1
    assert r3["n_feasible"] == 3


def test_yaml_defines_direction_for_every_metric():
    names = list(TCFG["metrics"])
    assert "co2_t" in names and "energy_cost_musd" in names
    assert better_is_lower("co2_t", TCFG)
    assert not better_is_lower("score", TCFG)
    dumped = yaml.safe_dump(TCFG)
    assert "judgment" in dumped
