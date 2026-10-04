# AI Data Center Decision Engine

County-level feature pipeline and scoring engine for siting a 300 MW to 1 GW sustainable AI data center.
Public datasets are downloaded, aggregated to US counties, then scored with config-driven exclusions, pillars,
and robustness checks.

Outputs, in `data/processed/`:

- `county_features.parquet` and `county_features.csv`: 3,109 rows (CONUS + DC; Connecticut uses the 2022 planning
  regions 09110-09190; Virginia independent cities are their own rows), keyed by `fips` (5-character string).
- `data_dictionary.csv`: column, pillar, description, unit, source, vintage, join_method, higher_is, notes.

Provenance: `data/sources.yaml` (source, version/vintage, download date, license, method notes per dataset) and
`data/SOURCES_STATUS.md` (OK / PARTIAL / BLOCKED / FAILED / SKIPPED per source). QA: `reports/validation_report.md` and one
quantile choropleth per feature in `reports/maps/`.

**Rule: nothing is estimated or imputed.** If a source cannot be downloaded or needs a key we do not have, its
features are NaN and the reason is in `SOURCES_STATUS.md`.

## Setup and API keys

```bash
make setup            # python3 -m venv .venv && pip install -r requirements.txt  (Python 3.11+)
```

Keys are read from the environment or from a `.env` file in this folder (`KEY=value` lines; `.env` is gitignored).
All are free:

