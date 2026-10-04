"""Run every ingest script, then build and validate.

    python run_all.py                  # everything
    python run_all.py --only peeringdb # one source (module name without the ingest_ prefix), then build+validate
    python run_all.py --skip-validate

A failing source is logged and the run continues; its features stay NaN (see data/SOURCES_STATUS.md).
"""
import argparse
import importlib
import time
import traceback

from src.common.io import set_status

# Order matters only for scripts that read another script's interim helper file.
ORDER = [
    "base",                     # county base layer, CT crosswalk, population centroids
    "eia860",                   # writes _eia860_plants (used by eia860m, eia923_water)
    "eia860m",                  # writes _retired_plants_100mw (used by epa_brownfields)
    "eia861",                   # writes pwr_iso + utility-county map (used by lbnl_queue)
    "epa_egrid",                # writes _egrid_subregions (used by eia923_water)
    "eia923_water",
    "hifld_transmission", "hifld_pipelines", "osm_substations", "lbnl_queue",
    "nrel_cambium", "nrel_reeds_cf",
    "wri_aqueduct", "usdm_drought", "usgs_water_use", "epa_cwns",
    "fema_nri", "wildfire_risk", "noaa_nclimgrid", "cmra",
    "nlcd", "padus", "epa_brownfields", "bts_interstates", "peeringdb", "gem_heavy_industry",
    "epa_greenbook", "census_aiannh", "nps_nrhp", "manual_features",
    "bls_laus", "census_acs", "ers_typology", "netl_energy_comm", "epa_ghgrp", "nrel_industrial_heat",
    "pnnl_im3", "epoch_ai",
    # Phase B (finished). Skipped for time: nsrdb_free_cooling, free_cooling_2050,
    # lmp_negative_prices, 3dep_slope, fema_nfhl. FCC fiber never started.
    "nri_future", "usgs_karst", "cejst", "bls_qcew",
]


def run(name: str) -> bool:
    t0 = time.time()
    print(f"\n=== ingest_{name} ===", flush=True)
    try:
        importlib.import_module(f"src.ingest.ingest_{name}").main()
        print(f"=== ingest_{name} done in {time.time() - t0:.0f}s", flush=True)
        return True
    except Exception as e:  # keep going; the source's features stay NaN
        traceback.print_exc()
        set_status(name, "FAILED", f"{type(e).__name__}: {e}"[:400])
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="ingest module names (without ingest_)")
    ap.add_argument("--skip-ingest", action="store_true")
    ap.add_argument("--skip-validate", action="store_true")
    a = ap.parse_args()
    failed = []
    if not a.skip_ingest:
        for name in (a.only or ORDER):
            if not run(name):
                failed.append(name)
    from src.build import build_features, validate
    build_features.build()
    if not a.skip_validate:
        validate.main()
    if failed:
        print(f"\nFailed sources (features left NaN): {failed}")


if __name__ == "__main__":
    main()
