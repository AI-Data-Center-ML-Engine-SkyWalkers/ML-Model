"""LBNL 'Queued Up' interconnection queue data: active clean MW per county and median IR->COD years by region."""
import json
import re

import pandas as pd

from src.common.fips_fixes import STATE_FIPS_TO_ABBR
from src.common.geo import table_join
from src.common.io import INTERIM, RAW, download, register_source, set_status, write_interim

PAGE = "https://eta-publications.lbl.gov/publications/us-interconnection-queue-data-0"
URL = "https://eta-publications.lbl.gov/sites/default/files/2026-05/lbnl_ix_queue_data_file_thru2025.xlsx"
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/128 Safari/537.36")
CLEAN = {"Solar", "Wind", "Offshore Wind", "Battery", "Other Storage", "Nuclear", "Geothermal"}
ISO_TO_REGION = {"CAISO": "CAISO", "ERCOT": "ERCOT", "ISONE": "ISO-NE", "MISO": "MISO", "NYISO": "NYISO",
                 "PJM": "PJM", "SPP": "SPP"}
# Pre-2022 Connecticut counties (Census names); queue rows still use them.
CT_OLD_NAMES = {"fairfield": "09001", "hartford": "09003", "litchfield": "09005", "middlesex": "09007",
                "new haven": "09009", "new london": "09011", "tolland": "09013", "windham": "09015"}
ABBR_TO_STATE_FIPS = {v: k for k, v in STATE_FIPS_TO_ABBR.items()}


