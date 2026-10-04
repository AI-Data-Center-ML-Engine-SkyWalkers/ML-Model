"""PeeringDB: IXP-hosting facilities per county and distance to the nearest one."""
import json

import geopandas as gpd
import pandas as pd

from src.common.counties import centroids_albers, load_counties
from src.common.geo import nearest_distance_km, points_to_county
from src.common.io import download, register_source, set_status, write_interim

API = "https://www.peeringdb.com/api/{obj}"


def _get(obj, params, dest):
    p = download(API.format(obj=obj), f"peeringdb/{dest}", params=params, allow_html=False, timeout=300)
    return pd.DataFrame(json.loads(p.read_text())["data"]), p


def main():
    fac, p1 = _get("fac", {"country": "US"}, "fac_US.json")
    ixfac, p2 = _get("ixfac", {}, "ixfac_all.json")
    ix, p3 = _get("ix", {"country": "US"}, "ix_US.json")
    fac = fac[fac["status"] == "ok"].copy()
    for c in ("latitude", "longitude"):
        fac[c] = pd.to_numeric(fac[c], errors="coerce")
    no_xy = fac["latitude"].isna() | fac["longitude"].isna()
    ix_fac_ids = set(ixfac.loc[ixfac["status"] == "ok", "fac_id"])
    fac["hosts_ix"] = fac["id"].isin(ix_fac_ids)
    pts = gpd.GeoDataFrame(fac[~no_xy], geometry=gpd.points_from_xy(fac.loc[~no_xy, "longitude"],
                                                                      fac.loc[~no_xy, "latitude"]), crs="EPSG:4326")
    ixp = pts[pts["hosts_ix"]]
    cty = load_counties()
    out = points_to_county(ixp, cty, "lnd_ixp_n")
    out = out.merge(points_to_county(pts, cty, "lnd_colo_fac_n"), on="fips")
    out = out.merge(nearest_distance_km(centroids_albers(), ixp, "lnd_dist_ixp_km", all_fips=cty[["fips"]]), on="fips")
    write_interim(out, "peeringdb")
    register_source(
        "peeringdb", raw_files=[p1, p2, p3], name="PeeringDB public API: fac, ixfac, ix",
        url=API.format(obj="{fac|ixfac|ix}"), landing_page="https://www.peeringdb.com/apidocs/",
        vintage=f"API snapshot {pd.Timestamp.today().date()} (cached)", license="PeeringDB AUP; public data, attribution",
        notes=(f"US facilities with status ok and coordinates ({len(pts)}; {int(no_xy.sum())} without coordinates dropped). "
               f"lnd_ixp_n = facilities linked to at least one exchange via ixfac ({len(ixp)} US facilities); "
               "lnd_colo_fac_n = all PeeringDB facilities. Distance from the population centroid to the nearest "
               "IX-hosting facility."),
    )
    set_status("peeringdb", "OK", f"{len(ixp)} IX-hosting US facilities, {len(pts)} facilities total.",
               ["lnd_ixp_n", "lnd_colo_fac_n", "lnd_dist_ixp_km"])


if __name__ == "__main__":
    main()
