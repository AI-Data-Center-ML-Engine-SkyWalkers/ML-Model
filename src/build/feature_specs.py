"""Data dictionary: one entry per output column, in output order.

Fields: (description, unit, source key in data/sources.yaml, join_method, higher_is, notes).
higher_is is from the point of view of siting a 300 MW-1 GW sustainable AI data center:
better / worse / context (depends on use) / label (validation only, never a model input) / id.
Pillar comes from the column prefix. Vintage comes from sources.yaml at build time.
"""

PILLARS = {"meta": "metadata", "pwr": "power", "crb": "carbon", "wtr": "water", "haz": "climate_hazard",
           "lnd": "land_connectivity", "prm": "permitting_risk", "cob": "community_benefit", "lbl": "label"}

S = {}  # column -> spec tuple

def _add(col, desc, unit, source, join, higher, notes=""):
    S[col] = (desc, unit, source, join, higher, notes)


# ---------------------------------------------------------------- meta
_add("fips", "5-digit county FIPS (CT = planning regions 09110-09190)", "code", "census_cb_counties", "key", "id")
_add("meta_county_name", "County name", "text", "census_cb_counties", "base layer", "id")
_add("meta_state_abbr", "State postal abbreviation", "text", "census_cb_counties", "base layer", "id")
_add("meta_state_fips", "2-digit state FIPS", "code", "census_cb_counties", "base layer", "id")
_add("meta_land_area_km2", "Land area (ALAND)", "km2", "census_cb_counties", "base layer", "context")
_add("meta_pop_centroid_lat", "Latitude of 2020 Census center of population", "deg", "census_pop_centroids",
     "table join", "id", "CT planning regions computed from block-group centers")
_add("meta_pop_centroid_lon", "Longitude of 2020 Census center of population", "deg", "census_pop_centroids",
     "table join", "id")
_add("meta_pop_2023", "Total population (ACS 2019-2023 5-year B01003)", "people", "census_acs5_2023", "table join",
     "context")

# ---------------------------------------------------------------- power
_add("pwr_gen_capacity_mw", "Operating + standby generator nameplate capacity", "MW", "eia860",
     "points in county (plant lat/lon), sum", "better")
_add("pwr_retired_capacity_mw", "Retired generator nameplate capacity (brownfield grid connections)", "MW", "eia860m",
     "points in county, sum", "better")
_add("pwr_dist_retired_plant_km", "Distance from pop. centroid to nearest retired plant >= 100 MW", "km", "eia860m",
     "nearest distance (EPSG:5070)", "worse", "18 retired plants lack coordinates and are excluded")
_add("pwr_hv230_line_km", "Length of transmission lines >= 230 kV inside the county", "km", "hifld_transmission_lines",
     "line length clipped to county", "better")
_add("pwr_dist_hv230_line_km", "Distance from pop. centroid to nearest >= 230 kV line", "km",
     "hifld_transmission_lines", "nearest distance (EPSG:5070)", "worse")
_add("pwr_hv345_line_km", "Length of transmission lines >= 345 kV inside the county", "km", "hifld_transmission_lines",
     "line length clipped to county", "better")
_add("pwr_dist_hv345_line_km", "Distance from pop. centroid to nearest >= 345 kV line", "km",
     "hifld_transmission_lines", "nearest distance (EPSG:5070)", "worse")
_add("pwr_substations_230kv_n", "OSM substations with max voltage >= 230 kV", "count", "osm_substations",
     "points in county (way/relation centers), count", "better",
     "Substations without a voltage tag are excluded, so this is a lower bound")
_add("pwr_gas_pipeline_km", "Length of interstate + intrastate natural gas pipelines in the county", "km",
     "eia_gas_pipelines", "line length clipped to county", "context", "On-site gas generation option vs. carbon")
_add("pwr_ind_price_cents_kwh", "Industrial electricity price of the county's serving utilities", "cents/kWh",
     "eia861_pudl", "utility service territory -> county, sales-weighted", "worse",
     "APPROXIMATION: territory lists counties served, not shares")
_add("pwr_saidi_min", "SAIDI without major events, 2020-2024 median, mean of serving utilities", "minutes/yr",
     "eia861_pudl", "utility service territory -> county, mean", "worse",
     "IEEE standard; median over the years each utility reported")
