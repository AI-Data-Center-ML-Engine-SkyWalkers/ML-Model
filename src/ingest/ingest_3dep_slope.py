"""USGS 3DEP: percent of each county's land with slope < 5%, from 30 m elevation.

The 3DEP ImageServer resamples the seamless DEM to a 30 m EPSG:5070 grid aligned with Annual NLCD, computes
percent-rise slope server-side (ArcGIS Slope = Horn 3x3) and returns a 0/1 tile (1 = slope < 5%), so CONUS is
~1 GB instead of ~40 GB of float DEM. Tiles are cached in data/raw/3dep_slope/ (resumable). NLCD open water (11)
and NLCD nodata are masked before the zonal mean.
"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import rasterio
import requests
from tqdm import tqdm

from src.common.counties import load_counties
from src.common.geo import raster_mean
from src.common.io import INTERIM, RAW, register_source, set_status, write_interim
from src.common.tiles import NLCD, RES, Grid

SERVICE = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"
SLOPE_PCT_MAX = 5.0
TILE = 4000  # pixels; service max is 8000
WORKERS = 4
OUT = RAW / "3dep_slope"
MASKED = INTERIM / "_slope_lt5_tiles"
FEATURE = "lnd_pct_slope_lt5"
RULE = {"rasterFunction": "Remap", "rasterFunctionArguments": {
    "InputRanges": [0, SLOPE_PCT_MAX, SLOPE_PCT_MAX, 1e6], "OutputValues": [1, 0],
    "Raster": {"rasterFunction": "Slope", "rasterFunctionArguments": {"SlopeType": 2, "ZFactor": 1}}}}


def fetch(grid: Grid, i: int, j: int) -> str:
    dest = OUT / f"slope_lt5_{i:02d}_{j:02d}.tif"
    if dest.exists():
        return "cached"
    params = {"bbox": ",".join(map(str, grid.bbox(i, j))), "bboxSR": 5070, "imageSR": 5070,
              "size": f"{TILE},{TILE}", "format": "tiff", "pixelType": "U8", "noData": 255, "compression": "LZ77",
              "renderingRule": json.dumps(RULE), "f": "image"}
    for _ in range(4):
        try:
            r = requests.get(f"{SERVICE}/exportImage", params=params, timeout=600)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                tmp = dest.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.rename(dest)
                return "ok"
            err = f"HTTP {r.status_code} {r.text[:200]}"
        except requests.RequestException as e:
            err = str(e)
    raise RuntimeError(f"tile {i},{j}: {err}")


def mask_tile(grid: Grid, i: int, j: int, nlcd: rasterio.DatasetReader) -> None:
    dest = MASKED / f"m_{i:02d}_{j:02d}.tif"
    if dest.exists():
        return
    with rasterio.open(OUT / f"slope_lt5_{i:02d}_{j:02d}.tif") as s:
        a, profile = s.read(1), s.profile
    a = np.where(grid.nlcd_land_mask(nlcd, i, j), a, 255).astype("uint8")
    profile.update(compress="deflate", nodata=255, tiled=True, blockxsize=512, blockysize=512)
    with rasterio.open(dest, "w", **profile) as d:
        d.write(a, 1)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    MASKED.mkdir(parents=True, exist_ok=True)
    grid = Grid(TILE)
    print(f"[3dep] {SERVICE}/exportImage, grid origin {grid.x0},{grid.y0} (NLCD), {TILE}px tiles at {RES} m")
    tiles = grid.tiles()
    failed = []
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(fetch, grid, i, j): (i, j) for i, j in tiles}
        for f in tqdm(as_completed(futs), total=len(futs), desc="3dep tiles"):
            try:
                f.result()
            except RuntimeError as e:
                print(f"[3dep] {e}")
                failed.append(futs[f])
    if failed:
        set_status("usgs_3dep_slope", "FAILED", f"{len(failed)}/{len(tiles)} tiles failed; re-run to resume.",
                   [FEATURE])
        return
    with rasterio.open(NLCD) as nlcd:
        for i, j in tqdm(tiles, desc="mask water"):
            mask_tile(grid, i, j, nlcd)
    vrt = MASKED / "slope_lt5.vrt"
    subprocess.run(["gdalbuildvrt", "-q", "-overwrite", str(vrt), *sorted(map(str, MASKED.glob("m_*.tif")))],
                   check=True)
    out = raster_mean(vrt, load_counties(), FEATURE)
    out[FEATURE] = 100.0 * out[FEATURE]
    write_interim(out, "usgs_3dep_slope")
    register_source(
        "usgs_3dep_slope", raw_files=sorted(OUT.glob("*.tif"))[:20],
        name="USGS 3D Elevation Program seamless DEM (3DEPElevation ImageServer), slope derived server-side",
        url=f"{SERVICE}/exportImage", landing_page="https://www.usgs.gov/3d-elevation-program",
        vintage="3DEP seamless DEM as served on the download date (best available source per location, resampled "
                "to 30 m)", license="Public domain (USGS)",
        notes=(f"Rendering rule: Slope (SlopeType 2 = percent rise, ZFactor 1; ArcGIS Horn 3x3) on the DEM resampled "
               f"to a 30 m EPSG:5070 grid aligned with Annual NLCD, then Remap [0, {SLOPE_PCT_MAX}) -> 1, else 0. "
               "Verified on a 30 km test window: identical to a local Horn slope from the service's 30 m DEM. "
               "(The 'Slope Degrees' template + Remap rounds thresholds and was not used.) NLCD 2024 open water (11) "
               "and NLCD nodata masked, so the value is the percent of non-water land area (exactextract "
               "coverage-weighted mean of the 0/1 raster x 100). Tile edges use only in-tile pixels."),
    )
    set_status("usgs_3dep_slope", "OK", f"{len(tiles)} tiles; {out[FEATURE].notna().sum()} counties.", [FEATURE])


if __name__ == "__main__":
    main()
