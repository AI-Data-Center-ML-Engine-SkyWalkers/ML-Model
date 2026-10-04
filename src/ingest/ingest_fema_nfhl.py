"""FEMA NFHL: percent of each county's mapped land in the 1%-annual-chance floodplain (SFHA, zones A* and V*).

The NFHL has ~1.4 M SFHA polygons (tens of GB as state geodatabases), so the NFHL MapServer renders them
server-side: 4000 px PNG tiles on the 30 m EPSG:5070 grid aligned with Annual NLCD, solid fill, no outline,
anti-aliased. Alpha / 255 is the covered fraction of each pixel (checked against an exact vector overlay on a
12 km test window: 29.13% vs 29.14%). dpi=30 puts the 30 m request at ~1:35,400, inside the layer's 1:36,112
visibility limit. Denominator = NLCD land (not open water) inside the NFHL Availability footprint.
"""
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import geopandas as gpd
import numpy as np
import rasterio
import requests
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import from_origin
from tqdm import tqdm

from src.common.counties import load_counties
from src.common.geo import polygon_coverage_pct, raster_mean
from src.common.io import INTERIM, RAW, register_source, set_status, write_interim
from src.common.tiles import NLCD, RES, Grid

SERVICE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
SFHA_LAYER, AVAIL_LAYER = 28, 0
TILE = 4000  # service max 4096
DPI = 30
WORKERS = 4
MIN_COVERAGE_PCT = 50.0  # below this share of the county inside NFHL Availability, the floodplain share is NaN
OUT = RAW / "fema_nfhl"
TILES = OUT / "sfha_tiles"
DERIVED = INTERIM / "_sfha_tiles"
FEATURES = ["haz_pct_floodplain_100yr", "haz_nfhl_coverage_pct"]
DYNAMIC = [{"id": SFHA_LAYER, "source": {"type": "mapLayer", "mapLayerId": SFHA_LAYER},
            "definitionExpression": "SFHA_TF = 'T'",
            "drawingInfo": {"transparency": 0, "renderer": {"type": "simple", "symbol": {
                "type": "esriSFS", "style": "esriSFSSolid", "color": [255, 0, 0, 255],
                "outline": {"type": "esriSLS", "style": "esriSLSNull", "color": [0, 0, 0, 0], "width": 0}}}}}]


def availability() -> gpd.GeoDataFrame:
    dest = OUT / "nfhl_availability_5070.geojson"
    if not dest.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        url = f"{SERVICE}/{AVAIL_LAYER}/query"
        print(f"[download] {url}")
        feats, off = [], 0
        while True:
            for attempt in range(5):
                j = requests.get(url, params={"where": "1=1", "outFields": "STUDY_ID", "outSR": 5070,
                                              "f": "geojson", "maxAllowableOffset": 10, "resultOffset": off,
                                              "resultRecordCount": 200}, timeout=600).json()
                if "features" in j:
                    break
                print(f"[nfhl] availability offset {off}: {str(j)[:200]}; retrying")
                time.sleep(10 * (attempt + 1))
            else:
                raise RuntimeError(f"NFHL Availability query failed at offset {off}")
            feats += j["features"]
            if len(j["features"]) < 200:
                break
            off += len(j["features"])
        dest.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    return gpd.read_file(dest).set_crs(5070, allow_override=True)


def fetch(grid: Grid, i: int, j: int) -> None:
    dest = TILES / f"sfha_{i:02d}_{j:02d}.png"
    if dest.exists():
        return
    params = {"bbox": ",".join(map(str, grid.bbox(i, j))), "bboxSR": 5070, "imageSR": 5070,
              "size": f"{TILE},{TILE}", "dpi": DPI, "format": "png32", "transparent": "true",
              "dynamicLayers": json.dumps(DYNAMIC), "f": "image"}
    err = ""
    for _ in range(4):
        try:
            r = requests.get(f"{SERVICE}/export", params=params, timeout=900)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                tmp = dest.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.rename(dest)
                return
            err = f"HTTP {r.status_code} {r.text[:200]}"
        except requests.RequestException as e:
            err = str(e)
    raise RuntimeError(f"tile {i},{j}: {err}")