| Variable | Needed for | Without it |
|---|---|---|
| `CONTACT_EMAIL` | BLS (User-Agent), NREL NSRDB (required parameter) | BLS uses a placeholder; NSRDB is BLOCKED |
| `NREL_API_KEY` | `haz_free_cooling_pct_hours`, `haz_wetbulb_gt26c_hours` (https://developer.nlr.gov/signup/) | BLOCKED (NaN) |

The NSRDB script makes ~3,108 calls (one per county, about 2 s apart) and caches every response, so it can be
re-run to resume after a rate limit.

## Running

```bash
make all                     # every ingest script (downloads are cached in data/raw/), then build + validate
make source S=peeringdb      # one source (module name without the ingest_ prefix), then rebuild + validate
make build                   # merge data/interim/*.parquet -> data/processed/
make validate                # report + maps
make test                    # unit tests for the geometry helpers
```

Equivalent: `python run_all.py [--only NAME ...] [--skip-ingest] [--skip-validate]`, or run a single script with
`python -m src.ingest.ingest_<name>`. Every script is re-runnable: raw files are downloaded once to `data/raw/` and
reused. A failing source is logged and the run continues.

```bash
make score                   # exclusions, pillar scores, robustness, sanity
make app                     # Streamlit demo (reads outputs/)
```

Scoring config is `config/scoring.yaml`. Rankings and reports write to `outputs/`.

The manual inputs in `data/manual/` (moratoria, state policy, contested projects, utility time-to-power) can carry
extra columns (`verified` on `state_policy.csv`, `basis` on `utility_time_to_power.csv`). Example rows are ignored
(fips `00000`, states `ZZ`/`ZY`), and a CSV with no real rows yields NaN (unknown), not 0. After editing, run
`make source S="manual_features eia861"`.

## Layout

```
config/          scoring.yaml (weights, exclusions, personas, manual adjustments)
data/raw/        cached downloads (gitignored; never edited)
data/interim/    one parquet per source (gitignored); files starting with _ are helpers
data/manual/     hand-maintained CSVs
data/processed/  county feature table + data dictionary
outputs/         rankings, robustness, sanity report, Streamlit artifacts
src/common/      counties, geo, io, fips fixes
src/ingest/      one script per source
src/build/       feature dictionary, merge, validate
src/score/       exclusions, scores, robustness, sanity, trade-off
app.py           Streamlit demo
```

Geometry: stored in EPSG:4269; areas, overlays and distances in EPSG:5070 (CONUS Albers). Distances are measured
from the 2020 Census center of population of each county. FIPS fixes: 46113 -> 46102, 51515 -> 51019 (and
51560 -> 51005). Connecticut table data on the old 8 counties is converted to planning regions with an area
crosswalk (sums split by area share; means area-weighted; flags/categories take the dominant old county).

## Columns

See `data/processed/data_dictionary.csv` for units, sources, vintages and join methods.
`higher_is` is better / worse / context / label / id from a siting point of view. `lbl_*` columns are validation
labels and must never be model inputs.

**key**

- `fips` (code): 5-digit county FIPS (CT = planning regions 09110-09190)

**metadata**

- `meta_county_name` (text): County name
- `meta_state_abbr` (text): State postal abbreviation
- `meta_state_fips` (code): 2-digit state FIPS
- `meta_land_area_km2` (km2): Land area (ALAND)
- `meta_pop_centroid_lat` (deg): Latitude of 2020 Census center of population
- `meta_pop_centroid_lon` (deg): Longitude of 2020 Census center of population
- `meta_pop_2023` (people): Total population (ACS 2019-2023 5-year B01003)

**power**

- `pwr_gen_capacity_mw` (MW): Operating + standby generator nameplate capacity
- `pwr_retired_capacity_mw` (MW): Retired generator nameplate capacity (brownfield grid connections)
- `pwr_dist_retired_plant_km` (km): Distance from pop. centroid to nearest retired plant >= 100 MW
- `pwr_hv230_line_km` (km): Length of transmission lines >= 230 kV inside the county
- `pwr_dist_hv230_line_km` (km): Distance from pop. centroid to nearest >= 230 kV line
- `pwr_hv345_line_km` (km): Length of transmission lines >= 345 kV inside the county
- `pwr_dist_hv345_line_km` (km): Distance from pop. centroid to nearest >= 345 kV line
- `pwr_substations_230kv_n` (count): OSM substations with max voltage >= 230 kV
- `pwr_gas_pipeline_km` (km): Length of interstate + intrastate natural gas pipelines in the county
- `pwr_ind_price_cents_kwh` (cents/kWh): Industrial electricity price of the county's serving utilities
- `pwr_saidi_min` (minutes/yr): SAIDI without major events, 2020-2024 median, mean of serving utilities
- `pwr_saifi` (interruptions/yr): SAIFI without major events, 2020-2024 median, mean of serving utilities
- `pwr_saidi_min_with_me_latest` (minutes/yr): SAIDI incl. major events, 2024 only (reference)
- `pwr_saifi_with_me_latest` (interruptions/yr): SAIFI incl. major events, 2024 only (reference)
- `pwr_iso` (category): ISO/RTO of the county's main utility (NONE = outside an ISO)
- `pwr_main_utility_id` (id): EIA utility ID of the county's main (largest-sales) utility
- `pwr_time_to_power_yrs` (years): Reported years to energize a large load (utility, else national average)
- `pwr_time_to_power_source` (category): Basis of pwr_time_to_power_yrs (utility / not_accepting / national / none)
- `pwr_gen_queue_median_yrs` (years): Median years from interconnection request to COD for completed generators, by region
- `pwr_neg_price_pct_hours` (percent 0-100): Share of real-time hours with LMP <= $0/MWh (BLOCKED)
- `pwr_neg_price_available` (0/1): 1 if the county is in an ISO market with nodal prices (BLOCKED)

**carbon**

- `crb_grid_co2_kg_mwh` (kg CO2/MWh): eGRID subregion annual CO2 total output emission rate
- `crb_lrmer_2035_kg_mwh` (kg CO2e/MWh): Long-run marginal CO2e emission rate, Mid-case 2035
- `crb_cambium_gea` (category): Cambium generation-and-emission assessment region
- `crb_clean_gen_mw` (MW): Operating nuclear, hydro, wind, solar, geothermal capacity
- `crb_queue_clean_mw` (MW): Active interconnection-queue MW of solar, wind, storage, nuclear, geothermal
- `crb_solar_cf` (fraction 0-1): Utility-scale PV mean capacity factor (reference siting)
- `crb_wind_cf` (fraction 0-1): Onshore wind mean capacity factor (reference siting)

**water**

- `wtr_bws_score` (score 0-5): Aqueduct 4.0 baseline water stress score
- `wtr_bws_2050_score` (score 0-5): Aqueduct 4.0 water stress 2050, business-as-usual (SSP3-7.0)
- `wtr_drought_d2plus_pct_weeks` (percent 0-100): Share of weeks 2000-2025 with any D2-D4 drought
- `wtr_grid_water_l_kwh` (L/kWh): Indirect water: power-sector cooling water consumed per kWh, eGRID subregion
- `wtr_total_withdrawal_mgd` (Mgal/d): 2020 withdrawals: public supply + irrigation + thermoelectric
- `wtr_ps_withdrawal_mgd` (Mgal/d): 2020 public-supply withdrawals
- `wtr_irr_withdrawal_mgd` (Mgal/d): 2020 crop irrigation withdrawals
- `wtr_te_withdrawal_mgd` (Mgal/d): 2020 thermoelectric withdrawals (fresh + saline)
- `wtr_wwtp_flow_mgd` (Mgal/d): Design flow of wastewater treatment plants (reclaimed-water potential)

**climate_hazard**

- `haz_nri_risk_score` (score 0-100): FEMA National Risk Index composite risk score
- `haz_eal_riverine_flood` (score 0-100): NRI expected annual loss score: riverine flooding
- `haz_eal_coastal_flood` (score 0-100): NRI expected annual loss score: coastal flooding
- `haz_eal_hurricane` (score 0-100): NRI expected annual loss score: hurricane
- `haz_eal_wildfire` (score 0-100): NRI expected annual loss score: wildfire
- `haz_eal_tornado` (score 0-100): NRI expected annual loss score: tornado
- `haz_eal_earthquake` (score 0-100): NRI expected annual loss score: earthquake
- `haz_eal_heatwave` (score 0-100): NRI expected annual loss score: heat wave
- `haz_eal_drought` (score 0-100): NRI expected annual loss score: drought
- `haz_eal_coastal_flood_future` (score 0-100): NRI Future Risk projected risk, mid-century: coastal flooding
- `haz_eal_drought_future` (score 0-100): NRI Future Risk projected risk, mid-century: drought
- `haz_eal_heatwave_future` (score 0-100): NRI Future Risk projected risk, mid-century: extreme heat
- `haz_eal_hurricane_future` (score 0-100): NRI Future Risk projected risk, mid-century: hurricane
- `haz_eal_wildfire_future` (score 0-100): NRI Future Risk projected risk, mid-century: wildfire
- `haz_wildfire_risk_to_homes` (percentile 0-100): Wildfire Risk to Communities: national percentile of risk to homes
- `haz_cdd_annual` (degree-days F): Mean annual cooling degree days, base 65F, 1991-2020
- `haz_days_tmax_gt35c` (days/yr): Mean days/yr with Tmax > 35C, 1991-2020
- `haz_days_gt95f_2050` (days/yr): Projected days/yr with Tmax > 95F, SSP2-4.5 mid-century (LOCA2)
- `haz_free_cooling_pct_hours` (percent 0-100): Share of TMY hours with dry-bulb <= 18C and dew point <= 15C
- `haz_wetbulb_gt26c_hours` (hours/yr): TMY hours with wet-bulb (Stull) > 26C
- `haz_free_cooling_pct_hours_2050` (percent 0-100): Free-cooling share after the 2050 warming delta
- `haz_tavg_delta_2050_c` (deg C): LOCA2 SSP2-4.5 change in annual mean temperature, 2040-2059 vs 2000-2019
- `haz_pct_floodplain_100yr` (percent 0-100): Share of mapped land in the FEMA 1%-annual-chance floodplain
- `haz_nfhl_coverage_pct` (percent 0-100): Share of county area inside the NFHL Availability footprint
- `haz_karst_pct` (percent 0-100): Share of county on karst-prone rock (including buried)
- `haz_karst_exposed_pct` (percent 0-100): Share of county on karst rock at or near the surface

**land_connectivity**

- `lnd_pct_developed` (percent 0-100): NLCD 2024 developed classes 21-24
- `lnd_pct_buildable` (percent 0-100): NLCD 2024 barren, shrub, grassland, pasture (31, 52, 71, 81)
- `lnd_pct_wetland` (percent 0-100): NLCD 2024 wetlands (90, 95)
- `lnd_pct_cropland` (percent 0-100): NLCD 2024 cultivated crops (82)
- `lnd_pct_forest` (percent 0-100): NLCD 2024 forest (41-43)
- `lnd_pct_slope_lt5` (percent 0-100): Share of land (open water excluded) with slope < 5%, 3DEP 30 m
- `lnd_pct_protected` (percent 0-100): PAD-US GAP 1-2 protected area share (overlaps dissolved)
- `lnd_brownfields_n` (count): EPA ACRES brownfield sites
- `lnd_dist_brownfield_km` (km): Distance from pop. centroid to nearest brownfield
- `lnd_dist_brownfield_or_retired_km` (km): Distance to nearest brownfield or retired plant >= 100 MW
- `lnd_dist_interstate_km` (km): Distance from pop. centroid to nearest Interstate
- `lnd_ixp_n` (count): PeeringDB facilities hosting an internet exchange
- `lnd_colo_fac_n` (count): All PeeringDB colocation facilities
- `lnd_dist_ixp_km` (km): Distance from pop. centroid to nearest IX-hosting facility
- `lnd_dist_eaf_steel_km` (km): Distance to nearest operating electric-arc-furnace steel plant
- `lnd_dist_cement_km` (km): Distance to nearest operating cement plant

**permitting_risk**

- `prm_pop_density_km2` (people/km2): meta_pop_2023 / meta_land_area_km2
- `prm_nonattainment` (0/1): 1 if any part of the county is in a current NAAQS nonattainment area
- `prm_pct_tribal` (percent 0-100): Share of county area in reservations, trust land, joint-use areas
- `prm_pct_ok_tribal_stat_area` (percent 0-100): Share of county area in Oklahoma Tribal Statistical Areas
- `prm_nrhp_n` (count): National Register of Historic Places listed properties
- `prm_price_growth_pct` (percent): State average retail price change 2020 -> 2024, all sectors
- `prm_moratorium_active` (0/0.5/1): 1 active county-level moratorium, 0.5 only a city/town/township/tribal one, else 0
- `prm_moratorium_proposed` (0/1): 1 if any moratorium in the county has status=proposed
- `prm_state_moratorium` (0/1): Statewide data center moratorium
- `prm_tax_exemption_status` (category): State data center sales-tax exemption (active/paused/repealed/none)
- `prm_large_load_tariff` (0/1): State has a large-load tariff in effect
- `prm_county_can_zone` (0/1): Counties have zoning authority over data centers
- `meta_state_policy_verified` (0/1): 1 if the state_policy.csv row was researched
- `prm_contested_n` (count): Contested data center projects in the county
- `prm_contested_neighbors_n` (count): Contested projects in Census-adjacent counties

**community_benefit**

- `cob_unemp_rate` (percent): Annual average unemployment rate 2024
- `cob_poverty_pct` (percent 0-100): Population below poverty (B17001)
- `cob_median_hh_income` (USD (2023)): Median household income (B19013)
- `cob_pct_fossil_heat` (percent 0-100): Occupied homes heated with gas, LP, or fuel oil (district heat offtake)
- `cob_persistent_poverty` (0/1): ERS persistent poverty county (>= 20% poverty in 1990, 2000, 2007-11, 2017-21)
- `cob_energy_community` (0/1): IRA energy community (> 50% of area qualifies)
- `cob_energy_community_pct` (percent 0-100): Share of county area that is an IRA energy community
- `cob_ghgrp_combustion_facilities_n` (count): GHGRP Subpart C facilities in low-temp-heat industries
- `cob_ghgrp_combustion_tco2` (t CO2e/yr): Stationary combustion emissions of those facilities
- `cob_lowtemp_ind_heat_tbtu` (TBtu/yr): Process-heating energy, food/beverage/paper (2014)
- `cob_hdd_annual` (degree-days F): Mean annual heating degree days, base 65F, 1991-2020
- `cob_ej_disadvantaged` (percent 0-100): Share of population in CEJST v2.0 disadvantaged tracts
- `cob_qcew_dc_emp` (people): Employment in NAICS 518210 (data processing, hosting), 2025 annual average
- `cob_qcew_dc_emp_suppressed` (0/1): 1 if BLS suppressed the NAICS 518210 county employment

**label**

- `lbl_dc_existing_n` (count): Existing data centers (PNNL IM3 atlas)
- `lbl_frontier_ai_dc_n` (count): Epoch AI frontier AI data center sites
- `lbl_contested_n` (count): Contested data center projects (label copy of prm_contested_n)

## Known approximations

- **Utility-based power features** (`pwr_ind_price_cents_kwh`, `pwr_saidi_min`, `pwr_saifi`, `pwr_iso`,
  `pwr_time_to_power_yrs`): EIA-861 service territories list the counties a utility serves, not shares, so county
  values are sales-weighted or simple means over all serving utilities. `pwr_saidi_min` / `pwr_saifi` are the
  2020-2024 median without major events; `*_with_me_latest` keep the old 2024-with-major-events definition.
  Time-to-power: a serving utility with `basis=not_accepting` sets the county to the CSV max + 2 years; otherwise
  the sales-weighted utility value; otherwise the NATIONAL AVERAGE row (source `national`).
- **`pwr_neg_price_pct_hours`** is BLOCKED: node-level LMPs for all seven ISOs need API credentials (PJM, ERCOT,
  ISO-NE) plus unpublished node coordinates, and the LBNL WEP download is behind a browser challenge. Non-ISO
  counties will stay NaN (never 0) once the source is filled. FCC fiber (`lnd_fiber_pct`) was not started.
- **`pwr_gen_queue_median_yrs`** is the median request-to-operation time of completed *generator* projects in the
  county's ISO (non-ISO counties: LBNL's West or Southeast region by state). It is a grid-congestion proxy, not a
  load-interconnection wait. ISO-NE has no usable dates in the LBNL file and is NaN.
