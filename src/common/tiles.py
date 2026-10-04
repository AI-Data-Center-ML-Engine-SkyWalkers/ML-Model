"""30 m EPSG:5070 tile grid aligned with Annual NLCD 2024, for rasters rendered by ArcGIS image/map services."""
from __future__ import annotations

import numpy as np
import rasterio
import shapely
from rasterio.windows import Window

from .counties import load_counties
from .io import RAW

NLCD = RAW / "nlcd" / "Annual_NLCD_LndCov_2024_CU_C1V1" / "Annual_NLCD_LndCov_2024_CU_C1V1.tif"
NLCD_WATER, NLCD_NODATA = 11, 250
RES = 30.0


class Grid:
    def __init__(self, tile_px: int):
        with rasterio.open(NLCD) as s:
            self.x0, self.y0, self.width, self.height = s.transform.c, s.transform.f, s.width, s.height
        self.tile = tile_px
        self.span = tile_px * RES

    def bbox(self, i: int, j: int) -> tuple[float, float, float, float]:
        return (self.x0 + i * self.span, self.y0 - (j + 1) * self.span,
                self.x0 + (i + 1) * self.span, self.y0 - j * self.span)

    def tiles(self) -> list[tuple[int, int]]:
        """Tiles that intersect a CONUS + DC county."""
        land = shapely.union_all(load_counties().to_crs(5070).geometry.simplify(500).values)
        return [(i, j) for j in range(int(np.ceil(self.height / self.tile)))
                for i in range(int(np.ceil(self.width / self.tile)))
                if land.intersects(shapely.box(*self.bbox(i, j)))]

    def nlcd_land_mask(self, nlcd: rasterio.DatasetReader, i: int, j: int) -> np.ndarray:
        """True where NLCD is a land class (not open water, not nodata)."""
        lc = nlcd.read(1, window=Window(i * self.tile, j * self.tile, self.tile, self.tile), boundless=True,
                       fill_value=NLCD_NODATA)
        return (lc != NLCD_WATER) & (lc != NLCD_NODATA)