def _norm(name: str) -> str:
    s = str(name).lower().replace("&", "and")
    s = re.sub(r"\bst\.?\s", "saint ", s)
    s = re.sub(r"\bste\.?\s", "sainte ", s)
    s = re.sub(r"\b(county|parish|borough|census area|municipality)\b", "", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _name_index() -> dict[tuple[str, str], str]:
    base = pd.read_parquet(INTERIM / "_base_counties.parquet", columns=["fips", "meta_county_name", "meta_state_abbr"])
    idx = {}
    for r in base.itertuples():
        n = _norm(r.meta_county_name)
        is_city = r.meta_county_name.lower().endswith(" city") and r.meta_state_abbr == "VA"
        idx[(r.meta_state_abbr, n)] = r.fips
        if not is_city:
            idx.setdefault((r.meta_state_abbr, n.removesuffix(" city").strip()), r.fips)
    idx.update({("CT", k): v for k, v in CT_OLD_NAMES.items()})
    return idx


def assign_fips(d: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    raw = d["fips_code"].map(lambda x: f"{int(x):05d}" if pd.notna(x) else None)
    st_ok = [isinstance(f, str) and STATE_FIPS_TO_ABBR.get(f[:2]) == s for f, s in zip(raw, d["state"])]
    idx = _name_index()
    out, method = [], []
    for f, ok, s, c in zip(raw, st_ok, d["state"], d["county"]):
        if ok:
            out.append(f), method.append("lbnl_fips")
            continue
        first = str(c).split(",")[0].split("/")[0] if pd.notna(c) else ""
        m = idx.get((s, _norm(first))) if first else None
        out.append(m), method.append("name_match" if m else "unmatched")
    return pd.Series(out, index=d.index), pd.Series(method, index=d.index)


def main():
    path = download(URL, RAW / "lbnl_queue" / "lbnl_ix_queue_data_file_thru2025.xlsx",
                    headers={"Referer": PAGE}, user_agent=BROWSER_UA, min_bytes=1_000_000)
    d = pd.read_excel(path, sheet_name="03. Complete Queue Data", header=1)
    d["fips"], d["fips_method"] = assign_fips(d)

    act = d[d["q_status"] == "active"].copy()
    act["clean_mw"] = sum(act[f"mw_{i}"].where(act[f"type_{i}"].isin(CLEAN), 0).fillna(0) for i in (1, 2, 3))
    act = act[act["clean_mw"] > 0]
    unmatched = act[act["fips"].isna()]
    log = RAW / "lbnl_queue" / "unmatched_active_clean.csv"
    unmatched[["q_id", "entity", "state", "county", "fips_code", "type_clean", "clean_mw"]].to_csv(log, index=False)
    agg = act.dropna(subset=["fips"]).groupby("fips", as_index=False)["clean_mw"].sum()
    agg = agg.rename(columns={"clean_mw": "crb_queue_clean_mw"})
    q = table_join(agg, "fips", {"crb_queue_clean_mw": "sum"}, source="lbnl_queue")

    op = d[(d["q_status"] == "operational") & d["on_date"].notna() & d["q_date"].notna()].copy()
    op["yrs"] = (pd.to_datetime(op["on_date"]) - pd.to_datetime(op["q_date"])).dt.days / 365.25
    op = op[op["yrs"] >= 0]
    med = op.groupby("region")["yrs"].median()
    n_by_region = op.groupby("region").size()

    non_iso = d[d["region"].isin(["West", "Southeast"])]
    state_region = non_iso.groupby("state")["region"].agg(lambda s: s.value_counts().idxmax())
    util = pd.read_parquet(INTERIM / "eia861_utility.parquet", columns=["fips", "pwr_iso"])
    util["state"] = util["fips"].str[:2].map(STATE_FIPS_TO_ABBR)
    util["region"] = util["pwr_iso"].map(ISO_TO_REGION)
    none = util["pwr_iso"] == "NONE"
    util.loc[none, "region"] = util.loc[none, "state"].map(state_region)
    util["pwr_gen_queue_median_yrs"] = util["region"].map(med)

    out = util[["fips", "pwr_gen_queue_median_yrs"]].merge(q, on="fips", how="left")
    out["crb_queue_clean_mw"] = out["crb_queue_clean_mw"].fillna(0)
    write_interim(out, "lbnl_queue")

    meth = act["fips_method"].value_counts().to_dict()
    register_source(
        "lbnl_queue", raw_files=[path, log],
        name="LBNL Queued Up: U.S. Interconnection Queue Data Through 2025 (Complete Interconnection Request Dataset)",
        url=URL, landing_page=PAGE, vintage="Queued Up 2026 edition, data through end of 2025 (file dated 2026-05)",
        license="CC BY 4.0 (Lawrence Berkeley National Laboratory)",
        notes=(
            "emp.lbl.gov is behind a Cloudflare challenge; the same file is served from eta-publications.lbl.gov "
            "(needs a browser User-Agent + Referer). crb_queue_clean_mw: q_status == active, sum of mw_1..3 whose "
            "type_1..3 is Solar/Wind/Offshore Wind/Battery/Other Storage/Nuclear/Geothermal (hydro excluded). "
            "County = LBNL fips_code when its state prefix matches 'state'; otherwise first listed county name "
            f"matched to the base layer by state + normalized name. Active clean rows by method: {meth}; "
            f"unmatched rows logged in {log.name} ({len(unmatched)} rows, {unmatched['clean_mw'].sum():,.0f} MW). "
            "Counties with no active clean requests = 0. Multi-county projects are credited to the first county only. "
            "pwr_gen_queue_median_yrs: median (on_date - q_date) in years over all operational requests with both "
            f"dates, by LBNL region (n per region: {json.dumps(n_by_region.to_dict())}). Joined via pwr_iso; "
            "counties with pwr_iso NONE get LBNL's non-ISO region (West or Southeast) that holds most of their "
            "state's non-ISO requests. Regions with no operational requests carrying both dates (here: "
            f"{sorted(set(ISO_TO_REGION.values()) - set(med.index))}) and counties with no pwr_iso stay NaN. "
            "This is a generator-interconnection congestion proxy, NOT a load interconnection wait time."
        ),
    )
    set_status("lbnl_queue", "OK",
               f"{len(act)} active clean requests ({act['clean_mw'].sum()/1000:,.0f} GW); {len(unmatched)} unmatched "
               f"rows logged. Region medians: {med.round(2).to_dict()}",
               ["crb_queue_clean_mw", "pwr_gen_queue_median_yrs"])


if __name__ == "__main__":
    main()