_add("pwr_saifi", "SAIFI without major events, 2020-2024 median, mean of serving utilities", "interruptions/yr",
     "eia861_pudl", "utility service territory -> county, mean", "worse",
     "IEEE standard; median over the years each utility reported")
_add("pwr_saidi_min_with_me_latest", "SAIDI incl. major events, 2024 only, mean of serving utilities", "minutes/yr",
     "eia861_pudl", "utility service territory -> county, mean", "worse", "Reference only (previous definition)")
_add("pwr_saifi_with_me_latest", "SAIFI incl. major events, 2024 only, mean of serving utilities",
     "interruptions/yr", "eia861_pudl", "utility service territory -> county, mean", "worse",
     "Reference only (previous definition)")
_add("pwr_iso", "ISO/RTO of the county's main utility (NONE = outside an ISO)", "category", "eia861_pudl",
     "utility service territory -> county", "context")
_add("pwr_main_utility_id", "EIA utility ID of the county's main (largest-sales) utility", "id", "eia861_pudl",
     "utility service territory -> county", "id")
_add("pwr_time_to_power_yrs", "Reported years to energize a large load (utility, else national average)", "years",
     "manual_time_to_power", "manual CSV via utility-county map", "worse",
     "Utilities not accepting new data center load = CSV max + 2 yrs; see pwr_time_to_power_source")
_add("pwr_time_to_power_source", "Basis of pwr_time_to_power_yrs (utility / not_accepting / national / none)",
     "category", "manual_time_to_power", "derived", "context")
_add("pwr_gen_queue_median_yrs", "Median years from interconnection request to COD for completed generators, by region",
     "years", "lbnl_queue", "region via pwr_iso (non-ISO -> LBNL West/Southeast by state)", "worse",
     "PROXY for grid congestion from generator queues, NOT a load interconnection wait time. ISO-NE has no data")

# ---------------------------------------------------------------- carbon
_add("crb_grid_co2_kg_mwh", "eGRID subregion annual CO2 total output emission rate", "kg CO2/MWh", "epa_egrid2023",
     "area-weighted polygon overlay", "worse")
_add("crb_lrmer_2035_kg_mwh", "Long-run marginal CO2e emission rate, Mid-case 2035", "kg CO2e/MWh", "nrel_cambium_2024",
     "GEA region table join (County Mapping tab)", "worse", "18 regions only")
_add("crb_cambium_gea", "Cambium generation-and-emission assessment region", "category", "nrel_cambium_2024",
     "table join", "context")
_add("crb_clean_gen_mw", "Operating nuclear, hydro, wind, solar, geothermal capacity", "MW", "eia860",
     "points in county, sum", "better")
_add("crb_queue_clean_mw", "Active interconnection-queue MW of solar, wind, storage, nuclear, geothermal", "MW",
     "lbnl_queue", "LBNL county FIPS (name match fallback), sum", "better", "Multi-county projects credited to first county")
_add("crb_solar_cf", "Utility-scale PV mean capacity factor (reference siting)", "fraction 0-1", "nrel_reeds_county_cf",
     "table join (unweighted mean over resource classes)", "better", "VA independent cities mostly NaN")
_add("crb_wind_cf", "Onshore wind mean capacity factor (reference siting)", "fraction 0-1", "nrel_reeds_county_cf",
     "table join (unweighted mean over resource classes)", "better", "VA independent cities mostly NaN")

# ---------------------------------------------------------------- water
_add("wtr_bws_score", "Aqueduct 4.0 baseline water stress score", "score 0-5", "wri_aqueduct40",
     "area-weighted polygon overlay", "worse")
_add("wtr_bws_2050_score", "Aqueduct 4.0 water stress 2050, business-as-usual (SSP3-7.0)", "score 0-5",
     "wri_aqueduct40", "area-weighted polygon overlay", "worse")
_add("wtr_drought_d2plus_pct_weeks", "Share of weeks 2000-2025 with any D2-D4 drought", "percent 0-100",
     "usdm_drought", "table join", "worse")
