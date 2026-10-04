"""Copy of the platform RankResponse / SiteScore contract (siting-platform/backend/app/scoring/schemas.py)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SiteScore(BaseModel):
    site_id: str
    name: str
    state: str = Field(description="Two-letter state code")
    county_fips: str | None = Field(default=None, description="5-digit county FIPS, used to join community signals")
    lat: float
    lon: float
    score: float = Field(ge=0, le=100, description="Sustainability score from the ML model")
    rank: int | None = None
    pillars: dict[str, float] = Field(default_factory=dict, description="Pillar scores 0-100")
    factors: dict[str, float | None] = Field(default_factory=dict, description="Raw factor values")
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    excluded: bool = False
    exclusion_reason: str | None = None
    attributes: dict[str, float | str | None] = Field(
        default_factory=dict,
        description="Extra inputs for the Social Accord trade-off engine: land, water, jobs, heat and community context",
    )


class RankRequest(BaseModel):
    n: int = Field(default=10, ge=1, le=500)
    weights: dict[str, float] | None = None


class RankResponse(BaseModel):
    model_version: str
    illustrative: bool = False
    sites: list[SiteScore]
