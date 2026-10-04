"""Features from hand-maintained CSVs in data/manual/ (moratoria, state policy, contested projects).

Example rows (fips 00000, state ZZ/ZY) are ignored. A CSV with no real rows yields NaN features (unknown,
not 0) and a BLOCKED status, so the build works on the bare templates.
Time-to-power is handled in ingest_eia861 because it needs the utility-county map.
"""
import pandas as pd

from src.common import manual
from src.common.counties import load_counties
from src.common.fips_fixes import FIPS_RENAMES, STATE_FIPS_TO_ABBR
from src.common.io import MANUAL, download, register_source, set_status, write_interim

ADJ_URL = "https://www2.census.gov/geo/docs/reference/county-adjacency/county_adjacency2025.txt"
EXAMPLE_STATES = {"ZZ", "ZY"}


def _real(df: pd.DataFrame, col: str = "fips") -> pd.DataFrame:
    if col == "fips":
        df = df.assign(fips=df["fips"].str.strip().str.zfill(5).replace(FIPS_RENAMES))
        return df[df["fips"] != "00000"]
    return df[~df[col].str.strip().str.upper().isin(EXAMPLE_STATES)]


SUB_COUNTY_TYPES = ["city", "town", "township", "tribal"]


def moratoria(base: pd.DataFrame) -> pd.DataFrame:
    feats = ["prm_moratorium_active", "prm_moratorium_proposed"]
    m = _real(manual.load("local_moratoria.csv"))
    out = base[["fips"]].copy()
    if m.empty:
        for f in feats:
            out[f] = float("nan")
        set_status("manual_moratoria", "BLOCKED", "data/manual/local_moratoria.csv has only example rows.", feats)
        return out
    status = m["status"].str.strip().str.lower()
    typ = m["jurisdiction_type"].str.strip().str.lower()
    act = m[status == "active"]
    county = set(act.loc[typ[act.index] == "county", "fips"])
    sub = set(act.loc[typ[act.index].isin(SUB_COUNTY_TYPES), "fips"])
    other = sorted(set(typ[act.index]) - {"county", *SUB_COUNTY_TYPES})
    proposed = set(m.loc[status == "proposed", "fips"])
    out["prm_moratorium_active"] = out["fips"].map(lambda f: 1.0 if f in county else 0.5 if f in sub else 0.0)
    out["prm_moratorium_proposed"] = out["fips"].isin(proposed).astype(float)
    bad = sorted(set(m["fips"]) - set(base["fips"]))
    set_status("manual_moratoria", "OK" if not (bad or other) else "PARTIAL",
               f"{len(m)} rows ({len(act)} active, {int((status == 'proposed').sum())} proposed); active: "
               f"{len(county)} counties = 1, {len(sub - county)} = 0.5; proposed: {len(proposed)} counties. "
               f"Unknown fips ignored: {bad}. Unrecognised active jurisdiction types ignored: {other}", feats)
    return out


def state_policy(base: pd.DataFrame) -> pd.DataFrame:
    feats = ["prm_state_moratorium", "prm_tax_exemption_status", "prm_large_load_tariff", "prm_county_can_zone",
             "meta_state_policy_verified"]
    s = _real(manual.load("state_policy.csv"), "state_abbr")
    out = base[["fips"]].copy()
    out["state_abbr"] = out["fips"].str[:2].map(STATE_FIPS_TO_ABBR)
    if s.empty:
        for f in feats:
            out[f] = pd.Series(dtype="object" if f == "prm_tax_exemption_status" else "float64")
        set_status("manual_state_policy", "BLOCKED", "data/manual/state_policy.csv has only example rows.", feats)
        return out.drop(columns="state_abbr")
    s = s.assign(state_abbr=s["state_abbr"].str.strip().str.upper()).drop_duplicates("state_abbr", keep="last")
    num = lambda c: pd.to_numeric(s[c].replace("", None), errors="coerce")
    s = pd.DataFrame({
        "state_abbr": s["state_abbr"],
        "prm_state_moratorium": num("statewide_moratorium"),
        "prm_tax_exemption_status": s["tax_exemption_status"].str.strip().str.lower().replace("", None),
        "prm_large_load_tariff": num("large_load_tariff"),
        "prm_county_can_zone": num("county_zoning_authority"),
        "meta_state_policy_verified": num("verified") if "verified" in s else float("nan"),
    })
    out = out.merge(s, on="state_abbr", how="left").drop(columns="state_abbr")
    covered = out["prm_state_moratorium"].notna() | out["prm_tax_exemption_status"].notna()
    n_ver = int((s["meta_state_policy_verified"] == 1).sum())
    set_status("manual_state_policy", "OK" if s["state_abbr"].nunique() >= 49 else "PARTIAL",
               f"{s['state_abbr'].nunique()} states filled ({n_ver} verified, the rest template defaults); "
               f"{int(covered.sum())} counties covered, rest NaN.", feats)
    return out


