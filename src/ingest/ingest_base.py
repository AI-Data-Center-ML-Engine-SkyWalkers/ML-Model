"""Base layer: county list, names, land area, population centroids, CT crosswalk."""
from src.common.counties import load_counties, load_pop_centroids
from src.common.fips_fixes import ct_crosswalk
from src.common.io import set_status, write_interim


def main():
    base = load_counties()
    cen = load_pop_centroids()
    xw = ct_crosswalk()
    print(xw.round(3).to_string())
    df = base.drop(columns=["geometry", "ALAND", "AWATER"]).merge(
        cen[["fips", "meta_pop_centroid_lat", "meta_pop_centroid_lon"]], on="fips", how="left")
    write_interim(df, "meta_base")
    n_missing = int(df["meta_pop_centroid_lat"].isna().sum())
    set_status("census_cb_counties", "OK", f"{len(df)} counties (CONUS+DC).",
               ["fips", "meta_county_name", "meta_state_abbr", "meta_state_fips", "meta_land_area_km2"])
    set_status("census_pop_centroids", "OK" if n_missing == 0 else "PARTIAL",
               f"2020 centers of population; CT derived from block groups; {n_missing} missing.",
               ["meta_pop_centroid_lat", "meta_pop_centroid_lon"])


if __name__ == "__main__":
    main()
