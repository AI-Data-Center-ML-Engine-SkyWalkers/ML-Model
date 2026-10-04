"""EPA ACRES brownfield sites (FRS KMZ): count per county, distance to nearest, and nearest brownfield-or-retired-plant."""
import re
import zipfile

import geopandas as gpd
import pandas as pd

from src.common.counties import centroids_albers, load_counties
from src.common.geo import nearest_distance_km, points_to_county
from src.common.io import INTERIM, RAW, download, register_source, set_status, write_interim

URL = "https://ordsext.epa.gov/FLA/www3/acres_frs.kmz"
PLACEMARK = re.compile(r"<Placemark>(.*?)</Placemark>", re.S)
REGID = re.compile(r"REGISTRY ID</td><td>.*?>(\d+)<")
COORD = re.compile(r"<coordinates>\s*([-\d.]+),([-\d.]+)")
STAMP = re.compile(r"produced by the US Environmental Protection Agency \(EPA\) on ([A-Z]{3}-\d{2}-\d{4})")


def parse(kmz) -> tuple[pd.DataFrame, str]:
    with zipfile.ZipFile(kmz) as z:
        txt = z.read(next(n for n in z.namelist() if n.lower().endswith(".kml"))).decode("utf-8", "replace")
    rows = []
    for pm in PLACEMARK.findall(txt):
        c, r = COORD.search(pm), REGID.search(pm)
        if c:
            rows.append({"registry_id": r.group(1) if r else None, "lon": float(c.group(1)), "lat": float(c.group(2))})
    stamp = STAMP.search(txt[:5000])
    return pd.DataFrame(rows), stamp.group(1) if stamp else "unknown"


def main():
    p = download(URL, "epa_brownfields/acres_frs.kmz", allow_html=False)
    df, stamp = parse(p)
    n_raw = len(df)
    df = df.drop_duplicates(subset=["registry_id"]) if df["registry_id"].notna().all() else df.drop_duplicates()
    df = df[(df["lat"] != 0) & (df["lon"] != 0)]
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs="EPSG:4326")
    cty = load_counties()
    cen = centroids_albers()
    out = points_to_county(pts, cty, "lnd_brownfields_n")
    out = out.merge(nearest_distance_km(cen, pts, "lnd_dist_brownfield_km", all_fips=cty[["fips"]]), on="fips")
    retired_path = INTERIM / "_retired_plants_100mw.parquet"
    if retired_path.exists():
        ret = gpd.read_parquet(retired_path)[["geometry"]].to_crs(4326)
        both = pd.concat([pts[["geometry"]], ret], ignore_index=True)
        out = out.merge(nearest_distance_km(cen, gpd.GeoDataFrame(both, crs=4326), "lnd_dist_brownfield_or_retired_km",
                                            all_fips=cty[["fips"]]), on="fips")
        combo_note = "lnd_dist_brownfield_or_retired_km = nearest of brownfields and EIA-860M retired plants >= 100 MW."
    else:
        out["lnd_dist_brownfield_or_retired_km"] = float("nan")
        combo_note = "Retired-plant file missing (run ingest_eia860m first); combined distance left NaN."
    write_interim(out, "epa_brownfields")
    register_source(
        "epa_acres_brownfields", raw_files=[p], name="EPA ACRES Brownfields Project Locations (FRS geospatial KMZ)",
        url=URL, landing_page="https://www.epa.gov/frs/geospatial-data-download-service ; https://www.epa.gov/cleanups/cleanups-my-community",
        vintage=f"KML produced by EPA on {stamp}", license="Public domain (US Government work)",
        notes=(f"{n_raw} placemarks parsed; {len(pts)} unique FRS registry IDs with non-zero coordinates. Locations are "
               "FRS best-available coordinates (many address-matched). " + combo_note),
    )
    set_status("epa_acres_brownfields", "OK", f"{len(pts)} brownfield sites located.",
               ["lnd_brownfields_n", "lnd_dist_brownfield_km", "lnd_dist_brownfield_or_retired_km"])


if __name__ == "__main__":
    main()
