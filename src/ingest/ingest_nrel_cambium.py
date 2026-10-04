"""NREL Cambium 2024: Mid-case long-run marginal CO2e emission rate (lrmer_co2e) in 2035, by GEA region -> county."""
import pandas as pd

from src.common.geo import table_join
from src.common.io import download, register_source, set_status, write_interim

URL = "https://data.nlr.gov/system/files/289/1744314776-Cambium24_Workbook.xlsx"
YEAR = 2035
SCENARIO = "Mid-case"
GWP_AR6_100 = {"CO2": 1.0, "CH4": 29.8, "N2O": 273.0}  # Cambium 2024 documentation, section 5
BLOCKS = {  # header text in row 2 of 'Data - Annual' -> (gas, unit divisor to kg)
    "CO2 from Direct Combustion": ("CO2", 1.0), "CH4 from Direct Combustion": ("CH4", 1000.0),
    "N2O from Direct Combustion": ("N2O", 1000.0), "CO2 from Precombustion": ("CO2", 1.0),
    "CH4 from Precombustion": ("CH4", 1000.0), "N2O from Precombustion": ("N2O", 1000.0),
}


def lrmer_by_gea(xlsx) -> pd.Series:
    d = pd.read_excel(xlsx, "Data - Annual", header=None)
    hdr_block, hdr_scen, hdr_year = d.iloc[2], d.iloc[3], d.iloc[4]
    regions = d.iloc[5:, 1].dropna()
    total = pd.Series(0.0, index=regions.values)
    block, scen = None, None
    found = 0
    for c in range(d.shape[1]):
        if isinstance(hdr_block[c], str):
            block = next((k for k in BLOCKS if hdr_block[c].startswith(k)), None)
        if isinstance(hdr_scen[c], str):
            scen = hdr_scen[c]
        if block and scen == SCENARIO and pd.notna(hdr_year[c]) and int(float(hdr_year[c])) == YEAR:
            gas, div = BLOCKS[block]
            vals = pd.to_numeric(d.loc[regions.index, c], errors="coerce").values
            total += GWP_AR6_100[gas] * vals / div
            found += 1
    if found != len(BLOCKS):
        raise RuntimeError(f"expected {len(BLOCKS)} gas/stage columns for {SCENARIO} {YEAR}, found {found}")
    return total


def main():
    p = download(URL, "nrel_cambium/Cambium24_Workbook.xlsx", timeout=600)
    gea = lrmer_by_gea(p)
    m = pd.read_excel(p, "County Mapping").iloc[:, :7]
    m["fips"] = m["State FIPS"].astype(int).astype(str).str.zfill(2) + m["County FIPS"].astype(int).astype(str).str.zfill(3)
    m["crb_lrmer_2035_kg_mwh"] = m["Cambium GEA"].map(gea)
    m["crb_cambium_gea"] = m["Cambium GEA"]
    unmapped = sorted(set(m["Cambium GEA"].dropna()) - set(gea.index))
    out = table_join(m[["fips", "crb_lrmer_2035_kg_mwh", "crb_cambium_gea"]], "fips",
                     {"crb_lrmer_2035_kg_mwh": "first", "crb_cambium_gea": "first"}, source="nrel_cambium")
    write_interim(out, "nrel_cambium")
    register_source(
        "nrel_cambium_2024", raw_files=[p], name="NREL Cambium 2024 Workbook (LRMER and GEA county mapping)", url=URL,
        landing_page="https://data.nlr.gov/submissions/289 ; https://data.openei.org/submissions/8395",
        vintage="Cambium 2024 (released March 2025; workbook 2025-04-10)", license="CC BY 4.0 (OEDI/NLR data catalog)",
        notes=(f"lrmer_co2e for {SCENARIO} {YEAR} rebuilt from the 'Data - Annual' tab as combustion + precombustion "
               "CO2 + 29.8*CH4 + 273*N2O (g->kg), AR6 100-yr GWPs as in Cambium docs. Units kg CO2e per MWh of end-use "
               "demand. Regional (18 GEAs), table-joined via the workbook 'County Mapping' tab (ReEDS BAs respect "
               f"county lines). GEA values: {gea.round(1).to_dict()}. Unmapped GEAs: {unmapped or 'none'}."),
    )
    set_status("nrel_cambium_2024", "OK", f"18 GEA regions mapped to {out['crb_lrmer_2035_kg_mwh'].notna().sum()} counties.",
               ["crb_lrmer_2035_kg_mwh", "crb_cambium_gea"])


if __name__ == "__main__":
    main()
