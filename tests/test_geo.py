"""Synthetic checks: two 10 km x 10 km square 'counties' side by side in EPSG:5070.

    A = fips 00001, x in [0, 10 km]      B = fips 00002, x in [10, 20 km]
"""
import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, box

from src.common import geo
from src.common.fips_fixes import apply_fips_fixes, normalize_fips, zfill_fips

KM = 1000.0


@pytest.fixture
def counties():
    return gpd.GeoDataFrame(
        {"fips": ["00001", "00002"]},
        geometry=[box(0, 0, 10 * KM, 10 * KM), box(10 * KM, 0, 20 * KM, 10 * KM)],
        crs="EPSG:5070",
    )


def test_points_count_and_sum(counties):
    pts = gpd.GeoDataFrame(
        {"mw": [100.0, 50.0, 25.0]},
        geometry=[Point(1 * KM, 1 * KM), Point(2 * KM, 2 * KM), Point(15 * KM, 5 * KM)],
        crs="EPSG:5070",
    )
    n = geo.points_to_county(pts, counties, "n").set_index("fips")["n"]
    assert n.to_dict() == {"00001": 2, "00002": 1}
    s = geo.points_to_county(pts, counties, "mw", value_col="mw", agg="sum").set_index("fips")["mw"]
    assert s.to_dict() == {"00001": 150.0, "00002": 25.0}


def test_points_missing_county_is_zero(counties):
    pts = gpd.GeoDataFrame(geometry=[Point(1 * KM, 1 * KM)], crs="EPSG:5070")
    n = geo.points_to_county(pts, counties, "n").set_index("fips")["n"]
    assert n["00002"] == 0


def test_points_in_other_crs(counties):
    pts = gpd.GeoDataFrame(geometry=[Point(15 * KM, 5 * KM)], crs="EPSG:5070").to_crs(4326)
    n = geo.points_to_county(pts, counties.to_crs(4269), "n").set_index("fips")["n"]
    assert n.to_dict() == {"00001": 0, "00002": 1}


def test_raster_class_pct(tmp_path, counties):
    # 20 x 10 grid of 1 km cells. Left county: left 4 columns class 1, rest class 2.
    # Right county: all class 3, except one nodata column (excluded from denominator).
    arr = np.full((10, 20), 2, dtype=np.uint8)
    arr[:, 0:4] = 1
    arr[:, 10:20] = 3
    arr[:, 19] = 255
    path = tmp_path / "r.tif"
    with rasterio.open(path, "w", driver="GTiff", height=10, width=20, count=1, dtype="uint8",
                       crs="EPSG:5070", transform=from_origin(0, 10 * KM, KM, KM), nodata=255) as dst:
        dst.write(arr, 1)
    out = geo.raster_class_pct(path, counties, {"c1": [1], "c12": [1, 2], "c3": [3]}).set_index("fips")
    assert out.loc["00001", "c1"] == pytest.approx(40.0)
    assert out.loc["00001", "c12"] == pytest.approx(100.0)
    assert out.loc["00002", "c3"] == pytest.approx(100.0)
    assert out.loc["00002", "c1"] == pytest.approx(0.0)


def test_raster_mean_partial_cells(tmp_path, counties):
    # Cells of 4 km straddle the county border at x=10 km; values = column index.
    arr = np.tile(np.arange(5, dtype=np.float32), (3, 1))  # columns cover x in [0, 20]
    path = tmp_path / "m.tif"
    with rasterio.open(path, "w", driver="GTiff", height=3, width=5, count=1, dtype="float32",
                       crs="EPSG:5070", transform=from_origin(0, 12 * KM, 4 * KM, 4 * KM)) as dst:
        dst.write(arr, 1)
    out = geo.raster_mean(path, counties, "m").set_index("fips")["m"]
    # county A covers col0 (4 km), col1 (4 km), half of col2 (2 km): (0*4 + 1*4 + 2*2)/10 = 0.8
    assert out["00001"] == pytest.approx(0.8)
    # county B: half col2 (2 km), col3, col4: (2*2 + 3*4 + 4*4)/10 = 3.2
    assert out["00002"] == pytest.approx(3.2)


