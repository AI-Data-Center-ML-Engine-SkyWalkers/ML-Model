"""County base layer (Census cartographic boundaries) and population-weighted centroids."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from .fips_fixes import CT_NEW_REGIONS, EXCLUDED_STATE_FIPS, STATE_FIPS_TO_ABBR
from .io import INTERIM, RAW, download, register_source, unzip

STORAGE_CRS = "EPSG:4269"
ALBERS = "EPSG:5070"

CB_URLS = {
    2025: "https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_500k.zip",
    2024: "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip",
}
CB_2020_URL = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_county_500k.zip"
CENPOP_CO_URL = "https://www2.census.gov/geo/docs/reference/cenpop2020/county/CenPop2020_Mean_CO.txt"
CENPOP_BG_CT_URL = "https://www2.census.gov/geo/docs/reference/cenpop2020/blkgrp/CenPop2020_Mean_BG09.txt"

BASE_PATH = INTERIM / "_base_counties.parquet"
CENTROID_PATH = INTERIM / "_pop_centroids.parquet"


def _read_cb(url: str) -> gpd.GeoDataFrame:
    zpath = download(url, f"census/{url.rsplit('/', 1)[-1]}")
    folder = unzip(zpath)
    shp = next(folder.glob("*.shp"))
    return gpd.read_file(shp)


def load_counties() -> gpd.GeoDataFrame:
    """CONUS + DC counties, EPSG:4269, columns fips, meta_*, ALAND, AWATER, geometry."""
    if BASE_PATH.exists():
        return gpd.read_parquet(BASE_PATH)
    vintage = None
    for year, url in CB_URLS.items():
        try:
            g = _read_cb(url)
            vintage = year
            break
        except Exception as e:  # pragma: no cover
            print(f"[counties] {year} boundaries unavailable: {e}")
    if vintage is None:
        raise RuntimeError("No county boundary file could be downloaded")
    g = g.rename(columns={"GEOID": "fips"})
    g = g[~g["STATEFP"].isin(EXCLUDED_STATE_FIPS)].copy()
    g["fips"] = g["fips"].astype(str).str.zfill(5)
    g["meta_county_name"] = g["NAMELSAD"]
    g["meta_state_fips"] = g["STATEFP"]
    g["meta_state_abbr"] = g["STATEFP"].map(STATE_FIPS_TO_ABBR)
    g["meta_land_area_km2"] = g["ALAND"].astype(float) / 1e6
    g = g.to_crs(STORAGE_CRS)
    g = g[["fips", "meta_county_name", "meta_state_abbr", "meta_state_fips", "meta_land_area_km2",
           "ALAND", "AWATER", "geometry"]].sort_values("fips").reset_index(drop=True)
    assert g["fips"].is_unique
    g.to_parquet(BASE_PATH)
    register_source(
        "census_cb_counties",
        raw_files=[RAW / f"census/{CB_URLS[vintage].rsplit('/', 1)[-1]}"],
        name=f"Census cartographic boundary counties 1:500k (cb_{vintage}_us_county_500k)",
        url=CB_URLS[vintage], vintage=str(vintage), license="Public domain (US Government work)",
        notes=f"{len(g)} CONUS+DC counties after dropping AK, HI and territories. CT uses planning regions.",
    )
    return g


def load_counties_2020() -> gpd.GeoDataFrame:
    """2020 cartographic counties (old CT counties), only used for the CT crosswalk."""
    g = _read_cb(CB_2020_URL).rename(columns={"GEOID": "fips"})
    register_source(
        "census_cb_counties_2020",
        raw_files=[RAW / "census/cb_2020_us_county_500k.zip"],
        name="Census cartographic boundary counties 2020 1:500k", url=CB_2020_URL, vintage="2020",
        license="Public domain (US Government work)",
        notes="Used only to build the Connecticut old-county -> planning-region area crosswalk.",
    )
    return g[["fips", "geometry"]]


def counties_albers() -> gpd.GeoDataFrame:
    return load_counties().to_crs(ALBERS)


def _mean_center(lat: np.ndarray, lon: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    """Census mean center of population formula (cos-latitude weighting of longitude)."""
    phi = np.radians(lat)
    c_lat = np.sum(w * lat) / np.sum(w)
    c_lon = np.sum(w * lon * np.cos(phi)) / np.sum(w * np.cos(phi))
    return float(c_lat), float(c_lon)


def load_pop_centroids() -> gpd.GeoDataFrame:
    """Population-weighted centroids (2020 census) for every base county, EPSG:4269.

    Columns: fips, meta_pop_centroid_lat, meta_pop_centroid_lon, centroid_source, geometry.
    CT planning regions are computed from 2020 block-group centers of population that fall
    inside each region. Counties with no published centroid fall back to NaN.
    """
    if CENTROID_PATH.exists():
        return gpd.read_parquet(CENTROID_PATH)
    base = load_counties()
    p = download(CENPOP_CO_URL, "census/CenPop2020_Mean_CO.txt")
    co = pd.read_csv(p, dtype={"STATEFP": str, "COUNTYFP": str}, encoding="utf-8-sig")
    co["fips"] = co["STATEFP"].str.zfill(2) + co["COUNTYFP"].str.zfill(3)
    co = co.rename(columns={"LATITUDE": "lat", "LONGITUDE": "lon"})[["fips", "lat", "lon"]]
    co["centroid_source"] = "census_cenpop2020_county"

    bgp = download(CENPOP_BG_CT_URL, "census/CenPop2020_Mean_BG09.txt")
    bg = pd.read_csv(bgp, dtype=str, encoding="utf-8-sig")
    for c in ("POPULATION", "LATITUDE", "LONGITUDE"):
        bg[c] = bg[c].astype(float)
    bg = gpd.GeoDataFrame(bg, geometry=gpd.points_from_xy(bg["LONGITUDE"], bg["LATITUDE"]), crs="EPSG:4269")
    ct = base[base["fips"].isin(CT_NEW_REGIONS)][["fips", "geometry"]]
    j = gpd.sjoin(bg, ct, how="inner", predicate="within")
    rows = []
    for f, g in j.groupby("fips"):
        lat, lon = _mean_center(g["LATITUDE"].values, g["LONGITUDE"].values, g["POPULATION"].values)
        rows.append({"fips": f, "lat": lat, "lon": lon, "centroid_source": "derived_from_cenpop2020_blockgroups"})
    ctc = pd.DataFrame(rows)

    cen = pd.concat([co[~co["fips"].str.startswith("09")], ctc], ignore_index=True)
    cen = base[["fips"]].merge(cen, on="fips", how="left")
    missing = cen[cen["lat"].isna()]["fips"].tolist()
    if missing:
        print(f"[centroids] no published population centroid for {missing}")
    cen = cen.rename(columns={"lat": "meta_pop_centroid_lat", "lon": "meta_pop_centroid_lon"})
    g = gpd.GeoDataFrame(
        cen, geometry=gpd.points_from_xy(cen["meta_pop_centroid_lon"], cen["meta_pop_centroid_lat"]),
        crs="EPSG:4269",
    )
    g.to_parquet(CENTROID_PATH)
    register_source(
        "census_pop_centroids",
        raw_files=[p, bgp],
        name="Census 2020 centers of population (county; CT block groups)",
        url=CENPOP_CO_URL, vintage="2020 Census", license="Public domain (US Government work)",
        notes=("CT planning regions have no published centroid; computed with the Census mean-center "
               "formula from 2020 block-group centers of population (" + CENPOP_BG_CT_URL + ")."
               + (f" Missing: {missing}" if missing else "")),
    )
    return g


def centroids_albers() -> gpd.GeoDataFrame:
    g = load_pop_centroids()
    return g[g.geometry.notna() & ~g.geometry.is_empty].to_crs(ALBERS)
