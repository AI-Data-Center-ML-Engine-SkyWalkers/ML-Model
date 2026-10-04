"""NREL US County-Level Industrial Energy Use (2014): low-temperature process heat proxy (food, beverage, paper)."""
import pandas as pd

from src.common.counties import load_counties
from src.common.fips_fixes import apply_fips_fixes
from src.common.io import download, register_source, set_status, write_interim

URL = "https://data.nlr.gov/system/files/97/manufacturing_EndUse.gz"
NAICS3 = ("311", "312", "322")
ENDUSE = "Process Heating"
FUELS = ["Coal", "Coke_and_breeze", "Diesel", "LPG_NGL", "Natural_gas", "Net_electricity", "Other",
         "Residual_fuel_oil"]


def main():
    p = download(URL, "nrel_industrial/manufacturing_EndUse.gz", allow_html=False, timeout=600)
    d = pd.read_csv(p, compression="gzip", usecols=["fips_matching", "naics", "Enduse", *FUELS])
    n3 = d["naics"].astype("Int64").astype(str).str[:3]
    sel = d[n3.isin(NAICS3) & (d["Enduse"] == ENDUSE)].copy()
    n_neg = int((sel["Net_electricity"] < 0).sum())
    sel["Net_electricity"] = sel["Net_electricity"].clip(lower=0)
    sel["Total_energy_use"] = sel[FUELS].sum(axis=1)
    sel["fips"] = sel["fips_matching"].astype(int).astype(str).str.zfill(5)
    agg = sel.groupby("fips", as_index=False)["Total_energy_use"].sum().rename(
        columns={"Total_energy_use": "cob_lowtemp_ind_heat_tbtu"})
    agg = apply_fips_fixes(agg, {"cob_lowtemp_ind_heat_tbtu": "sum"}, source="nrel_industrial_heat")
    out = load_counties()[["fips"]].merge(agg, on="fips", how="left").fillna({"cob_lowtemp_ind_heat_tbtu": 0.0})
    write_interim(out, "nrel_industrial_heat")
    register_source(
        "nrel_county_industrial_energy", raw_files=[p], name="NREL United States County-Level Industrial Energy Use",
        url=URL, landing_page="https://data.nlr.gov/submissions/97 ; https://doi.org/10.7799/1481899",
        vintage="Energy-use year 2014 (published 2018-09-27)", license="CC BY 4.0 (NREL Data Catalog)",
        notes=(f"FALLBACK per spec: the county file has no temperature field (temperatures exist only by SIC in "
               f"Process_temperatures.csv), so cob_lowtemp_ind_heat_tbtu = sum of Enduse '{ENDUSE}' (all fuels, TBtu) "
               f"for NAICS {NAICS3} (food, beverage, paper) - a proxy, not a measured <100C total. Boiler and CHP steam "
               "for these sectors (also largely low-temperature) are NOT included. Counties absent from the file = 0. "
               f"Total = sum of fuel columns with negative Net_electricity (on-site generation exported, e.g. paper "
               f"mills) floored at 0, since exports are not negative heat demand ({n_neg} rows affected). "
               "2014 county codes fixed (46113, 51515) and old CT counties converted by area weight."),
    )
    set_status("nrel_county_industrial_energy", "OK",
               f"{(out['cob_lowtemp_ind_heat_tbtu'] > 0).sum()} counties with food/beverage/paper process heat (proxy).",
               ["cob_lowtemp_ind_heat_tbtu"])


if __name__ == "__main__":
    main()