_add("wtr_grid_water_l_kwh", "Indirect water: power-sector cooling water consumed per kWh, eGRID subregion",
     "L/kWh", "eia923_cooling_water", "area-weighted polygon overlay", "worse")
_add("wtr_total_withdrawal_mgd", "2020 withdrawals: public supply + irrigation + thermoelectric", "Mgal/d",
     "usgs_water_use", "HUC12 values split by area share", "worse",
     "NWAA models omit industrial, mining, livestock, aquaculture, domestic self-supply")
_add("wtr_ps_withdrawal_mgd", "2020 public-supply withdrawals", "Mgal/d", "usgs_water_use",
     "HUC12 values split by area share", "context")
_add("wtr_irr_withdrawal_mgd", "2020 crop irrigation withdrawals", "Mgal/d", "usgs_water_use",
     "HUC12 values split by area share", "context")
_add("wtr_te_withdrawal_mgd", "2020 thermoelectric withdrawals (fresh + saline)", "Mgal/d", "usgs_water_use",
     "HUC12 values split by area share", "context")
_add("wtr_wwtp_flow_mgd", "Design flow of wastewater treatment plants (reclaimed-water potential)", "Mgal/d",
     "epa_cwns", "facility county field (else point-in-polygon), sum", "better")

# ---------------------------------------------------------------- climate & hazards
_add("haz_nri_risk_score", "FEMA National Risk Index composite risk score", "score 0-100", "fema_nri", "table join",
     "worse")
for h, lab in [("riverine_flood", "riverine flooding"), ("coastal_flood", "coastal flooding"),
               ("hurricane", "hurricane"), ("wildfire", "wildfire"), ("tornado", "tornado"),
               ("earthquake", "earthquake"), ("heatwave", "heat wave"), ("drought", "drought")]:
    _add(f"haz_eal_{h}", f"NRI expected annual loss score: {lab}", "score 0-100", "fema_nri", "table join", "worse",
         "'Not Applicable' set to 0 (NRI's no-loss score); 'Insufficient Data' NaN")
for h, lab in [("coastal_flood", "coastal flooding"), ("drought", "drought"),
               ("heatwave", "extreme heat (LOCA 95th pct)"), ("hurricane", "hurricane"), ("wildfire", "wildfire")]:
    _add(f"haz_eal_{h}_future", f"NRI Future Risk projected risk index score, mid-century lower warming: {lab}",
         "score 0-100", "fema_nri_future_risk", "table join", "worse",
         "Projected RISK score (no projected EAL score exists); 'Not Applicable' -> 0")
_add("haz_wildfire_risk_to_homes", "Wildfire Risk to Communities: national percentile of risk to homes",
     "percentile 0-100", "wildfire_risk", "table join", "worse")
_add("haz_cdd_annual", "Mean annual cooling degree days, base 65F, 1991-2020", "degree-days F", "noaa_nclimgrid_daily",
     "table join", "worse")
_add("haz_days_tmax_gt35c", "Mean days/yr with Tmax > 35C, 1991-2020", "days/yr", "noaa_nclimgrid_daily",
     "table join", "worse")
_add("haz_days_gt95f_2050", "Projected days/yr with Tmax > 95F, SSP2-4.5 mid-century (LOCA2)", "days/yr", "cmra_2025",
     "table join (2019 counties)", "worse")
_add("haz_karst_pct", "Share of county on karst-prone carbonate/evaporite/sandstone rock (incl. buried)",
     "percent 0-100", "usgs_karst", "polygon coverage", "worse", "Pseudokarst (volcanic, piping) excluded")
_add("haz_karst_exposed_pct", "Share of county on karst rock at or near the surface", "percent 0-100", "usgs_karst",
     "polygon coverage", "worse")

# ---------------------------------------------------------------- land & connectivity
_add("lnd_pct_developed", "NLCD 2024 developed classes 21-24", "percent 0-100", "usgs_annual_nlcd",
     "raster zonal fraction (exactextract)", "context")
_add("lnd_pct_buildable", "NLCD 2024 barren, shrub, grassland, pasture (31, 52, 71, 81)", "percent 0-100",
     "usgs_annual_nlcd", "raster zonal fraction (exactextract)", "better")
