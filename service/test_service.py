"""Contract tests for the scoring service. Uses a copy of the platform pydantic models."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from service.main import app
from service.test_schemas import RankResponse, SiteScore

client = TestClient(app)

# scoring.yaml carbon-first persona × 100 (slider units)
CARBON_FIRST = {
    "power": 15,
    "carbon": 35,
    "water": 20,
    "permission": 10,
    "hazard": 10,
    "land": 5,
    "cobenefit": 5,
}

# outputs/sanity_report.md §4 carbon-first top 10
CARBON_FIRST_TOP10 = [
    "53005",  # Benton County, WA
    "41051",  # Multnomah County, OR
    "53073",  # Whatcom County, WA
    "53053",  # Pierce County, WA
    "41005",  # Clackamas County, OR
    "53011",  # Clark County, WA
    "41039",  # Lane County, OR
    "53077",  # Yakima County, WA
    "53033",  # King County, WA
    "53037",  # Kittitas County, WA
]


def _timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, (time.perf_counter() - t0) * 1000


def test_rank_response_matches_platform_contract():
    response = client.post("/rank", json={"n": 5})
    assert response.status_code == 200
    RankResponse.model_validate(response.json())
    assert response.json()["illustrative"] is False


def test_default_rank_top1_is_cowlitz():
    response = client.post("/rank", json={"n": 1})
    assert response.status_code == 200
    top = response.json()["sites"][0]
    assert top["county_fips"] == "53015"
    assert top["site_id"] == "53015"
    assert top["state"] == "WA"
    assert top["rank"] == 1


def test_carbon_first_rank_matches_sanity_report():
    response = client.post("/rank", json={"n": 10, "weights": CARBON_FIRST})
    assert response.status_code == 200
    fips = [site["county_fips"] for site in response.json()["sites"]]
    assert fips == CARBON_FIRST_TOP10


def test_manhattan_is_excluded_with_reason():
    response = client.get("/sites/36061")
    assert response.status_code == 200
    body = response.json()
    SiteScore.model_validate(body)
    assert body["excluded"] is True
    assert body["exclusion_reason"]
    assert "36061" in {body["site_id"], body["county_fips"]}


def test_unknown_fips_is_404():
    response = client.get("/sites/99999")
    assert response.status_code == 404


def test_solve_co2_cap_returns_cowlitz_first():
    response = client.post(
        "/engine/solve",
        json={"objective": "score", "constraints": [["co2_t", "<=", 25000]]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["best"]["fips"] == "53015"
    assert body["n_feasible"] >= 1


def test_lowest_co2_within_4_years_is_alameda_with_ttp_tags():
    response = client.post(
        "/engine/solve",
        json={"objective": "co2_t", "constraints": [["time_to_power_yrs", "<=", 4]], "min_score": 0.6},
    )
    assert response.status_code == 200
    best = response.json()["best"]
    assert best["fips"] == "06001"
    assert "time_to_power_tag" in best
    cowlitz = client.post("/engine/solve", json={"objective": "score"}).json()["best"]
    assert cowlitz["time_to_power_tag"] == "judgment"


def test_every_route_answers_under_200ms():
    calls = [
        lambda: client.get("/meta"),
        lambda: client.post("/rank", json={"n": 10}),
        lambda: client.get("/sites/53015"),
        lambda: client.post("/engine/solve", json={"objective": "score", "constraints": [["co2_t", "<=", 25000]]}),
        lambda: client.post("/engine/sweep", json={"metric": "time_to_power_yrs", "values": [6, 5, 4]}),
        lambda: client.get("/engine/pareto", params={"x": "co2_t", "y": "energy_cost_musd", "min_score": 0.6}),
    ]
    for call in calls:
        response, ms = _timed(call)
        assert response.status_code == 200, response.text
        assert ms < 200, f"{call} took {ms:.1f} ms"
