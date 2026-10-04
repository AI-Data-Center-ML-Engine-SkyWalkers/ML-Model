"""EPA eGRID2023 (rev2): subregion CO2 output emission rate, area-weighted onto counties."""
import geopandas as gpd
import pandas as pd

from src.common.counties import load_counties
from src.common.geo import polygon_area_weighted_mean
from src.common.io import INTERIM, download, register_source, set_status, unzip, write_interim

DATA_URL = "https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx"
SHP_URL = "https://www.epa.gov/system/files/other-files/2025-01/egrid2023_subregions.zip"
LB_TO_KG = 0.45359237


def load_subregions() -> gpd.GeoDataFrame:
    z = download(SHP_URL, "egrid/egrid2023_subregions.zip")
    g = gpd.read_file(next(unzip(z).glob("*.shp")))
    col = next(c for c in g.columns if c.lower() in ("subrgn", "zipsubregi", "subregion"))
    return g.rename(columns={col: "SUBRGN"})[["SUBRGN", "geometry"]], z


def load_egrid_sheet(sheet: str) -> pd.DataFrame:
    p = download(DATA_URL, "egrid/egrid2023_data_rev2.xlsx", timeout=900)
    return pd.read_excel(p, sheet_name=sheet, header=1), p


def main():
    srl, p = load_egrid_sheet("SRL23")
    shp, z = load_subregions()
    srl["crb_grid_co2_kg_mwh"] = srl["SRCO2RTA"] * LB_TO_KG
    poly = shp.merge(srl[["SUBRGN", "crb_grid_co2_kg_mwh"]], on="SUBRGN", how="left")
    missing = poly[poly["crb_grid_co2_kg_mwh"].isna()]["SUBRGN"].tolist()
    poly.to_parquet(INTERIM / "_egrid_subregions.parquet")
    out = polygon_area_weighted_mean(poly, ["crb_grid_co2_kg_mwh"], load_counties())
    write_interim(out, "epa_egrid")
    register_source(
        "epa_egrid2023", raw_files=[p, z], name="EPA eGRID2023 rev2 data + eGRID2023 subregion shapefile",
        url=DATA_URL, shapefile_url=SHP_URL, landing_page="https://www.epa.gov/egrid/detailed-data",
        vintage="eGRID2023 (data year 2023), revision 2 released June 2025", license="Public domain (US EPA)",
        notes=("SRCO2RTA (subregion annual CO2 total output emission rate, lb/MWh) x 0.4536 -> kg/MWh. Area-weighted "
               "overlay of subregion polygons onto counties in EPSG:5070. Subregions are large, so many counties "
               f"share a value. Polygons without a rate: {missing}"),
    )
    set_status("epa_egrid2023", "OK", f"{out['crb_grid_co2_kg_mwh'].notna().sum()} counties.", ["crb_grid_co2_kg_mwh"])


if __name__ == "__main__":
    main()