_add("lnd_pct_wetland", "NLCD 2024 wetlands (90, 95)", "percent 0-100", "usgs_annual_nlcd",
     "raster zonal fraction (exactextract)", "worse")
_add("lnd_pct_cropland", "NLCD 2024 cultivated crops (82)", "percent 0-100", "usgs_annual_nlcd",
     "raster zonal fraction (exactextract)", "context")
_add("lnd_pct_forest", "NLCD 2024 forest (41-43)", "percent 0-100", "usgs_annual_nlcd",
     "raster zonal fraction (exactextract)", "worse")
_add("lnd_pct_protected", "PAD-US GAP 1-2 protected area share (overlaps dissolved)", "percent 0-100", "usgs_padus",
     "polygon coverage", "worse")
_add("lnd_brownfields_n", "EPA ACRES brownfield sites", "count", "epa_acres_brownfields", "points in county, count",
     "better")
_add("lnd_dist_brownfield_km", "Distance from pop. centroid to nearest brownfield", "km", "epa_acres_brownfields",
     "nearest distance (EPSG:5070)", "worse")
_add("lnd_dist_brownfield_or_retired_km", "Distance to nearest brownfield or retired plant >= 100 MW", "km",
     "epa_acres_brownfields", "nearest distance (EPSG:5070)", "worse")
_add("lnd_dist_interstate_km", "Distance from pop. centroid to nearest Interstate", "km", "bts_interstates",
     "nearest distance (EPSG:5070)", "worse")
_add("lnd_ixp_n", "PeeringDB facilities hosting an internet exchange", "count", "peeringdb", "points in county, count",
     "better")
_add("lnd_colo_fac_n", "All PeeringDB colocation facilities", "count", "peeringdb", "points in county, count",
     "better")
_add("lnd_dist_ixp_km", "Distance from pop. centroid to nearest IX-hosting facility", "km", "peeringdb",
     "nearest distance (EPSG:5070)", "worse")
_add("lnd_dist_eaf_steel_km", "Distance to nearest operating electric-arc-furnace steel plant", "km",
     "gem_heavy_industry", "nearest distance (EPSG:5070)", "context", "Low-carbon steel supply / heat offtake")
_add("lnd_dist_cement_km", "Distance to nearest operating cement plant", "km", "gem_heavy_industry",
     "nearest distance (EPSG:5070)", "context")

# ---------------------------------------------------------------- permitting risk
_add("prm_pop_density_km2", "meta_pop_2023 / meta_land_area_km2", "people/km2", "census_acs5_2023", "computed",
     "context")
_add("prm_nonattainment", "1 if any part of the county is in a current NAAQS nonattainment area", "0/1",
     "epa_greenbook", "table join", "worse")
_add("prm_pct_tribal", "Share of county area in reservations, trust land, joint-use areas", "percent 0-100",
     "census_aiannh", "polygon coverage", "context", "Oklahoma Tribal Statistical Areas excluded (see next column)")
_add("prm_pct_ok_tribal_stat_area", "Share of county area in Oklahoma Tribal Statistical Areas", "percent 0-100",
     "census_aiannh", "polygon coverage", "context", "Ambiguous legal status post-McGirt; kept separate")
_add("prm_nrhp_n", "National Register of Historic Places listed properties", "count", "nps_nrhp",
     "points in county, count", "worse", "Restricted sites withheld by NPS: lower bound")
_add("prm_price_growth_pct", "State average retail price change 2020 -> 2024, all sectors", "percent",
     "eia861_pudl", "state table join", "worse")
_add("prm_moratorium_active", "1 active county-level moratorium, 0.5 only a city/town/township/tribal one, else 0",
     "0/0.5/1", "manual_csvs", "manual CSV", "worse", "status=active rows only")
_add("prm_moratorium_proposed", "1 if any moratorium in the county has status=proposed", "0/1", "manual_csvs",
     "manual CSV", "worse")
_add("prm_state_moratorium", "Statewide data center moratorium", "0/1", "manual_csvs", "manual CSV by state", "worse")
_add("meta_state_policy_verified", "1 if the state_policy.csv row was researched (0 = template defaults)", "0/1",
     "manual_csvs", "manual CSV by state", "context",
     "Unverified rows carry default moratorium 0, tariff 0, county zoning 1, tax status unknown")
