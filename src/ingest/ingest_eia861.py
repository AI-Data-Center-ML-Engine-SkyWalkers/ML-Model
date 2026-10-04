"""EIA-861 (via Catalyst PUDL): utility -> county mapping and utility-derived county features.

Features: pwr_ind_price_cents_kwh, pwr_saidi_min, pwr_saifi, pwr_iso, pwr_time_to_power_yrs,
pwr_time_to_power_source, prm_price_growth_pct. Also writes the utility-county map to
data/interim/_utility_county_map.parquet for reuse.
"""
import numpy as np
import pandas as pd

from src.common import manual
from src.common.counties import load_counties
from src.common.fips_fixes import CT_OLD_COUNTIES, FIPS_RENAMES, ct_crosswalk
from src.common.io import INTERIM, MANUAL, download, register_source, set_status, unzip, write_interim

PUDL = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/stable/{t}.parquet"
YEAR = 2024  # latest final EIA-861 year (2025 is early release / provisional)
BASE_YEAR = 2020
REL_YEARS = range(2020, 2025)
NOT_ACCEPTING_EXTRA_YRS = 2  # basis=not_accepting -> max years in the CSV + this

BA_TO_ISO = {"PJM": "PJM", "ERCO": "ERCOT", "MISO": "MISO", "SWPP": "SPP", "CISO": "CAISO",
             "NYIS": "NYISO", "ISNE": "ISONE"}


RAW_URLS = {
    2024: "https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip",
    2020: "https://www.eia.gov/electricity/data/eia861/archive/zip/f8612020.zip",
}
CLASSES = ["residential", "commercial", "industrial", "transportation", "total"]
FEDERAL_PMA = [27000, 1738, 17716, 17000]  # WAPA, BPA, Southwestern PA, Southeastern PA (TVA kept)


def _pudl(t):
    p = download(PUDL.format(t=t), f"pudl/{t}.parquet", timeout=900)
    d = pd.read_parquet(p)
    d["yr"] = pd.to_datetime(d["report_date"]).dt.year
    return d, p


def read_raw_sales(year: int) -> tuple[pd.DataFrame, object]:
    """Long table from raw EIA-861 Sales_Ult_Cust (parts A-D) + Delivery_Companies (TX TDUs).

    PUDL's sales table omits the Delivery_Companies file, which holds the Texas wires utilities
    (CenterPoint, Oncor, AEP Texas, TNMP...), so the raw files are used for sales.
    """
    z = download(RAW_URLS[year], f"eia861/f861{year}.zip")
    folder = unzip(z)
    frames = []
    for f, sheet in [(f"Sales_Ult_Cust_{year}.xlsx", "States"), (f"Delivery_Companies_{year}.xlsx", 0)]:
        d = pd.read_excel(folder / f, sheet_name=sheet, header=2)
        d = d[pd.to_numeric(d["Utility Number"], errors="coerce").notna()]
        d = d[d["Utility Number"].astype(int) != 99999]  # state adjustment rows
        base = pd.DataFrame({
            "utility_id_eia": d["Utility Number"].astype(int).astype("Int64"),
            "state": d["State"], "service_type": d["Service Type"].str.lower(),
            "part": d["Part"], "ownership": d["Ownership"],
            "balancing_authority_code_eia": d["BA Code"],
        })
        for i, c in enumerate(CLASSES):
            sfx = "" if i == 0 else f".{i}"
            part = base.copy()
            part["customer_class"] = c
            part["sales_revenue"] = pd.to_numeric(d[f"Thousand Dollars{sfx}"], errors="coerce") * 1000
            part["sales_mwh"] = pd.to_numeric(d[f"Megawatthours{sfx}"], errors="coerce")
            frames.append(part)
    out = pd.concat(frames, ignore_index=True)
    out = out[out["customer_class"] != "total"]
    out["yr"] = year
    return out, z


def utility_county_map(st: pd.DataFrame) -> pd.DataFrame:
    """(utility_id_eia, state, fips) for CONUS counties; old CT counties expanded to regions."""
    m = st[st["yr"] == YEAR][["utility_id_eia", "state", "county_id_fips"]].dropna()
    m = m.rename(columns={"county_id_fips": "fips"})
    m["fips"] = m["fips"].replace(FIPS_RENAMES)
    xw = ct_crosswalk()
    xw = xw[xw["w_old"] > 0.01]
    ct = m[m["fips"].isin(CT_OLD_COUNTIES)].merge(xw[["old_fips", "new_fips"]], left_on="fips", right_on="old_fips")
    ct["fips"] = ct["new_fips"]
    m = pd.concat([m[~m["fips"].isin(CT_OLD_COUNTIES)], ct[["utility_id_eia", "state", "fips"]]])
    base = set(load_counties()["fips"])
    m = m[m["fips"].isin(base)].drop_duplicates()
    return m.reset_index(drop=True)


