"""FEMA NRI Future Risk Index (removed by FEMA Feb 2025; fulton-ring/nri-future-risk GitHub mirror).

Projected Risk Index Score per hazard, mid-century, lower mean global temperature scenario.
"""
import pandas as pd

from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

REPO = "https://github.com/fulton-ring/nri-future-risk"
URL = "https://raw.githubusercontent.com/fulton-ring/nri-future-risk/main/public/NRI_Future_Risk_Master_Datasheet_12052024.xlsx"
DICT_URL = "https://raw.githubusercontent.com/fulton-ring/nri-future-risk/main/public/NRI_Data_Dictionary.xlsx"
SCENARIO = "MID_LOWER"  # mid-century, lower warming (closest to the SSP2-4.5 choice used for CMRA)
HAZARDS = {  # NRI code (field prefix) -> output column
    "CFLD": ("CFLD", "haz_eal_coastal_flood_future"),
    "DRGT": ("DRGT", "haz_eal_drought_future"),
    "EXHT": ("EXHT_L95", "haz_eal_heatwave_future"),  # LOCA 95th-percentile variant (CMRA also uses LOCA2)
    "HRCN": ("HRCN", "haz_eal_hurricane_future"),
    "WFIR": ("WFIR", "haz_eal_wildfire_future"),
}


def main():
    p = download(URL, "nri_future/NRI_Future_Risk_Master_Datasheet_12052024.xlsx")
    p_dict = download(DICT_URL, "nri_future/NRI_Data_Dictionary.xlsx")
    d = pd.read_excel(p, dtype={"STCOFIPS": str})
    n_na = {}
    for code, (prefix, col) in HAZARDS.items():
        s = pd.to_numeric(d[f"{prefix}_{SCENARIO}_PRISKS"], errors="coerce")
        na = s.isna() & d[f"{code}_RISKR"].eq("Not Applicable")
        n_na[col] = int(na.sum())
        d[col] = s.mask(na, 0.0)
    cols = [c for _, c in HAZARDS.values()]
    out = table_join(d[["STCOFIPS", *cols]], "STCOFIPS", {c: "mean" for c in cols}, source="nri_future")
    write_interim(out, "nri_future")
    register_source(
        "fema_nri_future_risk", raw_files=[p, p_dict],
        name="FEMA National Risk Index - Future Risk (Climate Informed Risk Index) master datasheet",
        url=URL, landing_page=REPO, mirror="fulton-ring/nri-future-risk (copy made before FEMA removed the tool)",
        vintage="Master Datasheet 2024-12-05, data dictionary version 1.0.0 (2024-12-02)",
        license="Public domain (US Government work); mirror repo MIT",
        notes=(f"{SCENARIO}_PRISKS = Projected Risk Index Score, mid-century, lower mean global temperature scenario "
               "(chosen to match the SSP2-4.5 CMRA choice). Only 5 hazards have projections: coastal flood, drought, "
               "extreme heat (LOCA 95th-percentile variant used; NEX/99th also published), hurricane, wildfire. "
               "Columns keep the spec's haz_eal_*_future names but hold projected RISK scores (0-100), not EAL "
               "scores: the Future Risk release has no projected EAL score. Where the current hazard risk rating is "
               f"'Not Applicable' the score is set to 0 (counts {n_na}); 'Insufficient Data' stays NaN. CT on old "
               "counties, area-weighted to planning regions."),
    )
    set_status("fema_nri_future_risk", "OK", f"{len(out)} counties; non-null {out[cols].notna().sum().to_dict()}",
               cols)


if __name__ == "__main__":
    main()
