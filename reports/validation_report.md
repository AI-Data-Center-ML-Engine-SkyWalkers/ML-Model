# Validation report

- Rows: **3109** (expected 3,109 = CONUS + DC, CT planning regions) - OK
- `fips`: unique = True, all 5-digit strings = True, dtype = str
- Columns: 110; choropleth maps written: 99 (reports/maps/)

## Source status

| Source | Status | Message |
|---|---|---|
| `eia860m` | PARTIAL | 2640 retired plants located (513 >= 100 MW); 18 plants (6,973 MW) without coordinates excluded. |
| `epoch_ai_frontier_dc` | PARTIAL | 67/77 US sites geocoded; 10 without a usable address. |
| `manual_time_to_power` | PARTIAL | Manual CSV data/manual/utility_time_to_power.csv: counties by source {'national': 2969, 'utility': 126, 'not_accepting': 14}; not_accepting = 9 yrs (CSV max + 2); national fallback = 4 yrs. |
| `fema_nfhl` | SKIPPED | time constraint; covered by haz_cdd_annual, haz_days_gt95f_2050, NRI flood scores and lnd_pct_buildable |
| `free_cooling_2050` | SKIPPED | time constraint; covered by haz_cdd_annual, haz_days_gt95f_2050, NRI flood scores and lnd_pct_buildable |
| `lmp_negative_prices` | SKIPPED | time constraint; needs ISO API credentials or a manual LBNL WEP download. |
| `nass_greenhouse` | SKIPPED | USDA Quick Stats key signup failing; heat-sink demand covered by GHGRP, NREL industrial heat and HDD. |
| `nsrdb_free_cooling` | SKIPPED | time constraint; covered by haz_cdd_annual, haz_days_gt95f_2050, NRI flood scores and lnd_pct_buildable |
| `usgs_3dep_slope` | SKIPPED | time constraint; covered by haz_cdd_annual, haz_days_gt95f_2050, NRI flood scores and lnd_pct_buildable |
| `bls_laus` | OK | 3109 counties, 2024 annual average. |
| `bls_qcew` | OK | 2025: 562 counties with disclosed employment > 0, 1274 suppressed (NaN + flag), 1273 with no establishments (0). |
| `bts_interstates` | OK | 100009 interstate segments (BTS NTAD via USDOT_BTS ArcGIS Online). |
| `cejst_v2` | OK | 3108 counties; 1318 with > 50% of population disadvantaged. |
| `census_acs5_2023` | OK | 3109 counties via ACS table-based Summary File (bulk download). |
| `census_aiannh` | OK | 475 counties with some tribal land. |
| `census_cb_counties` | OK | 3109 counties (CONUS+DC). |
| `census_pop_centroids` | OK | 2020 centers of population; CT derived from block groups; 0 missing. |
| `cmra_2025` | OK | 3109 counties. |
| `eia860` | OK | 14119 plants joined; CONUS operating capacity 1,350,630 MW. |
| `eia861_pudl` | OK | non-null counts: {'fips': 3109, 'pwr_ind_price_cents_kwh': 3072, 'pwr_saidi_min': 2879, 'pwr_saifi': 2854, 'pwr_saidi_min_with_me_latest': 2850, 'pwr_saifi_with_me_latest': 2825, 'pwr_iso': 3091, 'pwr_main_utility_id': 3 |
| `eia923_cooling_water` | OK | 26 subregions; 3109 counties. |
| `eia_gas_pipelines` | OK | 32892 pipeline segments; 344,079 km in CONUS. |
| `epa_acres_brownfields` | OK | 41692 brownfield sites located. |
| `epa_cwns` | OK | 15979 treatment plants located. |
| `epa_egrid2023` | OK | 3109 counties. |
| `epa_ghgrp` | OK | RY2023: 1186 Subpart C facilities in NAICS ('311', '312', '322', '325', '1114'). |
| `epa_greenbook` | OK | 237 counties in nonattainment (pw_2026). |
| `ers_typology` | OK | 3095 counties with a 0/1 value; 14 NaN (ERS codes -1). |
| `fema_nri` | OK | 3109 counties; NRI version ['March 2023']. |
| `fema_nri_future_risk` | OK | 3109 counties; non-null {'haz_eal_coastal_flood_future': 3109, 'haz_eal_drought_future': 3109, 'haz_eal_heatwave_future': 3109, 'haz_eal_hurricane_future': 3109, 'haz_eal_wildfire_future': 3109} |
| `gem_heavy_industry` | OK | 61 operating EAF plants, 96 operating cement plants. |
| `hifld_transmission_lines` | OK | 10675 lines >= 230 kV, 3457 >= 345 kV; 14248 unknown-voltage lines excluded. |
| `lbnl_queue` | OK | 7562 active clean requests (1,560 GW); 74 unmatched rows logged. Region medians: {'CAISO': 6.02, 'ERCOT': 3.7, 'MISO': 3.04, 'NYISO': 4.61, 'PJM': 3.15, 'SPP': 4.06, 'Southeast': 3.79, 'West': 2.05} |
| `manual_contested` | OK | 60 contested projects in 51 counties. Unknown fips ignored: [] |
| `manual_moratoria` | OK | 31 rows (18 active, 6 proposed); active: 6 counties = 1, 12 = 0.5; proposed: 6 counties. Unknown fips ignored: []. Unrecognised active jurisdiction types ignored: [] |
| `manual_state_policy` | OK | 49 states filled (14 verified, the rest template defaults); 3109 counties covered, rest NaN. |
| `netl_energy_community` | OK | 1066 counties > 50% energy community (2024 layers). |
| `noaa_nclimgrid_daily` | OK | 3108 counties, 1991-2020. |
| `nps_nrhp` | OK | 94337 listed NRHP properties located. |
| `nrel_cambium_2024` | OK | 18 GEA regions mapped to 3109 counties. |
| `nrel_county_industrial_energy` | OK | 2580 counties with food/beverage/paper process heat (proxy). |
| `nrel_reeds_county_cf` | OK | solar CF for 3080 counties, wind CF for 2981. |
| `osm_substations` | OK | 6857 substations >= 230 kV; failed states: none. |
| `peeringdb` | OK | 478 IX-hosting US facilities, 1354 facilities total. |
| `pnnl_im3_datacenter_atlas` | OK | 1223 data center features counted. |
| `usdm_drought` | OK | 3109 counties, 1357 weeks. |
| `usgs_annual_nlcd` | OK | Land cover class shares for all counties. |
| `usgs_karst` | OK | 2154 counties with any karst; 1692 with exposed karst. |
| `usgs_padus` | OK | 120670 GAP 1-2 features overlaid. |
| `usgs_water_use` | OK | 83322 HUC12s area-weighted onto counties (2020). |
| `wildfire_risk` | OK | 3109 counties. |
| `wri_aqueduct40` | OK | baseline non-null 3109, 2050 non-null 3109 |

## Columns with > 20% missing

| Column | Missing | Source |
|---|---|---|
| `cob_qcew_dc_emp` | 41.0% | bls_qcew |

## Range checks

Rules: percent/percentile/score-100 columns in [0, 100]; CO2 rates in [0, 1200]; Aqueduct scores in [0, 5]; fractions and flags in [0, 1]; distances, counts, MW, flows, etc. >= 0.

All range checks passed.

## Spot checks

| column | Loudoun VA (51107) | Maricopa AZ (04013) | Cook IL (17031) | Harris TX (48201) | King WA (53033) | Douglas GA (13097) | Richland LA (22083) | Taylor TX (48441) | Laramie WY (56021) | Polk IA (19153) |
|---|---|---|---|---|---|---|---|---|---|---|
| `meta_land_area_km2` | 1,336 | 23,833 | 2,447 | 4,421 | 5,480 | 518 | 1,439 | 2,371 | 6,956 | 1,483 |
| `meta_pop_centroid_lat` | 39 | 33.5 | 41.9 | 29.8 | 47.6 | 33.7 | 32.4 | 32.4 | 41.2 | 41.6 |
| `meta_pop_centroid_lon` | -77.5 | -112 | -87.8 | -95.4 | -122 | -84.7 | -91.7 | -99.8 | -105 | -93.6 |
| `meta_pop_2023` | 427,082 | 4,491,987 | 5,185,812 | 4,758,579 | 2,262,713 | 146,141 | 19,908 | 144,259 | 100,661 | 497,441 |
| `pwr_gen_capacity_mw` | 812 | 21,536 | 1,281 | 10,212 | 160 | 3 | 0 | 1,444 | 746 | 1,066 |
| `pwr_retired_capacity_mw` | 0 | 362 | 2,162 | 3,529 | 20.4 | 0 | 0 | 15 | 0 | 5.3 |
| `pwr_dist_retired_plant_km` | 20.2 | 11.9 | 5.43 | 17.2 | 52.3 | 25.7 | 43.8 | 20 | 83.7 | 79.5 |
| `pwr_hv230_line_km` | 228 | 3,021 | 529 | 588 | 1,260 | 153 | 25.9 | 194 | 522 | 76.4 |
| `pwr_dist_hv230_line_km` | 2.11 | 1.76 | 5.01 | 0.791 | 4.19 | 2.86 | 13.3 | 11.8 | 5.04 | 4.53 |
| `pwr_hv345_line_km` | 59 | 1,253 | 529 | 588 | 599 | 70.1 | 25.9 | 194 | 154 | 76.4 |
| `pwr_dist_hv345_line_km` | 2.14 | 18 | 5.01 | 0.791 | 9.5 | 2.86 | 13.3 | 11.8 | 10.3 | 4.53 |
| `pwr_substations_230kv_n` | 75 | 80 | 84 | 17 | 13 | 12 | 0 | 3 | 5 | 5 |
| `pwr_gas_pipeline_km` | 118 | 493 | 404 | 1,672 | 75.8 | 40.3 | 398 | 297 | 196 | 121 |
| `pwr_ind_price_cents_kwh` | 7.82 | 8.37 | 9.81 | 6.09 | 8.29 | 7.13 | 5.17 | 6.06 | 9.67 | 6.62 |
| `pwr_saidi_min` | 51.3 | 77.9 | 37.6 | 189 | 117 | 117 | 213 | 199 | 33.4 | 88.3 |
| `pwr_saifi` | 0.672 | 1.17 | 0.52 | 1.6 | 0.768 | 1.3 | 1.55 | 1.9 | 0.511 | 0.91 |
| `pwr_saidi_min_with_me_latest` | 94.6 | 119 | 132 | 2,427 | 466 | 815 | 610 | 240 | 33.4 | 356 |
| `pwr_saifi_with_me_latest` | 0.859 | 1.95 | 0.68 | 3.39 | 1.3 | 1.78 | 2.04 | 2.24 | 0.495 | 1.41 |
| `pwr_iso` | PJM | NONE | PJM | ERCOT | NONE | NONE | MISO | ERCOT | NONE | MISO |
| `pwr_main_utility_id` | 19,876 | 803 | 4,110 | 8,901 | 15,500 | 7,140 | 11,241 | 20,404 | 3,461 | 12,341 |
| `pwr_time_to_power_yrs` | 7 | 9 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| `pwr_time_to_power_source` | utility | not_accepting | national | national | national | national | national | national | national | national |
| `pwr_gen_queue_median_yrs` | 3.15 | 2.05 | 3.15 | 3.7 | 2.05 | 3.79 | 3.04 | 3.7 | 2.05 | 3.04 |
| `crb_grid_co2_kg_mwh` | 269 | 319 | 413 | 334 | 287 | 382 | 336 | 333 | 470 | 417 |
| `crb_lrmer_2035_kg_mwh` | 262 | 125 | 203 | 69.9 | 24.9 | 143 | 163 | 69.9 | 84.8 | 142 |
| `crb_cambium_gea` | PJM_East | WestConnect_South | PJM_West | ERCOT | NorthernGrid_West | SERTP | MISO_South | ERCOT | WestConnect_North | MISO_North |
| `crb_clean_gen_mw` | 0 | 7,339 | 41.7 | 69.1 | 142 | 3 | 0 | 1,442 | 606 | 0 |
| `crb_queue_clean_mw` | 715 | 23,067 | 435 | 7,108 | 480 | 0 | 750 | 2,451 | 3,172 | 340 |
| `crb_solar_cf` | 0.179 | 0.255 | 0.177 | 0.204 | 0.137 | 0.193 | 0.203 | 0.233 | 0.205 | 0.184 |
| `crb_wind_cf` | 0.341 | 0.218 | NaN | 0.33 | 0.248 | 0.27 | 0.326 | 0.453 | 0.423 | 0.416 |
| `wtr_bws_score` | 0.306 | 4.68 | 3.51 | 2.52 | 0.863 | 2.41 | 2.8 | 2.77 | 4.92 | 0.758 |
| `wtr_bws_2050_score` | 0.599 | 4.34 | 3.77 | 2.99 | 0.987 | 2.24 | 2.81 | 3.68 | 4.92 | 1.01 |
| `wtr_drought_d2plus_pct_weeks` | 7.89 | 51.9 | 6.63 | 18.9 | 10.2 | 22.5 | 15.3 | 30.5 | 32 | 14.4 |
| `wtr_grid_water_l_kwh` | 0.528 | 1.03 | 1.15 | 0.767 | 0.57 | 1.35 | 1.14 | 0.616 | 0.561 | 0.61 |
| `wtr_total_withdrawal_mgd` | 57.9 | 1,538 | 654 | 707 | 185 | 15.5 | 99.7 | 27.9 | 89.7 | 54.4 |
| `wtr_ps_withdrawal_mgd` | 44.9 | 622 | 628 | 565 | 184 | 15.5 | 0.999 | 20.9 | 13.1 | 54.4 |
| `wtr_irr_withdrawal_mgd` | 0.0987 | 884 | 0 | 11.3 | 1.36 | 0 | 98.7 | 6.99 | 76.5 | 0.00563 |
| `wtr_te_withdrawal_mgd` | 12.9 | 32 | 25.6 | 130 | 0 | 0 | 0 | 0 | 0 | 0 |
| `wtr_wwtp_flow_mgd` | 35.4 | 562 | 2,016 | 868 | 382 | 10.2 | 1.59 | 19.4 | 17.2 | 138 |
| `haz_nri_risk_score` | 78.2 | 97.3 | 99.6 | 100 | 99.7 | 75.1 | 67.6 | 84.1 | 80.6 | 91.5 |
| `haz_eal_riverine_flood` | 15.1 | 94.6 | 99 | 100 | 72.1 | 70.4 | 92.1 | 89 | 82.1 | 85.7 |
| `haz_eal_coastal_flood` | 0 | 0 | 44.4 | 73.3 | 74.4 | 0 | 0 | 0 | 0 | 0 |
| `haz_eal_hurricane` | 85.7 | 45.1 | 60.8 | 100 | 0 | 62.6 | 60.1 | 47 | 0 | 27.9 |
| `haz_eal_wildfire` | 63.2 | 99.7 | 60.8 | 87.9 | 73.6 | 47.5 | 17.6 | 95.4 | 84.1 | 64 |
| `haz_eal_tornado` | 85.5 | 86.7 | 99.9 | 100 | 80.3 | 90.1 | 62.4 | 77.2 | 90.3 | 98.5 |
| `haz_eal_earthquake` | 70.3 | 98.4 | 96.4 | 88.2 | 99.8 | 79.5 | 60.5 | 39.8 | 54.6 | 67.2 |
| `haz_eal_heatwave` | 84.2 | 99.8 | 100 | 99.4 | 82.3 | 0 | 83.4 | 91.3 | 0 | 64.1 |
| `haz_eal_drought` | 75 | 84.4 | 22 | 86 | 21.8 | 0 | 70.5 | 62.6 | 43.3 | 90.5 |
| `haz_eal_coastal_flood_future` | 0 | 0 | 39.6 | 69.8 | 73.4 | 0 | 0 | 0 | 0 | 0 |
| `haz_eal_drought_future` | 66 | 91.8 | 21.2 | 86.9 | 18.9 | 7.4 | 66.2 | 72.3 | 48.5 | 84.6 |
| `haz_eal_heatwave_future` | 74.5 | 99.8 | 99.9 | 99.7 | 76.4 | 8.59 | 91.4 | 94.7 | 8.59 | 58.6 |
| `haz_eal_hurricane_future` | 86 | 40.1 | 54.9 | 100 | 0 | 64.1 | 63.5 | 49.9 | 0 | 22.2 |
| `haz_eal_wildfire_future` | 58.9 | 99.7 | 62.9 | 88.9 | 71.3 | 46 | 19.1 | 95.1 | 81.5 | 64.3 |
| `haz_wildfire_risk_to_homes` | 27.2 | 78.7 | 27.5 | 58.2 | 64.6 | 62.1 | 31.7 | 83.6 | 79.4 | 28 |
| `haz_cdd_annual` | 1,077 | 3,651 | 844 | 3,055 | 89.1 | 1,617 | 2,402 | 2,311 | 326 | 925 |
| `haz_days_tmax_gt35c` | 3.47 | 127 | 1.1 | 28.9 | 0 | 4.3 | 25.7 | 46.1 | 1.67 | 2.67 |
| `haz_days_gt95f_2050` | 20.5 | 154 | 14.6 | 71.3 | 1.07 | 25.6 | 74.5 | 85.1 | 13.6 | 23.8 |
| `haz_karst_pct` | 6.51 | 0.287 | 94.4 | 0 | 0.105 | 0 | 0 | 67.3 | 1.03 | 3.67 |
| `haz_karst_exposed_pct` | 6.51 | 0.287 | 0.361 | 0 | 0.105 | 0 | 0 | 67.3 | 1.03 | 0 |
| `lnd_pct_developed` | 27.7 | 14.2 | 85.2 | 73.1 | 25.3 | 38.3 | 6.62 | 11.1 | 4.14 | 35.7 |
| `lnd_pct_buildable` | 37.7 | 80.7 | 2.13 | 11.7 | 9.48 | 9.07 | 4.41 | 53.2 | 80.2 | 11 |
| `lnd_pct_wetland` | 1.49 | 0.977 | 4.37 | 7.04 | 2.28 | 1.76 | 24.4 | 0.147 | 1.45 | 4.28 |
| `lnd_pct_cropland` | 2.79 | 3.75 | 1.71 | 0.533 | 0.0613 | 0.00156 | 62.2 | 19 | 13.4 | 40 |
| `lnd_pct_forest` | 29.8 | 0.121 | 5.11 | 4.54 | 59.7 | 49.6 | 0.89 | 16.2 | 0.695 | 6.11 |
| `lnd_pct_protected` | 0.508 | 13.9 | 4.41 | 1.21 | 27.4 | 3.22 | 4.03 | 0 | 2.21 | 4.22 |
| `lnd_brownfields_n` | 1 | 232 | 636 | 132 | 180 | 0 | 0 | 2 | 56 | 20 |
| `lnd_dist_brownfield_km` | 9.94 | 3.16 | 1.17 | 3.38 | 2.98 | 21 | 29.8 | 4.18 | 2.36 | 3.09 |
| `lnd_dist_brownfield_or_retired_km` | 9.94 | 3.16 | 1.17 | 3.38 | 2.98 | 21 | 29.8 | 4.18 | 2.36 | 3.09 |
| `lnd_dist_interstate_km` | 22.3 | 3.16 | 0.237 | 0.461 | 2.68 | 0.903 | 1.79 | 6.87 | 3.37 | 2.08 |
| `lnd_ixp_n` | 27 | 14 | 16 | 10 | 12 | 2 | 0 | 0 | 0 | 2 |
| `lnd_colo_fac_n` | 42 | 26 | 50 | 19 | 30 | 4 | 0 | 0 | 4 | 7 |
| `lnd_dist_ixp_km` | 3.71 | 4.98 | 8.01 | 9.13 | 7.89 | 14.2 | 229 | 242 | 155 | 4.88 |
| `lnd_dist_eaf_steel_km` | 179 | 48 | 21.3 | 134 | 10.6 | 58 | 313 | 256 | 328 | 234 |
| `lnd_dist_cement_km` | 59.7 | 144 | 28.1 | 23.6 | 8.68 | 26.9 | 287 | 67.4 | 70.4 | 177 |
| `prm_pop_density_km2` | 320 | 188 | 2,119 | 1,076 | 413 | 282 | 13.8 | 60.8 | 14.5 | 335 |
| `prm_nonattainment` | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| `prm_pct_tribal` | 0 | 4.59 | 0 | 0 | 0.286 | 0 | 0 | 0 | 0 | 0 |
| `prm_pct_ok_tribal_stat_area` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `prm_nrhp_n` | 98 | 432 | 609 | 300 | 319 | 7 | 9 | 61 | 59 | 202 |
| `prm_price_growth_pct` | 16.2 | 22.5 | 28 | 16.7 | 21.9 | 15.2 | 17.3 | 16.7 | 11.1 | 4.17 |
| `prm_moratorium_active` | 0 | 0 | 0 | 0 | 0.5 | 0 | 0 | 0 | 0 | 0 |
| `prm_moratorium_proposed` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `prm_state_moratorium` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `meta_state_policy_verified` | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 0 |
| `prm_tax_exemption_status` | active | paused | paused | unknown | unknown | active | unknown | unknown | unknown | unknown |
| `prm_large_load_tariff` | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 0 |
| `prm_county_can_zone` | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 1 |
| `prm_contested_n` | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `prm_contested_neighbors_n` | 4 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `cob_unemp_rate` | 2.5 | 3.2 | 5.3 | 4.5 | 4.2 | 3.7 | 5.4 | 3.4 | 3.3 | 3.2 |
| `cob_poverty_pct` | 3.96 | 11.3 | 13.3 | 15.9 | 8.38 | 11.3 | 23.5 | 13.5 | 9.88 | 10.1 |
| `cob_median_hh_income` | 178,707 | 85,518 | 81,797 | 73,104 | 122,148 | 80,764 | 52,960 | 66,406 | 77,884 | 81,621 |
| `cob_pct_fossil_heat` | 67.4 | 28.9 | 82.3 | 43.2 | 44.8 | 58.2 | 27.7 | 42.9 | 76 | 67.1 |
| `cob_persistent_poverty` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `cob_energy_community` | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| `cob_energy_community_pct` | 14 | 0.00408 | 100 | 100 | 8.42 | 0.00308 | 100 | 0.00679 | 0.00368 | 0 |
| `cob_ghgrp_combustion_facilities_n` | 0 | 1 | 4 | 44 | 0 | 0 | 0 | 0 | 2 | 1 |
| `cob_ghgrp_combustion_tco2` | 0 | 41,284 | 641,854 | 13,059,502 | 0 | 0 | 0 | 0 | 274,527 | 108,458 |
| `cob_lowtemp_ind_heat_tbtu` | 0.0563 | 1.47 | 8.02 | 1.25 | 1.21 | 0.012 | 0.0347 | 0.0339 | 0.00132 | 0.824 |
| `cob_hdd_annual` | 4,775 | 1,338 | 6,228 | 1,278 | 6,303 | 2,971 | 2,238 | 2,526 | 7,168 | 6,431 |
| `cob_ej_disadvantaged` | 8.6 | 28.8 | 43.8 | 49.2 | 11.5 | 22.3 | 100 | 29.9 | 21 | 16.3 |
| `cob_qcew_dc_emp` | 2,045 | 9,277 | 9,784 | 2,788 | 19,792 | 199 | NaN | NaN | 102 | 1,155 |
| `cob_qcew_dc_emp_suppressed` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| `lbl_dc_existing_n` | 146 | 56 | 29 | 6 | 15 | 7 | 0 | 0 | 5 | 7 |
| `lbl_frontier_ai_dc_n` | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 2 | 1 | 0 |
| `lbl_contested_n` | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Per-column summary

| Column | Unit | % missing | Min | Max | Mean | Top 5 | Bottom 5 |
|---|---|---|---|---|---|---|---|
| `meta_county_name` | text | 0.0 | | | | Washington County (30), Jefferson County (25), Franklin County (24), Jackson County (23), Lincoln County (23) | |
| `meta_state_abbr` | text | 0.0 | | | | TX (254), GA (159), VA (133), KY (120), MO (115) | |
| `meta_state_fips` | code | 0.0 | | | | 48 (254), 13 (159), 51 (133), 21 (120), 29 (115) | |
| `meta_land_area_km2` | km2 | 0.0 | 5.3 | 51,977 | 2,462 | San Bernardino CA 51,977, Coconino AZ 48,216, Nye NV 47,091, Elko NV 44,479, Mohave AZ 34,530 | Falls Church VA 5.3, Lexington VA 6.47, Manassas Park VA 7.84, Covington VA 14.2, Fairfax VA 16.2 |
| `meta_pop_centroid_lat` | deg | 0.0 | 24.7 | 48.9 | 38.3 | Divide ND 48.9, Rolette ND 48.8, Roseau MN 48.8, Whatcom WA 48.8, Bottineau ND 48.8 | Monroe FL 24.7, Miami-Dade FL 25.8, Cameron TX 26, Broward FL 26.1, Collier FL 26.2 |
| `meta_pop_centroid_lon` | deg | 0.0 | -124 | -67.5 | -91.7 | Washington ME -67.5, Aroostook ME -68.1, Hancock ME -68.5, Penobscot ME -68.8, Waldo ME -69.1 | Curry OR -124, Coos OR -124, Del Norte CA -124, Humboldt CA -124, Lincoln OR -124 |
| `meta_pop_2023` | people | 0.0 | 52 | 9,848,406 | 106,210 | Los Angeles CA 9,848,406, Cook IL 5,185,812, Harris TX 4,758,579, Maricopa AZ 4,491,987, San Diego CA 3,282,782 | Kenedy TX 52, Loving TX 54, King TX 189, Blaine NE 385, Petroleum MT 401 |
| `pwr_gen_capacity_mw` | MW | 0.0 | 0 | 21,536 | 434 | Maricopa AZ 21,536, Kern CA 18,287, Clark NV 15,062, Los Angeles CA 13,883, Riverside CA 11,104 | Sullivan MO 0, Winston MS 0, Wilkinson MS 0, Webster MS 0, Wayne MS 0 |
| `pwr_retired_capacity_mw` | MW | 0.0 | 0 | 6,828 | 95.7 | Los Angeles CA 6,828, San Diego CA 5,046, Will IL 3,902, Broward FL 3,573, Harris TX 3,529 | Autauga AL 0, Greene NC 0, Harnett NC 0, Henderson NC 0, Hertford NC 0 |
| `pwr_dist_retired_plant_km` | km | 0.0 | 0.5 | 457 | 82.9 | Flathead MT 457, Glacier MT 454, Lake MT 452, Missoula MT 445, Ravalli MT 441 | Brown WI 0.5, Jefferson LA 0.644, Middlesex NJ 0.954, Hudson NJ 1.13, DuPage IL 2.01 |
| `pwr_hv230_line_km` | km | 0.0 | 0 | 3,442 | 95.5 | San Bernardino CA 3,442, Clark NV 3,243, Maricopa AZ 3,021, Los Angeles CA 2,788, Coconino AZ 1,745 | Sullivan MO 0, Nantucket MA 0, Dukes MA 0, Worcester MD 0, Talbot MD 0 |
| `pwr_dist_hv230_line_km` | km | 0.0 | 0.000605 | 174 | 16.9 | Presidio TX 174, Cook MN 172, Cherry NE 163, Chippewa MI 151, Luce MI 145 | Cheyenne NE 0.000605, Mercer NJ 0.00264, Cleveland OK 0.00367, Pottawatomie KS 0.00575, Lincoln SD 0.00705 |
| `pwr_hv345_line_km` | km | 0.0 | 0 | 2,290 | 50.5 | San Bernardino CA 2,290, Coconino AZ 1,518, Maricopa AZ 1,253, Clark NV 1,245, Los Angeles CA 995 | Sullivan MO 0, Carter MT 0, Carbon MT 0, Blaine MT 0, Beaverhead MT 0 |
| `pwr_dist_hv345_line_km` | km | 0.0 | 0.00367 | 271 | 30 | Lawrence SD 271, Meade SD 271, Pennington SD 255, Phillips MT 253, Blaine MT 250 | Cleveland OK 0.00367, Jefferson MO 0.0087, Linn KS 0.022, Cumberland PA 0.0256, Pottawatomie KS 0.0268 |
| `pwr_substations_230kv_n` | count | 0.0 | 0 | 84 | 2.2 | Cook IL 84, Maricopa AZ 80, Loudoun VA 75, Clark NV 67, Fairfax VA 59 | Sullivan MO 0, Isabella MI 0, Iron MI 0, Iosco MI 0, Ionia MI 0 |
| `pwr_gas_pipeline_km` | km | 0.0 | 0 | 2,235 | 111 | Sweetwater WY 2,235, Pecos TX 2,001, San Bernardino CA 1,916, Vermilion LA 1,769, Nueces TX 1,758 | Sullivan MO 0, Carroll TN 0, McCreary KY 0, Cannon TN 0, Campbell TN 0 |
| `pwr_ind_price_cents_kwh` | cents/kWh | 1.2 | 3.43 | 30.5 | 8.15 | Queens NY 30.5, Bronx NY 30.5, New York NY 30.5, Kings NY 30.5, Richmond NY 30.5 | Chelan WA 3.43, Okanogan WA 3.53, Douglas WA 3.95, Marshall KY 4.18, Calloway KY 4.3 |
| `pwr_saidi_min` | minutes/yr | 7.4 | 0 | 822 | 161 | Franklin MS 822, Adams MS 822, Jefferson MS 822, Lincoln MS 822, Claiborne MS 822 | Richland WI 0, Nassau NY 7.44, Merrick NE 8.46, Warren TN 10.1, Adams NE 13.8 |
| `pwr_saifi` | interruptions/yr | 8.2 | 0 | 4.78 | 1.31 | Angelina TX 4.78, Sabine TX 4.78, Nacogdoches TX 4.68, Cherokee TX 4.68, Polk TN 4.64 | Richland WI 0, Clay NE 0.13, Adams NE 0.13, Teton WY 0.139, Nassau NY 0.154 |
| `pwr_saidi_min_with_me_latest` | minutes/yr | 8.3 | 0 | 9,415 | 620 | Montgomery GA 9,415, Tattnall GA 9,415, Toombs GA 9,415, Treutlen GA 9,415, Emanuel GA 9,019 | Davidson TN 0, Robertson TN 0, Merrick NE 12.2, Douglas WI 22.4, Wilson TN 24.7 |
| `pwr_saifi_with_me_latest` | interruptions/yr | 9.1 | 0 | 8.31 | 1.85 | Nacogdoches TX 8.31, Cherokee TX 8.31, Bristol VA 7.58, Rusk TX 6.3, Aroostook ME 6.19 | Robertson TN 0, Davidson TN 0, Teton WY 0.11, Clay NE 0.201, Adams NE 0.201 |
| `pwr_iso` | category | 0.6 | | | | NONE (1024), MISO (817), PJM (455), SPP (420), ERCOT (188) | |
| `pwr_main_utility_id` | id | 0.2 | 84 | 66,101 | 15,461 | Montgomery PA 66,101, Monroe PA 66,101, Franklin PA 66,101, Fulton PA 66,101, Greene PA 66,101 | Northampton VA 84, Barnwell SC 162, Orangeburg SC 162, Lincoln NV 191, Monroe AL 195 |
| `pwr_time_to_power_yrs` | years | 0.0 | 4 | 9 | 4.14 | Yuma AZ 9, Maricopa AZ 9, Greenlee AZ 9, Graham AZ 9, Gila AZ 9 | Autauga AL 4, Ward ND 4, Wells ND 4, Williams ND 4, Adams OH 4 |
| `pwr_time_to_power_source` | category | 0.0 | | | | national (2969), utility (126), not_accepting (14) | |
| `pwr_gen_queue_median_yrs` | years | 2.8 | 2.05 | 6.02 | 3.37 | Ventura CA 6.02, Contra Costa CA 6.02, Tulare CA 6.02, Alameda CA 6.02, Alpine CA 6.02 | Weston WY 2.05, Harney OR 2.05, Hood River OR 2.05, Jackson OR 2.05, Jefferson OR 2.05 |
| `crb_grid_co2_kg_mwh` | kg CO2/MWh | 0.0 | 110 | 634 | 373 | Columbia WI 634, Iowa WI 634, Door WI 634, Sauk WI 634, Keweenaw MI 634 | Genesee NY 110, Jefferson NY 110, Chenango NY 110, St. Lawrence NY 110, Oswego NY 110 |
| `crb_lrmer_2035_kg_mwh` | kg CO2e/MWh | 0.0 | 24.9 | 262 | 146 | District of Columbia DC 262, Anne Arundel MD 262, New Castle DE 262, Kent DE 262, Shelby OH 262 | Yamhill OR 24.9, Columbia WA 24.9, Cowlitz WA 24.9, Douglas WA 24.9, Ferry WA 24.9 |
| `crb_cambium_gea` | category | 0.0 | | | | SERTP (527), PJM_East (473), MISO_Central (318), SPP_South (304), MISO_North (298) | |
| `crb_clean_gen_mw` | MW | 0.0 | 0 | 10,162 | 159 | Kern CA 10,162, Maricopa AZ 7,339, Okanogan WA 6,495, Clark NV 6,279, Riverside CA 5,468 | Autauga AL 0, McDonald MO 0, Linn MO 0, Lewis MO 0, Knox MO 0 |
| `crb_queue_clean_mw` | MW | 0.0 | 0 | 27,727 | 496 | Kern CA 27,727, Maricopa AZ 23,067, Fresno CA 22,702, Los Angeles CA 21,374, Clark NV 20,785 | Autauga AL 0, Pondera MT 0, Phillips MT 0, Petroleum MT 0, Park MT 0 |
| `crb_solar_cf` | fraction 0-1 | 0.9 | 0.134 | 0.262 | 0.192 | El Paso TX 0.262, Luna NM 0.261, Doña Ana NM 0.261, Hidalgo NM 0.26, Hudspeth TX 0.26 | Snohomish WA 0.134, Skagit WA 0.137, King WA 0.137, Clallam WA 0.138, Pacific WA 0.139 |
| `crb_wind_cf` | fraction 0-1 | 4.1 | 0.0937 | 0.503 | 0.339 | Butler KS 0.503, Pocahontas WV 0.503, Canadian OK 0.497, Marion KS 0.482, Carson TX 0.478 | Orange CA 0.0937, Tulare CA 0.13, Hinsdale CO 0.134, Mariposa CA 0.134, Archuleta CO 0.137 |
| `wtr_bws_score` | score 0-5 | 0.0 | 0 | 5 | 2.05 | Crane TX 5, Jefferson CO 5, Terry TX 5, Sherman KS 5, Ottawa KS 5 | Franklin ME 0, Assumption LA 0, Avoyelles LA 0, East Carroll LA 0, Hettinger ND 0 |
| `wtr_bws_2050_score` | score 0-5 | 0.0 | 0 | 5 | 2.22 | Deuel NE 5, Kit Carson CO 5, Santa Cruz AZ 5, Hodgeman KS 5, Jefferson CO 5 | Marion MO 0, Callaway MO 0, Chittenden VT 0, Crittenden KY 0, Cooper MO 0 |
| `wtr_drought_d2plus_pct_weeks` | percent 0-100 | 0.0 | 0 | 66 | 15.4 | Navajo AZ 66, Apache AZ 63.3, Coconino AZ 62.4, Nye NV 60.6, McKinley NM 59.1 | Schenectady NY 0, Fulton NY 0, Sullivan PA 0, Madison NY 0, Montgomery NY 0 |
| `wtr_grid_water_l_kwh` | L/kWh | 0.0 | 0 | 1.38 | 0.836 | Adams WI 1.38, Kewaunee WI 1.38, Door WI 1.38, Keweenaw MI 1.38, Green Lake WI 1.38 | Nassau NY 0, Richmond NY 0, Queens NY 0, Kings NY 0, Bronx NY 0.000605 |
| `wtr_total_withdrawal_mgd` | Mgal/d | 0.0 | 0 | 3,386 | 71 | Fresno CA 3,386, Kern CA 2,431, Berrien MI 1,956, Merced CA 1,860, Tulare CA 1,855 | Mathews VA 0, Harding SD 0, Loving TX 0, Robertson KY 0.00843, Owen KY 0.0101 |
| `wtr_ps_withdrawal_mgd` | Mgal/d | 0.0 | 0 | 911 | 11.4 | Los Angeles CA 911, Cook IL 628, Maricopa AZ 622, Dallas TX 603, Harris TX 565 | Arthur NE 0, Mathews VA 0, Harding SD 0, Prairie MT 0, Loving TX 0 |
| `wtr_irr_withdrawal_mgd` | Mgal/d | 0.0 | 0 | 3,232 | 35.6 | Fresno CA 3,232, Kern CA 2,267, Merced CA 1,810, Imperial CA 1,808, Tulare CA 1,789 | Sullivan MO 0, Centre PA 0, Carbon PA 0, Cameron PA 0, Cambria PA 0 |
| `wtr_te_withdrawal_mgd` | Mgal/d | 0.0 | 0 | 1,916 | 24 | Berrien MI 1,916, Lancaster PA 1,806, Limestone AL 1,742, Southeastern Connecticut CT 1,673, Brunswick NC 1,657 | Sullivan MO 0, Nash NC 0, Northampton NC 0, Onslow NC 0, Orange NC 0 |
| `wtr_wwtp_flow_mgd` | Mgal/d | 0.0 | 0 | 2,016 | 16 | Cook IL 2,016, Los Angeles CA 1,202, Wayne MI 1,090, Cuyahoga OH 1,024, Harris TX 868 | Campbell SD 0, Wyoming PA 0, Inyo CA 0, Abbeville SC 0, Aiken SC 0 |
| `haz_nri_risk_score` | score 0-100 | 0.0 | 0.0318 | 100 | 50.3 | Los Angeles CA 100, Harris TX 100, Riverside CA 99.9, San Bernardino CA 99.9, Alameda CA 99.9 | Loving TX 0.0318, Keweenaw MI 0.0955, McPherson NE 0.127, Harding NM 0.223, Petroleum MT 0.255 |
| `haz_eal_riverine_flood` | score 0-100 | 0.0 | 0 | 100 | 50.6 | Harris TX 100, Galveston TX 100, Brazoria TX 99.9, East Baton Rouge LA 99.9, Shelby TN 99.9 | McPherson NE 0, Hubbard MN 0, Kidder ND 0, Banner NE 0, Lake of the Woods MN 0 |
| `haz_eal_coastal_flood` | score 0-100 | 0.0 | 0 | 100 | 7.91 | Bergen NJ 100, Ocean NJ 99.8, Atlantic NJ 99.7, Cape May NJ 99.5, Monmouth NJ 99.3 | Autauga AL 0, Stark ND 0, Steele ND 0, Stutsman ND 0, Towner ND 0 |
| `haz_eal_hurricane` | score 0-100 | 0.0 | 0 | 100 | 34.8 | Harris TX 100, Broward FL 100, Palm Beach FL 99.9, Miami-Dade FL 99.9, Hillsborough FL 99.8 | Weston WY 0, Dawes NE 0, Dakota NE 0, Custer NE 0, Cuming NE 0 |
| `haz_eal_wildfire` | score 0-100 | 0.0 | 0.0955 | 100 | 50.1 | San Diego CA 100, Riverside CA 100, San Bernardino CA 99.9, Los Angeles CA 99.9, Washington UT 99.9 | Scott IL 0.0955, Warren IL 0.127, Lawrence IL 0.159, Greene IL 0.191, Brown IL 0.223 |
| `haz_eal_tornado` | score 0-100 | 0.0 | 0.837 | 100 | 51.7 | Collin TX 100, Harris TX 100, Cook IL 99.9, Tarrant TX 99.9, Denton TX 99.9 | Esmeralda NV 0.837, Lincoln NV 0.962, White Pine NV 0.993, Alpine CA 1.02, Eureka NV 1.09 |
| `haz_eal_earthquake` | score 0-100 | 0.0 | 0 | 100 | 48.8 | Los Angeles CA 100, Santa Clara CA 100, Alameda CA 99.9, San Bernardino CA 99.9, Orange CA 99.9 | Lake MN 0, Cook MN 0, Keweenaw MI 0.0929, Kenedy TX 0.124, Slope ND 0.155 |
| `haz_eal_heatwave` | score 0-100 | 0.0 | 0 | 100 | 50 | Cook IL 100, St. Louis MO 100, Clark NV 99.9, Philadelphia PA 99.9, Dallas TX 99.9 | Weston WY 0, Cherokee GA 0, Chattooga GA 0, Dickens TX 0, DeWitt TX 0 |
| `haz_eal_drought` | score 0-100 | 0.0 | 0 | 100 | 50.3 | Santa Barbara CA 100, Yolo CA 100, Napa CA 99.9, Sutter CA 99.9, Colusa CA 99.9 | Sanilac MI 0, Monroe MI 0, Missaukee MI 0, Midland MI 0, Mecosta MI 0 |
| `haz_eal_coastal_flood_future` | score 0-100 | 0.0 | 0 | 100 | 7.82 | Bergen NJ 100, Atlantic NJ 99.8, Ocean NJ 99.6, Cape May NJ 99.4, Monmouth NJ 99.2 | Autauga AL 0, Pembina ND 0, Pierce ND 0, Ramsey ND 0, Ransom ND 0 |
| `haz_eal_drought_future` | score 0-100 | 0.0 | 7.4 | 100 | 50.4 | Santa Barbara CA 100, Yolo CA 100, Sutter CA 99.9, Napa CA 99.9, Colusa CA 99.9 | Madison NY 7.4, Buchanan VA 7.4, Bradford PA 7.4, Butler PA 7.4, Jefferson NY 7.4 |
| `haz_eal_heatwave_future` | score 0-100 | 0.0 | 8.59 | 100 | 50.5 | Clark NV 100, St. Louis MO 100, Dallas TX 99.9, Cook IL 99.9, Tulsa OK 99.9 | Weston WY 8.59, Towns GA 8.59, Troup GA 8.59, Tioga PA 8.59, Union GA 8.59 |
| `haz_eal_hurricane_future` | score 0-100 | 0.0 | 0 | 100 | 35.8 | Harris TX 100, Miami-Dade FL 100, Broward FL 99.9, Palm Beach FL 99.9, Hillsborough FL 99.8 | Weston WY 0, Cuming NE 0, Colfax NE 0, Clay NE 0, Cheyenne NE 0 |
| `haz_eal_wildfire_future` | score 0-100 | 0.0 | 0.0954 | 100 | 50.1 | San Diego CA 100, Riverside CA 100, San Bernardino CA 99.9, Los Angeles CA 99.9, Washington UT 99.9 | Scott IL 0.0954, Warren IL 0.127, Covington VA 0.159, Greene IL 0.191, Brown IL 0.223 |
| `haz_wildfire_risk_to_homes` | percentile 0-100 | 0.0 | 0 | 100 | 50 | San Diego CA 100, Broward FL 100, Elko NV 99.9, Miami-Dade FL 99.9, Chelan WA 99.9 | Van Wert OH 0, Benton IN 0, Putnam OH 0.1, Mercer OH 0.1, Tipton IN 0.1 |
| `haz_cdd_annual` | degree-days F | 0.0 | 0 | 4,413 | 1,257 | Monroe FL 4,413, Hidalgo TX 4,312, Starr TX 4,299, Miami-Dade FL 4,272, Imperial CA 4,264 | San Juan CO 0, Summit CO 0, Mineral CO 0, Lake CO 0, Hinsdale CO 0 |
| `haz_days_tmax_gt35c` | days/yr | 0.0 | 0 | 143 | 10.7 | Imperial CA 143, Yuma AZ 140, La Paz AZ 132, Maricopa AZ 127, Pinal AZ 114 | Rio Arriba NM 0, Larimer CO 0, Mackinac MI 0, Luce MI 0, Webster WV 0 |
| `haz_days_gt95f_2050` | days/yr | 0.0 | 0 | 161 | 33.7 | Yuma AZ 161, Imperial CA 160, La Paz AZ 154, Maricopa AZ 154, Zapata TX 148 | Lake CO 0, San Juan CO 0, Mineral CO 0.00275, Hinsdale CO 0.00522, Summit CO 0.00595 |
| `haz_karst_pct` | percent 0-100 | 0.0 | 0 | 100 | 27 | Stone MO 100, Fayette IA 100, Berrien GA 100, Wilcox GA 100, Madison FL 100 | LaPorte IN 0, Fairfield OH 0, Gallia OH 0, Geauga OH 0, Guernsey OH 0 |
| `haz_karst_exposed_pct` | percent 0-100 | 0.0 | 0 | 100 | 15.6 | Phelps MO 100, Dent MO 100, Crawford MO 100, Stone MO 100, Maries MO 100 | Sullivan MO 0, Clatsop OR 0, Columbia OR 0, Deschutes OR 0, Cecil MD 0 |
| `lnd_pct_developed` | percent 0-100 | 0.0 | 0.246 | 99.7 | 11.3 | Falls Church VA 99.7, Fairfax VA 96.9, Arlington VA 96.7, Alexandria VA 96.4, San Francisco CA 95.6 | Esmeralda NV 0.246, Inyo CA 0.336, Brewster TX 0.42, Mineral NV 0.427, Lincoln NV 0.44 |
| `lnd_pct_buildable` | percent 0-100 | 0.0 | 0 | 99.1 | 28.8 | Terrell TX 99.1, Jim Hogg TX 98.8, De Baca NM 98.2, Guadalupe NM 98, Crockett TX 98 | Falls Church VA 0, Fairfax VA 0, Arlington VA 0.000794, Humphreys MS 0.00105, Quitman MS 0.00718 |
| `lnd_pct_wetland` | percent 0-100 | 0.0 | 0 | 79.1 | 7.66 | Koochiching MN 79.1, Franklin FL 77.5, Dare NC 76.7, Collier FL 72.7, Monroe FL 71.2 | Norton VA 0, Lexington VA 0, Roanoke VA 0, Salem VA 0, Staunton VA 0 |
| `lnd_pct_cropland` | percent 0-100 | 0.0 | 0 | 90.8 | 21.5 | Benton IN 90.8, Grundy IA 90.6, Pocahontas IA 90.3, Ford IL 89.9, Traill ND 89.7 | Lexington VA 0, Doddridge WV 0, Camp TX 0, Clay WV 0, Harlan KY 0 |
| `lnd_pct_forest` | percent 0-100 | 0.0 | 0 | 93.1 | 28.6 | Swain NC 93.1, Cameron PA 92.8, Webster WV 92.4, Clay WV 91.2, McDowell WV 90.8 | Loving TX 0, Denver CO 0, Carson TX 0, Moore TX 0, Broomfield CO 0 |
| `lnd_pct_protected` | percent 0-100 | 0.0 | 0 | 100 | 5.13 | San Juan WA 100, Teton WY 76.2, Monroe FL 74.6, Hamilton NY 71.6, Inyo CA 66.1 | Grant IN 0, Lavaca TX 0, Lampasas TX 0, Lamb TX 0, Fallon MT 0 |
| `lnd_brownfields_n` | count | 0.0 | 0 | 636 | 13.2 | Cook IL 636, Wayne MI 580, Oklahoma OK 461, Miami-Dade FL 375, St. Louis MO 367 | Hartley TX 0, Hale TX 0, Hall TX 0, Hopkins KY 0, Hart KY 0 |
| `lnd_dist_brownfield_km` | km | 0.0 | 0.0599 | 241 | 15.6 | Presidio TX 241, Jeff Davis TX 179, Brewster TX 167, Culberson TX 147, Edwards TX 141 | Marion IN 0.0599, Erie NY 0.0688, Monroe NY 0.072, Johnson IA 0.0869, Missoula MT 0.0876 |
| `lnd_dist_brownfield_or_retired_km` | km | 0.0 | 0.0599 | 211 | 14.9 | Presidio TX 211, Culberson TX 147, Jeff Davis TX 146, Edwards TX 141, Val Verde TX 139 | Marion IN 0.0599, Erie NY 0.0688, Monroe NY 0.072, Johnson IA 0.0869, Missoula MT 0.0876 |
| `lnd_dist_interstate_km` | km | 0.0 | 0.0018 | 290 | 35.8 | Keweenaw MI 290, Houghton MI 262, Esmeralda NV 243, Phillips MT 238, Baraga MI 227 | Bexar TX 0.0018, McCracken KY 0.0114, Tulsa OK 0.0128, Lexington SC 0.0135, St. Charles LA 0.0205 |
| `lnd_ixp_n` | count | 0.0 | 0 | 28 | 0.153 | Santa Clara CA 28, Loudoun VA 27, Dallas TX 24, New York NY 19, Miami-Dade FL 17 | Autauga AL 0, Holmes OH 0, Huron OH 0, Jackson OH 0, Jefferson OH 0 |
| `lnd_colo_fac_n` | count | 0.0 | 0 | 53 | 0.432 | Santa Clara CA 53, Cook IL 50, Loudoun VA 42, Los Angeles CA 42, Dallas TX 38 | Autauga AL 0, Belmont OH 0, Brown OH 0, Carroll OH 0, Champaign OH 0 |
| `lnd_dist_ixp_km` | km | 0.0 | 0.515 | 521 | 136 | Divide ND 521, Jackson SD 504, Haakon SD 479, Burke ND 479, Mellette SD 474 | Ada ID 0.515, Dane WI 0.735, Orange FL 1.28, Los Angeles CA 1.38, Mecklenburg NC 1.44 |
| `lnd_dist_eaf_steel_km` | km | 0.0 | 0.8 | 932 | 221 | Daniels MT 932, Sheridan MT 926, Divide ND 887, Roosevelt MT 886, Aroostook ME 856 | Roanoke VA 0.8, Cuyahoga OH 1.57, Brooke WV 1.76, Sebastian AR 2.09, Tuscaloosa AL 2.41 |
| `lnd_dist_cement_km` | km | 0.0 | 1.44 | 680 | 163 | Pembina ND 680, Kittson MN 675, Roseau MN 654, Aroostook ME 651, Walsh ND 650 | York PA 1.44, Pontotoc OK 2.3, Berkeley WV 2.69, Mayes OK 2.85, Northampton PA 4.05 |
| `prm_pop_density_km2` | people/km2 | 0.0 | 0.0138 | 27,738 | 108 | New York NY 27,738, Kings NY 14,728, Bronx NY 12,985, Queens NY 8,275, San Francisco CA 6,917 | Kenedy TX 0.0138, Loving TX 0.0312, Garfield MT 0.0774, King TX 0.0801, Petroleum MT 0.0935 |
| `prm_nonattainment` | 0/1 | 0.0 | 0 | 1 | 0.0762 | Bullitt KY 1, Brazoria TX 1, Sonoma CA 1, Solano CA 1, Fairfax VA 1 | Autauga AL 0, Delaware OH 0, Erie OH 0, Fairfield OH 0, Fayette OH 0 |
| `prm_pct_tribal` | percent 0-100 | 0.0 | 0 | 100 | 1.38 | Bennett SD 100, Dewey SD 100, Corson SD 100, Osage OK 100, Ziebach SD 100 | Autauga AL 0, Hettinger ND 0, Kidder ND 0, LaMoure ND 0, Logan ND 0 |
| `prm_pct_ok_tribal_stat_area` | percent 0-100 | 0.0 | 0 | 100 | 1.98 | Custer OK 100, Murray OK 100, Rogers OK 100, Carter OK 100, Coal OK 100 | Autauga AL 0, Williams ND 0, Adams OH 0, Allen OH 0, Ashland OH 0 |
| `prm_nrhp_n` | count | 0.0 | 0 | 1,336 | 29.8 | Middlesex MA 1,336, Worcester MA 689, District of Columbia DC 657, Multnomah OR 634, Philadelphia PA 620 | Missaukee MI 0, Terry TX 0, Poquoson VA 0, Borden TX 0, Frontier NE 0 |
| `prm_price_growth_pct` | percent | 0.0 | -7.19 | 51.1 | 18 | Kings CA 51.1, San Mateo CA 51.1, San Joaquin CA 51.1, San Francisco CA 51.1, San Diego CA 51.1 | Traill ND -7.19, LaMoure ND -7.19, Kidder ND -7.19, Hettinger ND -7.19, Griggs ND -7.19 |
| `prm_moratorium_active` | 0/0.5/1 | 0.0 | 0 | 1 | 0.00386 | Suffolk VA 1, Calvert MD 1, Clayton GA 1, Hill TX 1, Santa Fe NM 1 | Autauga AL 0, Medina OH 0, Meigs OH 0, Mercer OH 0, Miami OH 0 |
| `prm_moratorium_proposed` | 0/1 | 0.0 | 0 | 1 | 0.00193 | Warren VA 1, Clayton GA 1, Orleans LA 1, Spartanburg SC 1, Loudoun VA 1 | Autauga AL 0, Miami OH 0, Monroe OH 0, Montgomery OH 0, Morgan OH 0 |
| `prm_state_moratorium` | 0/1 | 0.0 | 0 | 1 | 0.0199 | Seneca NY 1, Franklin NY 1, Montgomery NY 1, Monroe NY 1, Madison NY 1 | Autauga AL 0, Trumbull OH 0, Tuscarawas OH 0, Union OH 0, Van Wert OH 0 |
| `meta_state_policy_verified` | 0/1 | 0.0 | 0 | 1 | 0.395 | Cimarron OK 1, Delaware OK 1, Cherokee OK 1, Choctaw OK 1, Cleveland OK 1 | Autauga AL 0, Linn MO 0, Lincoln MO 0, Lewis MO 0, Lawrence MO 0 |
| `prm_tax_exemption_status` | category | 0.0 | | | | unknown (2429), active (454), paused (226) | |
| `prm_large_load_tariff` | 0/1 | 0.0 | 0 | 1 | 0.276 | Rabun GA 1, Madison FL 1, Campbell SD 1, Butte SD 1, Buffalo SD 1 | Autauga AL 0, Garfield NE 0, Gosper NE 0, Grant NE 0, Greeley NE 0 |
| `prm_county_can_zone` | 0/1 | 0.0 | 0 | 1 | 0.918 | Weston WY 1, Knott KY 1, Meade KY 1, Mason KY 1, Martin KY 1 | Mills TX 0, Wichita TX 0, Wilbarger TX 0, Willacy TX 0, Williamson TX 0 |
| `prm_contested_n` | count | 0.0 | 0 | 4 | 0.0193 | Porter IN 4, Maricopa AZ 3, Culpeper VA 2, Prince William VA 2, Washtenaw MI 2 | Autauga AL 0, Lake OH 0, Lawrence OH 0, Licking OH 0, Logan OH 0 |
| `prm_contested_neighbors_n` | count | 0.0 | 0 | 7 | 0.116 | Stafford VA 7, Fauquier VA 5, Starke IN 4, Livingston MI 4, Lake IN 4 | Autauga AL 0, Towner ND 0, Traill ND 0, Walsh ND 0, Ward ND 0 |
| `cob_unemp_rate` | percent | 0.0 | 1.3 | 18.4 | 3.94 | Imperial CA 18.4, Colusa CA 13.2, Yuma AZ 12.7, East Carroll LA 12.5, Luna NM 12.2 | Brule SD 1.3, Loving TX 1.3, Tripp SD 1.4, Perkins SD 1.4, Hand SD 1.4 |
| `cob_poverty_pct` | percent 0-100 | 0.0 | 1.7 | 52.8 | 14.3 | Oglala Lakota SD 52.8, Todd SD 49, Mellette SD 46.2, Corson SD 45.2, Dimmit TX 44.8 | Morgan UT 1.7, Stanley SD 2.06, Sterling TX 2.73, Los Alamos NM 2.93, Nantucket MA 3.03 |
| `cob_median_hh_income` | USD (2023) | 0.1 | 25,425 | 178,707 | 65,904 | Loudoun VA 178,707, Santa Clara CA 159,674, San Mateo CA 156,000, Falls Church VA 154,734, Fairfax VA 150,113 | Randolph GA 25,425, Jackson SD 26,686, East Carroll LA 28,321, Presidio TX 29,014, Wolfe KY 29,052 |
| `cob_pct_fossil_heat` | percent 0-100 | 0.0 | 2.13 | 92.1 | 50.9 | Nassau NY 92.1, Decatur KS 91.9, Richmond NY 91.8, Wibaux MT 91.2, Bristol RI 90.6 | Glades FL 2.13, Highlands FL 2.5, Charlotte FL 2.63, Union FL 2.65, Douglas WA 2.69 |
| `cob_persistent_poverty` | 0/1 | 0.5 | 0 | 1 | 0.102 | Duval TX 1, Rowan KY 1, Coal OK 1, Corson SD 1, Perry KY 1 | Autauga AL 0, Champaign OH 0, Clark OH 0, Clermont OH 0, Clinton OH 0 |
| `cob_energy_community` | 0/1 | 0.0 | 0 | 1 | 0.343 | Weston WY 1, Perry IL 1, Marion OH 1, Pulaski IL 1, Meigs OH 1 | Autauga AL 0, Chenango NY 0, Clinton NY 0, Columbia NY 0, Cortland NY 0 |
| `cob_energy_community_pct` | percent 0-100 | 0.0 | 0 | 100 | 35.2 | White IL 100, Shelby IL 100, Kendall IL 100, Ouachita AR 100, Galax VA 100 | Sullivan MO 0, Wallace KS 0, Wabaunsee KS 0, Trego KS 0, Thomas KS 0 |
| `cob_ghgrp_combustion_facilities_n` | count | 0.0 | 0 | 44 | 0.379 | Harris TX 44, Jefferson TX 17, Calcasieu LA 14, Ascension LA 13, Brazoria TX 11 | Weston WY 0, Shackelford TX 0, Cuming NE 0, Custer NE 0, Scurry TX 0 |
| `cob_ghgrp_combustion_tco2` | t CO2e/yr | 0.0 | 0 | 13,059,502 | 55,418 | Harris TX 13,059,502, Brazoria TX 9,551,012, Jefferson TX 7,976,601, Ascension LA 6,894,029, Calhoun TX 5,237,128 | Weston WY 0, Cuming NE 0, Custer NE 0, Schleicher TX 0, Dawes NE 0 |
| `cob_lowtemp_ind_heat_tbtu` | TBtu/yr | 0.0 | 0 | 8.02 | 0.126 | Cook IL 8.02, Linn IA 7.9, Macon IL 7.79, Washington NE 6.66, Los Angeles CA 6.09 | Weston WY 0, Carter MT 0, Broadwater MT 0, Big Horn MT 0, Dinwiddie VA 0 |
| `cob_hdd_annual` | degree-days F | 0.0 | 125 | 10,980 | 4,912 | Lake CO 10,980, Teton WY 10,773, San Juan CO 10,744, Summit CO 10,574, Sublette WY 10,533 | Monroe FL 125, Miami-Dade FL 139, Broward FL 174, Collier FL 220, Palm Beach FL 230 |
| `cob_ej_disadvantaged` | percent 0-100 | 0.0 | 0 | 100 | 46.6 | Jackson TN 100, Bennett SD 100, St. Francis AR 100, Clare MI 100, Dewey SD 100 | Weston WY 0, Meeker MN 0, Murray MN 0, Nicollet MN 0, Norman MN 0 |
| `cob_qcew_dc_emp` | people | 41.0 | 0 | 19,792 | 198 | King WA 19,792, New York NY 17,727, San Francisco CA 16,709, Santa Clara CA 14,593, Fulton GA 12,128 | Chester TN 0, Bollinger MO 0, Benton MO 0, Bates MO 0, Barton MO 0 |
| `cob_qcew_dc_emp_suppressed` | 0/1 | 0.0 | 0 | 1 | 0.41 | Weston WY 1, McLean ND 1, Ogle IL 1, Watauga NC 1, Wayne NC 1 | Autauga AL 0, Valley NE 0, Thomas NE 0, Thayer NE 0, Stanton NE 0 |
| `lbl_dc_existing_n` | count | 0.0 | 0 | 146 | 0.393 | Loudoun VA 146, Santa Clara CA 74, Maricopa AZ 56, Prince William VA 55, Umatilla OR 31 | Autauga AL 0, Brown OH 0, Carroll OH 0, Champaign OH 0, Clermont OH 0 |
| `lbl_frontier_ai_dc_n` | count | 0.0 | 0 | 3 | 0.0216 | Bexar TX 3, Henrico VA 3, Licking OH 2, Linn IA 2, Shelby TN 2 | Autauga AL 0, Lake OH 0, Lawrence OH 0, Logan OH 0, Lorain OH 0 |
| `lbl_contested_n` | count | 0.0 | 0 | 4 | 0.0193 | Porter IN 4, Maricopa AZ 3, Culpeper VA 2, Prince William VA 2, Washtenaw MI 2 | Autauga AL 0, Lake OH 0, Lawrence OH 0, Licking OH 0, Logan OH 0 |
