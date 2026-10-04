"""FEMA National Risk Index county table (Harvard Dataverse mirror; FEMA site taken down 2025)."""
import pandas as pd

from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

DATAVERSE_DOI = "doi:10.7910/DVN/JSQ8KZ"
URL = "https://dataverse.harvard.edu/api/access/datafile/10775771?format=original"
FEMA_URL = "https://hazards.fema.gov/nri/data-resources"

COLS = {
    "RISK_SCORE": "haz_nri_risk_score",
    "RFLD_EALS": "haz_eal_riverine_flood",
    "CFLD_EALS": "haz_eal_coastal_flood",
    "HRCN_EALS": "haz_eal_hurricane",
    "WFIR_EALS": "haz_eal_wildfire",
    "TRND_EALS": "haz_eal_tornado",
    "ERQK_EALS": "haz_eal_earthquake",
    "HWAV_EALS": "haz_eal_heatwave",
    "DRGT_EALS": "haz_eal_drought",
}


def main():
    p = download(URL, "fema_nri/NRI_Table_Counties.csv", timeout=900)
    ratings = [c.replace("_EALS", "_EALR") for c in COLS if c.endswith("_EALS")]
    df = pd.read_csv(p, usecols=["STCOFIPS", "NRI_VER", *COLS, *ratings])
    version = sorted(df["NRI_VER"].dropna().unique().tolist())
    n_na = {}
    for r in ratings:
        s = r.replace("_EALR", "_EALS")
        mask = df[r].eq("Not Applicable") & df[s].isna()
        n_na[COLS[s]] = int(mask.sum())
        df.loc[mask, s] = 0.0
    out = table_join(df, "STCOFIPS", {c: "mean" for c in COLS}, source="fema_nri").rename(columns=COLS)
    write_interim(out, "fema_nri")
    register_source(
        "fema_nri", raw_files=[p],
        name="FEMA National Risk Index, county table", url=URL, landing_page=FEMA_URL,
        mirror=f"Harvard Dataverse {DATAVERSE_DOI} (dataset version 2, released 2024-12-13)",
        vintage=f"NRI_VER = {', '.join(version)} (NRI v1.19.0)",
        license="Public domain (US Government work)",
        notes="hazards.fema.gov now redirects to the FEMA RAPT page; used the Dataverse mirror. "
              "Scores (0-100 percentile-type), not dollar values. Where the EAL rating is 'Not Applicable' "
              "(NRI: county not susceptible to the hazard) the blank score is set to 0, the same score NRI "
              f"gives 'No Expected Annual Losses'; counts set: {n_na}. 'Insufficient Data' stays NaN. "
              "CT is on old counties in this release and was area-weighted to planning regions.",
    )
    set_status("fema_nri", "OK", f"{len(out)} counties; NRI version {version}.", list(COLS.values()))


if __name__ == "__main__":
    main()
