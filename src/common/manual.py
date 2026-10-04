"""Manual CSV templates (created if missing; filled in by hand) and loaders."""
from __future__ import annotations

import pandas as pd

from .io import MANUAL

TEMPLATES = {
    "local_moratoria.csv": (
        ["fips", "jurisdiction_name", "jurisdiction_type", "status", "start_date", "end_date", "source_url", "notes"],
        [
            ["00000", "EXAMPLE County", "county", "active", "2025-01-01", "", "", "EXAMPLE ROW - replace (fips 00000 is ignored)"],
            ["00000", "EXAMPLE City", "city", "proposed", "2025-06-01", "", "", "EXAMPLE ROW - replace (fips 00000 is ignored)"],
        ],
    ),
    "state_policy.csv": (
        ["state_abbr", "statewide_moratorium", "tax_exemption_status", "large_load_tariff",
         "county_zoning_authority", "verified", "source_url", "notes"],
        [
            ["ZZ", "0", "active", "1", "1", "0", "", "EXAMPLE ROW - replace (state ZZ is ignored)"],
            ["ZY", "1", "paused", "0", "0", "0", "", "EXAMPLE ROW - replace (state ZY is ignored)"],
        ],
    ),
    "contested_projects.csv": (
        ["project_name", "developer", "fips", "state_abbr", "mw", "usd_bn", "year", "outcome", "main_reason", "source_url"],
        [
            ["EXAMPLE Project A", "EXAMPLE Dev", "00000", "ZZ", "300", "1.5", "2025", "abandoned", "water", ""],
            ["EXAMPLE Project B", "EXAMPLE Dev", "00000", "ZZ", "1000", "10", "2025", "delayed", "noise", ""],
        ],
    ),
    "utility_time_to_power.csv": (
        ["utility_name", "eia_utility_id", "iso", "years_to_power_est", "mw_basis", "as_of_date", "basis",
         "source_url", "notes"],
        [
            ["Virginia Electric & Power Co (Dominion Energy Virginia)", "19876", "PJM", "7", "", "", "published", "",
             "EXAMPLE from task brief (Northern Virginia, about 7 years) - add source_url before use"],
            ["Arizona Public Service Co", "803", "NONE", "", "", "", "not_accepting", "",
             "EXAMPLE from task brief: pause on new data center customers"],
            ["NATIONAL AVERAGE", "", "ALL", "", "", "", "published", "", "Fallback for counties with no utility value"],
        ],
    ),
}


def ensure_templates() -> None:
    for name, (cols, rows) in TEMPLATES.items():
        p = MANUAL / name
        if not p.exists():
            pd.DataFrame(rows, columns=cols).to_csv(p, index=False)
            print(f"[manual] created template {p}")


def load(name: str) -> pd.DataFrame:
    ensure_templates()
    return pd.read_csv(MANUAL / name, dtype=str).fillna("")