_add("prm_tax_exemption_status", "State data center sales-tax exemption (active/paused/repealed/none)", "category",
     "manual_csvs", "manual CSV by state", "context")
_add("prm_large_load_tariff", "State has a large-load tariff in effect", "0/1", "manual_csvs", "manual CSV by state",
     "context")
_add("prm_county_can_zone", "Counties have zoning authority over data centers", "0/1", "manual_csvs",
     "manual CSV by state", "context")
_add("prm_contested_n", "Contested data center projects in the county", "count", "manual_csvs", "manual CSV", "worse")
_add("prm_contested_neighbors_n", "Contested projects in Census-adjacent counties", "count", "manual_csvs",
     "manual CSV + county adjacency", "worse")

# ---------------------------------------------------------------- community benefit
_add("cob_unemp_rate", "Annual average unemployment rate 2024", "percent", "bls_laus", "table join", "better",
     "Higher = more benefit from jobs")
_add("cob_poverty_pct", "Population below poverty (B17001)", "percent 0-100", "census_acs5_2023", "table join", "better")
_add("cob_median_hh_income", "Median household income (B19013)", "USD (2023)", "census_acs5_2023", "table join",
     "context")
_add("cob_pct_fossil_heat", "Occupied homes heated with gas, LP, or fuel oil (district heat offtake)",
     "percent 0-100", "census_acs5_2023", "table join", "better")
_add("cob_persistent_poverty", "ERS persistent poverty county (>= 20% poverty in 1990, 2000, 2007-11, 2017-21)", "0/1",
     "ers_typology", "table join", "better", "ERS codes -1/99 -> NaN; CT from old counties")
_add("cob_energy_community", "IRA energy community (> 50% of area qualifies)", "0/1", "netl_energy_community",
     "polygon coverage > 50%", "better", "2024 NETL release; IRS Notice 2025-31 not reflected")
_add("cob_energy_community_pct", "Share of county area that is an IRA energy community", "percent 0-100",
     "netl_energy_community", "polygon coverage", "better")
_add("cob_ghgrp_combustion_facilities_n", "GHGRP Subpart C facilities in low-temp-heat industries", "count",
     "epa_ghgrp", "points in county, count", "better", "NAICS 311, 312, 322, 325, 1114; RY2023")
_add("cob_ghgrp_combustion_tco2", "Stationary combustion emissions of those facilities", "t CO2e/yr", "epa_ghgrp",
     "points in county, sum", "better")
_add("cob_lowtemp_ind_heat_tbtu", "Process-heating energy, food/beverage/paper (2014)", "TBtu/yr",
     "nrel_county_industrial_energy", "table join", "better", "PROXY for low-temperature heat demand")
_add("cob_hdd_annual", "Mean annual heating degree days, base 65F, 1991-2020", "degree-days F",
     "noaa_nclimgrid_daily", "table join", "better", "Waste-heat reuse potential")
_add("cob_ej_disadvantaged", "Share of population in CEJST v2.0 disadvantaged tracts", "percent 0-100", "cejst_v2",
     "tract population sum (2010 tracts)", "better", "Justice40-style benefit targeting; 46102 NaN (no population)")
_add("cob_qcew_dc_emp", "Employment in NAICS 518210 (data processing, hosting), 2025 annual average", "people",
     "bls_qcew", "table join", "better", "NaN where BLS suppressed; see flag. 0 = no establishments")
_add("cob_qcew_dc_emp_suppressed", "1 if BLS suppressed the NAICS 518210 county employment", "0/1", "bls_qcew",
     "table join", "context")

# ---------------------------------------------------------------- labels
_add("lbl_dc_existing_n", "Existing data centers (PNNL IM3 atlas)", "count", "pnnl_im3_datacenter_atlas",
     "points in county, count", "label")
_add("lbl_frontier_ai_dc_n", "Epoch AI frontier AI data center sites", "count", "epoch_ai_frontier_dc",
     "geocoded points in county, count", "label", "10 of 77 US sites could not be located")
_add("lbl_contested_n", "Contested data center projects (label copy of prm_contested_n)", "count", "manual_csvs",
     "manual CSV", "label")
