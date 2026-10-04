"""Reusable join methods. All area and distance work is done in EPSG:5070 (Albers Equal Area).

1. table_join                  source already has FIPS
2. points_to_county            count / sum of points per county (0 where none)
3. raster_class_pct / raster_mean   exactextract zonal statistics (coverage-weighted)
4. polygon_area_weighted_mean  sum(value * overlap) / sum(overlap)
   polygon_coverage_pct        % of county area covered by (dissolved) polygons
   line_length_km              length of lines inside each county (0 where none)
5. nearest_distance_km         population centroid -> nearest feature (sjoin_nearest)
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .fips_fixes import apply_fips_fixes, normalize_fips

ALBERS = "EPSG:5070"


def _albers(g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if g.crs is None:
        raise ValueError("GeoDataFrame has no CRS")
    return g if g.crs.to_epsg() == 5070 else g.to_crs(ALBERS)


def _all_fips(counties: gpd.GeoDataFrame) -> pd.DataFrame:
    return counties[["fips"]].drop_duplicates().reset_index(drop=True)


# 1 ------------------------------------------------------------------------------ table join

def table_join(df: pd.DataFrame, fips_col: str, how: dict[str, str], source: str) -> pd.DataFrame:
    """Zero-pad FIPS, apply fips_fixes (renames, CT crosswalk, scope), return fips + value cols."""
    out = normalize_fips(df, fips_col)
    return apply_fips_fixes(out, how, source=source)


# 2 -------------------------------------------------------------------------- points to county

def points_to_county(points: gpd.GeoDataFrame, counties: gpd.GeoDataFrame, out_col: str,
                     value_col: str | None = None, agg: str = "count") -> pd.DataFrame:
    """Spatially join points to counties. agg='count' or 'sum' of value_col. Missing -> 0."""
    pts = points[points.geometry.notna() & ~points.geometry.is_empty]
    pts = _albers(pts)
    cty = _albers(counties[["fips", "geometry"]])
    j = gpd.sjoin(pts, cty, how="inner", predicate="intersects")
    j = j[~j.index.duplicated(keep="first")]  # a point on a shared border counts once
    if agg == "count":
        s = j.groupby("fips").size()
    elif agg == "sum":
        s = j.groupby("fips")[value_col].sum()
    else:
        raise ValueError(agg)
    out = _all_fips(counties).merge(s.rename(out_col).reset_index(), on="fips", how="left")
    out[out_col] = out[out_col].fillna(0)
    return out


# 3 ------------------------------------------------------------------------ raster to county

def _vector_for_raster(counties: gpd.GeoDataFrame, raster_path: str | Path) -> gpd.GeoDataFrame:
    import rasterio
    with rasterio.open(raster_path) as src:
        crs = src.crs
    return counties[["fips", "geometry"]].to_crs(crs)


def raster_class_pct(raster_path: str | Path, counties: gpd.GeoDataFrame,
                     groups: dict[str, list[int]], **ee_kwargs) -> pd.DataFrame:
    """Percent (0-100) of each county's valid raster area in each class group.

    Uses exactextract 'unique' + 'frac', which weight every cell by the fraction of the
    cell covered by the polygon. Nodata cells are excluded from the denominator.
    """
    from exactextract import exact_extract

    vec = _vector_for_raster(counties, raster_path)
    res = exact_extract(str(raster_path), vec, ["unique", "frac"], include_cols=["fips"],
                        output="pandas", **ee_kwargs)
    rows = []
    for fips, uniq, frac in zip(res["fips"], res["unique"], res["frac"]):
        lut = dict(zip(np.asarray(uniq).astype(int), np.asarray(frac, dtype=float)))
        rec = {"fips": fips}
        for name, classes in groups.items():
            rec[name] = 100.0 * sum(lut.get(c, 0.0) for c in classes) if lut else np.nan
        rows.append(rec)
    return _all_fips(counties).merge(pd.DataFrame(rows), on="fips", how="left")


def raster_mean(raster_path: str | Path, counties: gpd.GeoDataFrame, out_col: str,
                **ee_kwargs) -> pd.DataFrame:
    """Coverage-weighted mean of a continuous raster per county."""
    from exactextract import exact_extract

    vec = _vector_for_raster(counties, raster_path)
    res = exact_extract(str(raster_path), vec, ["mean"], include_cols=["fips"], output="pandas", **ee_kwargs)
    res = res.rename(columns={"mean": out_col})
    return _all_fips(counties).merge(res[["fips", out_col]], on="fips", how="left")


# 4 ---------------------------------------------------------------------- polygons / lines

def _pairwise_intersection(src: gpd.GeoDataFrame, counties: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Intersect every source feature with every county it touches (both in EPSG:5070)."""
    src = _albers(src)
    cty = _albers(counties[["fips", "geometry"]]).reset_index(drop=True)
    src = src[src.geometry.notna() & ~src.geometry.is_empty].reset_index(drop=True)
    src["geometry"] = shapely.make_valid(src.geometry.values)
    j = gpd.sjoin(src, cty, how="inner", predicate="intersects")
    a = src.geometry.values[j.index.values]
    b = cty.geometry.values[j["index_right"].values]
    inter = shapely.intersection(a, b)
    out = j.drop(columns=["index_right"]).copy()
    out["geometry"] = inter
    return gpd.GeoDataFrame(out, geometry="geometry", crs=ALBERS)