def derive_tile(grid: Grid, i: int, j: int, nlcd, avail: gpd.GeoDataFrame) -> None:
    """uint8: 0-200 = SFHA fraction x 200 on mapped land; 255 = water, NLCD nodata, or outside NFHL coverage."""
    dest = DERIVED / f"f_{i:02d}_{j:02d}.tif"
    if dest.exists():
        return
    alpha = np.asarray(Image.open(TILES / f"sfha_{i:02d}_{j:02d}.png").convert("RGBA"))[..., 3].astype(float)
    xmin, _, _, ymax = grid.bbox(i, j)
    transform = from_origin(xmin, ymax, RES, RES)
    box = avail.cx[xmin:xmin + grid.span, ymax - grid.span:ymax]
    covered = rasterize(((g, 1) for g in box.geometry), out_shape=(TILE, TILE), transform=transform, fill=0,
                        dtype="uint8").astype(bool) if len(box) else np.zeros((TILE, TILE), bool)
    val = np.rint(200 * alpha / 255).astype("uint8")
    val[~(covered & grid.nlcd_land_mask(nlcd, i, j))] = 255
    profile = {"driver": "GTiff", "width": TILE, "height": TILE, "count": 1, "dtype": "uint8", "crs": "EPSG:5070",
               "transform": transform, "nodata": 255, "compress": "deflate", "tiled": True,
               "blockxsize": 512, "blockysize": 512}
    with rasterio.open(dest, "w", **profile) as d:
        d.write(val, 1)


def main():
    TILES.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)
    grid = Grid(TILE)
    avail = availability()
    print(f"[nfhl] {SERVICE}/export layer {SFHA_LAYER}, {len(avail)} NFHL Availability polygons")
    tiles = grid.tiles()
    failed = []
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(fetch, grid, i, j): (i, j) for i, j in tiles}
        for f in tqdm(as_completed(futs), total=len(futs), desc="nfhl tiles"):
            try:
                f.result()
            except RuntimeError as e:
                print(f"[nfhl] {e}")
                failed.append(futs[f])
    if failed:
        set_status("fema_nfhl", "FAILED", f"{len(failed)}/{len(tiles)} tiles failed; re-run to resume.", FEATURES)
        return
    with rasterio.open(NLCD) as nlcd:
        for i, j in tqdm(tiles, desc="derive"):
            derive_tile(grid, i, j, nlcd, avail)
    vrt = DERIVED / "sfha.vrt"
    subprocess.run(["gdalbuildvrt", "-q", "-overwrite", str(vrt), *sorted(map(str, DERIVED.glob("f_*.tif")))],
                   check=True)
    counties = load_counties()
    share = raster_mean(vrt, counties, "haz_pct_floodplain_100yr")
    cov = polygon_coverage_pct(avail, counties, "haz_nfhl_coverage_pct")
    out = share.merge(cov, on="fips")
    out["haz_pct_floodplain_100yr"] = (out["haz_pct_floodplain_100yr"] / 2.0).where(
        out["haz_nfhl_coverage_pct"] >= MIN_COVERAGE_PCT)
    write_interim(out, "fema_nfhl")
    register_source(
        "fema_nfhl", raw_files=[OUT / "nfhl_availability_5070.geojson", *sorted(TILES.glob("*.png"))[:19]],
        name="FEMA National Flood Hazard Layer (NFHL MapServer: Flood Hazard Zones + NFHL Availability)",
        url=f"{SERVICE}/export ; {SERVICE}/{AVAIL_LAYER}/query", landing_page="https://www.fema.gov/flood-maps/national-flood-hazard-layer",
        vintage="NFHL as served on the download date (continuously updated)", license="Public domain (FEMA)",
        notes=("SFHA = S_FLD_HAZ_AR with SFHA_TF = 'T' (zones A, AE, AH, AO, AR, A99, V, VE). Rendered server-side "
               f"at 30 m (EPSG:5070, NLCD-aligned, dpi={DPI}); anti-aliased alpha used as partial pixel coverage. "
               "haz_pct_floodplain_100yr = SFHA share of NLCD land (open water excluded) inside the NFHL Availability "
               f"footprint, NaN where haz_nfhl_coverage_pct < {MIN_COVERAGE_PCT:.0f}. Areas with only paper or "
               "unmodernized maps are outside the footprint. Instead of the state-by-state geodatabases in the spec "
               "(tens of GB) the official map service rendering was used; same polygons."),
    )
    n = int(out["haz_pct_floodplain_100yr"].notna().sum())
    set_status("fema_nfhl", "OK" if n == len(out) else "PARTIAL",
               f"{len(tiles)} tiles; {n} counties with a value; {len(out) - n} NaN (NFHL coverage < "
               f"{MIN_COVERAGE_PCT:.0f}% of county area).", FEATURES)


if __name__ == "__main__":
    main()