- **`crb_queue_clean_mw`**: multi-county projects are credited to the first listed county; 74 active rows
  (offshore wind, Mexico, or state/FIPS conflicts) could not be placed and are logged in
  `data/raw/lbnl_queue/unmatched_active_clean.csv`.
- **`crb_solar_cf` / `crb_wind_cf`**: unweighted mean over the ReEDS resource classes present in a county;
  Virginia independent cities are mostly NaN because ReEDS folds them into the surrounding counties.
- **Regional values** (`crb_grid_co2_kg_mwh`, `wtr_grid_water_l_kwh`: eGRID subregions; `crb_lrmer_2035_kg_mwh`:
  18 Cambium regions) are area-weighted or table-joined, so many counties share a value.
- **`wtr_total_withdrawal_mgd`**: the USGS NWAA models are HUC12-only and cover public supply, irrigation and
  thermoelectric use only (no industrial, mining, livestock, aquaculture or domestic self-supply). HUC12 values are
  split onto counties by area share.
- **`cob_lowtemp_ind_heat_tbtu`** is a proxy: 2014 process-heating energy for food, beverage and paper (the NREL
  county file has no temperature field); negative net electricity (exports) is floored at 0.
- **`cob_energy_community`** uses NETL's 2024 spatial release; IRS Notice 2025-31 lists are not reflected.
- **`prm_pct_tribal`** excludes Oklahoma Tribal Statistical Areas, which are reported separately in
  `prm_pct_ok_tribal_stat_area`.
- **Point counts** depend on source coverage: OSM substations need a voltage tag, NRHP omits restricted sites,
  Epoch AI sites were geocoded (12 only to city level, 10 of 77 not located).
- **Vintages differ by source** (e.g. GHGRP RY2023, NLCD 2024 Collection 1.1, CMRA on 2019 counties, NRI March
  2023 on old CT counties); see `data/sources.yaml`.
- **NASS greenhouse** (`cob_greenhouse_sqft`) is SKIPPED: USDA Quick Stats key signup is failing; heat-sink demand
  is covered by GHGRP, NREL industrial heat and HDD.