def state_avg_price(sales: pd.DataFrame, year: int) -> pd.Series:
    """All-sector state average retail price (cents/kWh): total revenue / (bundled + energy sales)."""
    s = sales[sales["yr"] == year]
    rev = s.groupby("state")["sales_revenue"].sum()
    mwh = s[s["service_type"].isin(["bundled", "energy"])].groupby("state")["sales_mwh"].sum()
    return 100 * rev / (mwh * 1000)


def main():
    st, p_st = _pudl("core_eia861__yearly_service_territory")
    rel, p_rel = _pudl("core_eia861__yearly_reliability")
    assert (st.loc[st["yr"] == YEAR, "data_maturity"] == "final").all()
    s_now, p_sales = read_raw_sales(YEAR)
    s_base, p_sales0 = read_raw_sales(BASE_YEAR)
    sales = pd.concat([s_now, s_base], ignore_index=True)

    ucm = utility_county_map(st)
    ucm.to_parquet(INTERIM / "_utility_county_map.parquet", index=False)

    s = sales[sales["yr"] == YEAR]
    ind = s[s["customer_class"] == "industrial"]

    # ---- industrial price per utility-state
    # Federal power marketing administrations sell wholesale plus a few special contracts; their
    # territories cover whole regions, so they are left out of county retail price weighting.
    retail = ind[~ind["utility_id_eia"].isin(FEDERAL_PMA)]
    g = retail[retail["part"].isin(["A", "C"])].groupby(
        ["utility_id_eia", "state", "service_type"], observed=True)[["sales_revenue", "sales_mwh"]].sum()
    g = g.unstack("service_type").fillna(0)
    rev = lambda t: g[("sales_revenue", t)] if ("sales_revenue", t) in g else 0  # noqa: E731
    mwh = lambda t: g[("sales_mwh", t)] if ("sales_mwh", t) in g else 0  # noqa: E731

    def _state_price(rows):
        t = rows.groupby("state")[["sales_revenue", "sales_mwh"]].sum()
        t = t[t["sales_mwh"] > 0]
        return t["sales_revenue"] / (t["sales_mwh"] * 1000)

    # Retail-choice states: delivery-only utilities carry only the wires charge. Add the state's
    # energy-only (Part B) industrial price; where suppliers report all-in bundled service by
    # retail marketers instead (Part D, e.g. Texas), use that all-in price.
    energy_price = _state_price(ind[ind["part"] == "B"])
    partd_price = _state_price(ind[ind["part"] == "D"])
    up = pd.DataFrame(index=g.index)
    up["bundled_mwh"], up["delivery_mwh"] = mwh("bundled"), mwh("delivery")
    up["bundled_price"] = rev("bundled") / (up["bundled_mwh"] * 1000)
    up["delivery_price"] = rev("delivery") / (up["delivery_mwh"] * 1000)
    up = up.reset_index()
    up["delivery_full_price"] = np.where(
        up["state"].isin(energy_price.index),
        up["delivery_price"] + up["state"].map(energy_price),
        up["state"].map(partd_price),
    )
    up["ind_mwh"] = up["bundled_mwh"] + up["delivery_mwh"]
    num = up["bundled_price"].fillna(0) * up["bundled_mwh"] + up["delivery_full_price"].fillna(0) * up["delivery_mwh"]
    den = up["bundled_mwh"].where(up["bundled_price"].notna(), 0) + \
        up["delivery_mwh"].where(up["delivery_full_price"].notna(), 0)
    up["ind_price"] = (num / den).where(den > 0)  # $/kWh
    up = up[["utility_id_eia", "state", "ind_price", "ind_mwh"]]

    cm = ucm.merge(up, on=["utility_id_eia", "state"], how="left")
    ok = cm["ind_price"].notna() & (cm["ind_mwh"] > 0)
    price = cm[ok].groupby("fips").apply(
        lambda d: 100 * np.average(d["ind_price"], weights=d["ind_mwh"]), include_groups=False)

    # ---- reliability (IEEE standard), simple mean across the county's utilities.
    # Main columns: per utility-state median of REL_YEARS without major event days.
    # *_with_me_latest: YEAR only, with major event days (kept for reference).
    ieee = rel[rel["standard"] == "ieee_standard"]
    wo = ["saidi_wo_major_event_days_minutes", "saifi_wo_major_event_days_customers"]
    w = ["saidi_w_major_event_days_minutes", "saifi_w_major_event_days_customers"]
    assert (ieee.loc[ieee["yr"].isin(REL_YEARS), "data_maturity"] == "final").all()
    r_med = (ieee[ieee["yr"].isin(REL_YEARS)].groupby(["utility_id_eia", "state", "yr"])[wo].mean()
             .groupby(["utility_id_eia", "state"]).median().reset_index())
    r_me = ieee[ieee["yr"] == YEAR].groupby(["utility_id_eia", "state"])[w].mean().reset_index()
    cr = ucm.merge(r_med, on=["utility_id_eia", "state"], how="inner").groupby("fips")[wo].mean()
    cr_me = ucm.merge(r_me, on=["utility_id_eia", "state"], how="inner").groupby("fips")[w].mean()

    # ---- ISO from the BA of the county's main utility (largest total retail sales in the state)
    tot = s[s["service_type"].isin(["bundled", "delivery"])].groupby(["utility_id_eia", "state"]).agg(
        mwh=("sales_mwh", "sum"),
        ba=("balancing_authority_code_eia", lambda x: x.dropna().mode().iloc[0] if x.notna().any() else None),
    ).reset_index()
    ct_ = ucm.merge(tot, on=["utility_id_eia", "state"], how="left")
    ct_["mwh"] = ct_["mwh"].fillna(0)
    main_u = ct_.sort_values(["fips", "mwh"], ascending=[True, False]).drop_duplicates("fips")
    iso = main_u.set_index("fips")["ba"].map(lambda b: BA_TO_ISO.get(b, "NONE") if pd.notna(b) else np.nan)
    main_util = main_u.set_index("fips")["utility_id_eia"]

    # ---- time to power from manual CSV
    # Priority: a serving utility with basis=not_accepting -> max years in the CSV + 2; else sales-weighted mean
    # of serving utilities with a value; else the NATIONAL AVERAGE row. Rows with empty years are ignored.
    ttp = manual.load("utility_time_to_power.csv")
    ttp["years"] = pd.to_numeric(ttp["years_to_power_est"], errors="coerce")
    basis = ttp["basis"].str.strip().str.lower() if "basis" in ttp else pd.Series("", index=ttp.index)
    is_util = ttp["eia_utility_id"].str.strip() != ""
    national = ttp.loc[ttp["utility_name"].str.strip().str.upper() == "NATIONAL AVERAGE", "years"].dropna()
    national_yrs = float(national.iloc[0]) if len(national) else np.nan
    not_acc_yrs = ttp["years"].max() + NOT_ACCEPTING_EXTRA_YRS
    uid = lambda d: pd.to_numeric(d["eia_utility_id"]).astype("Int64")  # noqa: E731
    na_ids = set(uid(ttp[is_util & (basis == "not_accepting")]))
    ttp_u = ttp[is_util & (basis != "not_accepting")].dropna(subset=["years"])
    ttp_u = ttp_u.assign(utility_id_eia=uid(ttp_u))
    cu = ct_.merge(ttp_u[["utility_id_eia", "years"]], on="utility_id_eia", how="inner")
    util_val = cu.groupby("fips").apply(
        lambda d: np.average(d["years"], weights=d["mwh"]) if d["mwh"].sum() > 0 else d["years"].mean(),
        include_groups=False)
    na_fips = set(ct_.loc[ct_["utility_id_eia"].isin(na_ids), "fips"])

    # ---- state price growth
    p0, p1 = state_avg_price(sales, BASE_YEAR), state_avg_price(sales, YEAR)
    growth = 100 * (p1 / p0 - 1)

    base = load_counties()[["fips", "meta_state_abbr"]]
    out = base.copy()
    out["pwr_ind_price_cents_kwh"] = out["fips"].map(price)
    out["pwr_saidi_min"] = out["fips"].map(cr[wo[0]])
    out["pwr_saifi"] = out["fips"].map(cr[wo[1]])
    out["pwr_saidi_min_with_me_latest"] = out["fips"].map(cr_me[w[0]])
    out["pwr_saifi_with_me_latest"] = out["fips"].map(cr_me[w[1]])
    out["pwr_iso"] = out["fips"].map(iso)
    out["pwr_main_utility_id"] = out["fips"].map(main_util).astype("Int64")
    out["pwr_time_to_power_yrs"] = out["fips"].map(util_val)
    out["pwr_time_to_power_source"] = np.where(out["pwr_time_to_power_yrs"].notna(), "utility", "none")
    na_rows = out["fips"].isin(na_fips)
    out.loc[na_rows, "pwr_time_to_power_yrs"] = not_acc_yrs
    out.loc[na_rows, "pwr_time_to_power_source"] = "not_accepting"
    nat_rows = out["pwr_time_to_power_yrs"].isna() & pd.notna(national_yrs)
    out.loc[nat_rows, "pwr_time_to_power_yrs"] = national_yrs
    out.loc[nat_rows, "pwr_time_to_power_source"] = "national"
    out["prm_price_growth_pct"] = out["meta_state_abbr"].map(growth)
    out = out.drop(columns="meta_state_abbr")
    write_interim(out, "eia861_utility")

    register_source(
        "eia861_pudl", raw_files=[p_st, p_rel, p_sales, p_sales0],
        name="EIA-861 Annual Electric Power Industry Report (service territory + reliability via Catalyst "
             "PUDL stable; sales from raw EIA-861 files)",
        url=f"{PUDL.format(t='core_eia861__yearly_{service_territory|reliability}')} ; "
            f"{RAW_URLS[YEAR]} ; {RAW_URLS[BASE_YEAR]}",
        landing_page="https://data.catalyst.coop ; https://www.eia.gov/electricity/data/eia861/",
        vintage=f"EIA-861 {YEAR} (final); {BASE_YEAR} for price growth; reliability {REL_YEARS.start}-{YEAR}",
        license="EIA data public domain; PUDL outputs CC-BY-4.0 (Catalyst Cooperative)",
        notes=("APPROXIMATION: utility service territories list every county a utility serves, not how much. "
               "Industrial price = weighted by each utility's industrial MWh in the state; bundled price = "
               "revenue/sales; delivery-only (retail-choice) utilities get their wires charge plus the state's "
               "average energy-only (Part B) industrial price, or, where suppliers report all-in service as "
               "Part D retail marketers (Texas), the state's Part D industrial price. Federal power marketing "
               "administrations (WAPA, BPA, SWPA, SEPA) are excluded from price weighting. Sales come from the "
               "raw EIA-861 files because PUDL omits Delivery_Companies (Texas TDUs). pwr_saidi_min / pwr_saifi = "
               f"IEEE standard WITHOUT major event days, median of {REL_YEARS.start}-{REL_YEARS.stop - 1} per "
               "utility-state (over the years it reported), then simple mean across the county's utilities; "
               f"*_with_me_latest = IEEE standard WITH major event days, {YEAR} only, same mean. ISO = BA of the county's largest-sales utility "
               "(PJM, ERCO, MISO, SWPP, CISO, NYIS, ISNE; everything else NONE). Price growth = state all-sector "
               f"revenue/(bundled+energy sales), {BASE_YEAR}->{YEAR}. CT service territories are on old "
               "counties; a utility serving an old county is mapped to every planning region overlapping it."),
    )
    n = out.notna().sum().to_dict()
    set_status("eia861_pudl", "OK", f"non-null counts: {n}",
               ["pwr_ind_price_cents_kwh", "pwr_saidi_min", "pwr_saifi", "pwr_saidi_min_with_me_latest",
                "pwr_saifi_with_me_latest", "pwr_iso", "prm_price_growth_pct"])
    src_n = out["pwr_time_to_power_source"].value_counts().to_dict()
    set_status("manual_time_to_power", "PARTIAL" if src_n.get("utility", 0) + src_n.get("not_accepting", 0)
               else "BLOCKED",
               f"Manual CSV data/manual/utility_time_to_power.csv: counties by source {src_n}; not_accepting = "
               f"{not_acc_yrs:g} yrs (CSV max + {NOT_ACCEPTING_EXTRA_YRS}); national fallback = {national_yrs:g} yrs.",
               ["pwr_time_to_power_yrs", "pwr_time_to_power_source"])
    register_source(
        "manual_time_to_power", raw_files=[MANUAL / "utility_time_to_power.csv"],
        name="Hand-maintained utility time-to-power CSV (data/manual/utility_time_to_power.csv)",
        url="data/manual/utility_time_to_power.csv", vintage="as edited",
        license="Project-internal; each row carries its own source_url",
        notes=("Mapped to counties with the EIA-861 service-territory map. A county served by ANY utility with "
               f"basis=not_accepting gets max(years_to_power_est) + {NOT_ACCEPTING_EXTRA_YRS} and source "
               "not_accepting (overrides other utilities). Otherwise the sales-weighted mean of serving utilities "
               "with a value (source utility). Rows with empty years_to_power_est are ignored. Every other county "
               "gets the NATIONAL AVERAGE row (source national). No ISO-level fallback."),
    )


if __name__ == "__main__":
    main()