def contested(base: pd.DataFrame) -> pd.DataFrame:
    feats = ["prm_contested_n", "prm_contested_neighbors_n", "lbl_contested_n"]
    c = _real(manual.load("contested_projects.csv"))
    out = base[["fips"]].copy()
    if c.empty:
        for f in feats:
            out[f] = float("nan")
        set_status("manual_contested", "BLOCKED", "data/manual/contested_projects.csv has only example rows.", feats)
        return out
    adj_path = download(ADJ_URL, "census_adjacency/county_adjacency2025.txt")
    adj = pd.read_csv(adj_path, sep="|", dtype=str)
    adj = adj.rename(columns={"County GEOID": "fips", "Neighbor GEOID": "nbr"})
    adj = adj[adj["fips"] != adj["nbr"]]
    n = c.groupby("fips").size()
    out["prm_contested_n"] = out["fips"].map(n).fillna(0)
    nb = adj.assign(k=adj["nbr"].map(n).fillna(0)).groupby("fips")["k"].sum()
    out["prm_contested_neighbors_n"] = out["fips"].map(nb).fillna(0)
    out["lbl_contested_n"] = out["prm_contested_n"]
    register_source("census_county_adjacency", raw_files=[adj_path], name="Census County Adjacency File 2025",
                    url=ADJ_URL, vintage="2025", license="Public domain (US Census Bureau)",
                    landing_page="https://www.census.gov/geographies/reference-files/time-series/geo/county-adjacency.html",
                    notes="Self-adjacency rows dropped. Uses 2025 geography (CT planning regions).")
    bad = sorted(set(c["fips"]) - set(base["fips"]))
    set_status("manual_contested", "OK" if not bad else "PARTIAL",
               f"{len(c)} contested projects in {c['fips'].nunique()} counties. Unknown fips ignored: {bad}", feats)
    return out


def main():
    base = load_counties()[["fips"]]
    out = moratoria(base).merge(state_policy(base), on="fips").merge(contested(base), on="fips")
    write_interim(out, "manual_features")
    register_source(
        "manual_csvs", raw_files=sorted(MANUAL.glob("*.csv")),
        name="Hand-maintained CSVs (data/manual/)", url="data/manual/",
        vintage="as edited", license="Project-internal; each row must carry its own source_url",
        notes=("local_moratoria -> prm_moratorium_active (status=active rows only: 1 if a county-level row, 0.5 if "
               "only city/town/township/tribal rows, else 0) and prm_moratorium_proposed (1 if any status=proposed "
               "row, any jurisdiction type); expired rows are ignored. state_policy -> prm_state_moratorium, "
               "prm_tax_exemption_status ('unknown' kept as a category), prm_large_load_tariff, prm_county_can_zone, "
               "meta_state_policy_verified (the CSV's verified column; unverified rows hold template defaults) "
               "(states absent from the CSV stay NaN); contested_projects -> prm_contested_n, "
               "prm_contested_neighbors_n (sum over Census-adjacent counties, self excluded), lbl_contested_n "
               "(same count, label use only). A CSV with only example rows gives NaN, not 0."),
    )


if __name__ == "__main__":
    main()