def polygon_area_weighted_mean(src: gpd.GeoDataFrame, value_cols: list[str],
                               counties: gpd.GeoDataFrame) -> pd.DataFrame:
    """sum(value * overlap_area) / sum(overlap_area) per county; NaN values are ignored."""
    src = src[[*value_cols, "geometry"]]
    ov = _pairwise_intersection(src, counties)
    ov["_a"] = ov.geometry.area
    ov = ov[ov["_a"] > 0]
    rows = {}
    for c in value_cols:
        v = pd.to_numeric(ov[c], errors="coerce")
        ok = v.notna()
        num = (v[ok] * ov.loc[ok, "_a"]).groupby(ov.loc[ok, "fips"]).sum()
        den = ov.loc[ok, "_a"].groupby(ov.loc[ok, "fips"]).sum()
        rows[c] = num / den
    res = pd.DataFrame(rows).reset_index().rename(columns={"index": "fips"})
    return _all_fips(counties).merge(res, on="fips", how="left")


def polygon_area_weighted_sum(src: gpd.GeoDataFrame, value_cols: list[str],
                              counties: gpd.GeoDataFrame) -> pd.DataFrame:
    """Split each source polygon's totals across counties by area share: sum(value * overlap / src_area).

    Counties touched by no source polygon get NaN; NaN values contribute nothing."""
    src = _albers(src[[*value_cols, "geometry"]]).reset_index(drop=True)
    src["_src_a"] = src.geometry.area
    ov = _pairwise_intersection(src, counties)
    ov["_w"] = ov.geometry.area / ov["_src_a"]
    ov = ov[ov["_w"] > 0]
    res = pd.DataFrame({c: (pd.to_numeric(ov[c], errors="coerce") * ov["_w"]).groupby(ov["fips"]).sum(min_count=1)
                        for c in value_cols}).reset_index().rename(columns={"index": "fips"})
    return _all_fips(counties).merge(res, on="fips", how="left")


def polygon_coverage_pct(src: gpd.GeoDataFrame, counties: gpd.GeoDataFrame, out_col: str,
                         dissolve: bool = True) -> pd.DataFrame:
    """Percent (0-100) of each county's area covered by `src` polygons (overlaps dissolved)."""
    src = _albers(src[["geometry"]])
    src = src[src.geometry.notna() & ~src.geometry.is_empty].copy()
    src["geometry"] = shapely.make_valid(src.geometry.values)
    ov = _pairwise_intersection(src, counties)
    if dissolve:
        ov = ov.dissolve(by="fips").reset_index()  # union per county removes double counting
    ov["_a"] = ov.geometry.area
    area = ov.groupby("fips")["_a"].sum()
    cty = _albers(counties[["fips", "geometry"]])
    cty_area = pd.Series(cty.geometry.area.values, index=cty["fips"].values)
    pct = (100.0 * area / cty_area.reindex(area.index)).clip(upper=100.0)
    out = _all_fips(counties).merge(pct.rename(out_col).reset_index().rename(columns={"index": "fips"}),
                                    on="fips", how="left")
    out[out_col] = out[out_col].fillna(0.0)
    return out


def line_length_km(lines: gpd.GeoDataFrame, counties: gpd.GeoDataFrame, out_col: str) -> pd.DataFrame:
    """Total length (km) of line features inside each county. Counties with none -> 0."""
    ov = _pairwise_intersection(lines[["geometry"]], counties)
    ov["_km"] = ov.geometry.length / 1000.0
    s = ov.groupby("fips")["_km"].sum()
    out = _all_fips(counties).merge(s.rename(out_col).reset_index(), on="fips", how="left")
    out[out_col] = out[out_col].fillna(0.0)
    return out


# 5 --------------------------------------------------------------------------- distances

def nearest_distance_km(centroids: gpd.GeoDataFrame, features: gpd.GeoDataFrame, out_col: str,
                        all_fips: pd.DataFrame | None = None) -> pd.DataFrame:
    """Distance (km) from each county population centroid to the nearest feature, EPSG:5070."""
    c = _albers(centroids[["fips", "geometry"]])
    f = _albers(features[["geometry"]])
    f = f[f.geometry.notna() & ~f.geometry.is_empty].reset_index(drop=True)
    if len(f) == 0:
        raise ValueError(f"no features for {out_col}")
    j = gpd.sjoin_nearest(c, f, how="left", distance_col="_d")
    s = j.groupby("fips")["_d"].min() / 1000.0
    base = all_fips if all_fips is not None else c[["fips"]]
    return base[["fips"]].merge(s.rename(out_col).reset_index(), on="fips", how="left")
