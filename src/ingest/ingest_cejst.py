"""CEJST v2.0 (taken down Jan 2025; official file via the Internet Archive): share of county population in
disadvantaged census tracts."""
import pandas as pd

from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

ORIG = ("https://static-data-screeningtool.geoplatform.gov/data-versions/2.0/data/score/downloadable/"
        "2.0-communities.csv")
URL = f"https://web.archive.org/web/20250122234715id_/{ORIG}"
MIRROR_PAGE = "https://screening-tools.com/climate-economic-justice-screening-tool"
FEATURE = "cob_ej_disadvantaged"


def main():
    p = download(URL, "cejst/2.0-communities.csv", timeout=900)
    d = pd.read_csv(p, usecols=["Census tract 2010 ID", "Identified as disadvantaged", "Total population"],
                    dtype={"Census tract 2010 ID": str})
    d["fips"] = d["Census tract 2010 ID"].str.zfill(11).str[:5]
    pop = pd.to_numeric(d["Total population"], errors="coerce")
    flag = d["Identified as disadvantaged"].astype(str).str.strip().str.lower().eq("true")
    d["pop"], d["dis_pop"] = pop, pop.where(flag, 0.0)
    g = table_join(d[["fips", "pop", "dis_pop"]], "fips", {"pop": "sum", "dis_pop": "sum"}, source="cejst")
    g[FEATURE] = 100.0 * g["dis_pop"] / g["pop"].where(g["pop"] > 0)
    out = g[["fips", FEATURE]]
    write_interim(out, "cejst")
    register_source(
        "cejst_v2", raw_files=[p], name="Climate and Economic Justice Screening Tool v2.0, communities list (tracts)",
        url=URL, landing_page=f"{MIRROR_PAGE} ; {ORIG}",
        mirror="Internet Archive capture 2025-01-22 of the official geoplatform.gov file (host no longer resolves); "
               "the screening-tools.com (PEDP) mirror hosts the map but no direct data file",
        vintage="CEJST 2.0 (Dec 2024), 2010 census tracts, ACS 2015-2019 population", license="Public domain (CEQ)",
        notes=("Percent of county 'Total population' living in tracts with 'Identified as disadvantaged' = True "
               "(includes tribal-overlap and grandfathered tracts, as CEJST's final flag does). Tracts with missing "
               "population are ignored, so 46102 Oglala Lakota (every tract flagged, no population published) is "
               "NaN. 2010 geography: CT old counties area-split to planning regions; 46113 and "
               "51515 renamed."),
    )
    set_status("cejst_v2", "OK", f"{out[FEATURE].notna().sum()} counties; "
               f"{int((out[FEATURE] > 50).sum())} with > 50% of population disadvantaged.", [FEATURE])


if __name__ == "__main__":
    main()