def test_polygon_area_weighted_mean(counties):
    # Source polygon P1 (value 10) covers x in [0, 15]; P2 (value 40) covers x in [15, 20].
    src = gpd.GeoDataFrame(
        {"v": [10.0, 40.0]},
        geometry=[box(0, 0, 15 * KM, 10 * KM), box(15 * KM, 0, 20 * KM, 10 * KM)],
        crs="EPSG:5070",
    )
    out = geo.polygon_area_weighted_mean(src, ["v"], counties).set_index("fips")["v"]
    assert out["00001"] == pytest.approx(10.0)
    assert out["00002"] == pytest.approx(25.0)  # half 10, half 40


def test_polygon_area_weighted_sum(counties):
    # P1 (total 30) covers x in [0, 15] -> 2/3 to A, 1/3 to B; P2 (total 8) half in B, half outside both.
    src = gpd.GeoDataFrame(
        {"v": [30.0, 8.0]},
        geometry=[box(0, 0, 15 * KM, 10 * KM), box(15 * KM, 0, 25 * KM, 10 * KM)],
        crs="EPSG:5070",
    )
    out = geo.polygon_area_weighted_sum(src, ["v"], counties).set_index("fips")["v"]
    assert out["00001"] == pytest.approx(20.0)
    assert out["00002"] == pytest.approx(10.0 + 4.0)


def test_polygon_coverage_dissolves_overlaps(counties):
    # Two overlapping polygons inside A, union = x in [0, 6] -> 60%; nothing in B.
    src = gpd.GeoDataFrame(
        geometry=[box(0, 0, 4 * KM, 10 * KM), box(2 * KM, 0, 6 * KM, 10 * KM)], crs="EPSG:5070"
    )
    out = geo.polygon_coverage_pct(src, counties, "pct").set_index("fips")["pct"]
    assert out["00001"] == pytest.approx(60.0)
    assert out["00002"] == pytest.approx(0.0)


def test_line_length(counties):
    lines = gpd.GeoDataFrame(geometry=[LineString([(5 * KM, 5 * KM), (17 * KM, 5 * KM)])], crs="EPSG:5070")
    out = geo.line_length_km(lines, counties, "km").set_index("fips")["km"]
    assert out["00001"] == pytest.approx(5.0)
    assert out["00002"] == pytest.approx(7.0)


def test_nearest_distance(counties):
    cents = gpd.GeoDataFrame({"fips": ["00001", "00002"]},
                             geometry=[Point(5 * KM, 5 * KM), Point(15 * KM, 5 * KM)], crs="EPSG:5070")
    feats = gpd.GeoDataFrame(geometry=[Point(5 * KM, 8 * KM), Point(30 * KM, 5 * KM)], crs="EPSG:5070")
    out = geo.nearest_distance_km(cents, feats, "d").set_index("fips")["d"]
    assert out["00001"] == pytest.approx(3.0)
    assert out["00002"] == pytest.approx(np.hypot(10, 3))


def test_nearest_distance_to_line(counties):
    cents = gpd.GeoDataFrame({"fips": ["00001"]}, geometry=[Point(5 * KM, 5 * KM)], crs="EPSG:5070")
    feats = gpd.GeoDataFrame(geometry=[LineString([(0, 9 * KM), (20 * KM, 9 * KM)])], crs="EPSG:5070")
    out = geo.nearest_distance_km(cents, feats, "d").set_index("fips")["d"]
    assert out["00001"] == pytest.approx(4.0)


def test_zfill_fips():
    assert zfill_fips(6037) == "06037"
    assert zfill_fips(6037.0) == "06037"
    assert zfill_fips(" 6037 ") == "06037"
    assert zfill_fips("06037") == "06037"
    assert zfill_fips(None) is None
    assert zfill_fips("abc") is None


def test_fips_fixes_renames_and_scope():
    df = pd.DataFrame({"code": [46113, 51515, 51019, 2020, 6037, 6000],
                       "n": [1, 2, 3, 4, 5, 6], "rate": [1.0, 2.0, 4.0, 9.0, 5.0, 7.0]})
    df = normalize_fips(df, "code")
    out = apply_fips_fixes(df, {"n": "sum", "rate": "mean"}, source="test").set_index("fips")
    assert "46102" in out.index and "46113" not in out.index
    assert out.loc["51019", "n"] == 5  # Bedford City merged into Bedford County
    assert out.loc["51019", "rate"] == pytest.approx(3.0)
    assert "02020" not in out.index  # Alaska dropped
    assert "06000" not in out.index  # state total dropped
