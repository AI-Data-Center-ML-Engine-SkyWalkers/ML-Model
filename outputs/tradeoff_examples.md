# Trade-off examples

One 100 MW campus (load factor 0.8). PUE and WUE are judgment assumptions that rise with cooling degree days. Energy cost is electricity only (no land or construction). Candidates are surviving, non-vetoed counties. Hard exclusions stay on.

Reference county: Cowlitz County, WA (`53015`).

## 1. CO2 cap at 25,000 t/yr

**To keep CO2 under 25,000 t/yr, you give up nothing versus the unconstrained ranking: Cowlitz already clears the cap and stays first.**

Best: **Cowlitz County, WA** (`53015`). 66 feasible. Objective `score` = 0.675.

| Metric | Best | Cowlitz | Change | Verdict |
|---|---:|---:|---:|---|
| PUE (judgment assumption) | 1.120 | 1.120 | 0.000 (+0.0%) | same |
| WUE (judgment assumption, on-site L/kWh IT) | 0.133 | 0.133 | 0.000 (+0.0%) | same |
| Facility energy | 784,673.5 | 784,673.5 | 0.000 (+0.0%) | same |
| CO2 (long-run marginal, 2035) | 19,527.1 | 19,527.1 | 0.000 (+0.0%) | same |
| CO2 (today's average grid, reference only) | 224,848.3 | 224,848.3 | 0.000 (+0.0%) | same |
| Water (direct + grid-indirect) | 540.6 | 540.6 | 0.000 (+0.0%) | same |
| Water stress 2050 | 0.000 | 0.000 | 0.000 (+0.0%) | same |
| Energy cost (electricity only; excludes land and construction) | 60.812 | 60.812 | 0.000 (+0.0%) | same |
| Time to power | 6.000 | 6.000 | 0.000 (+0.0%) | same |
| Power pillar | 0.668 | 0.668 | 0.000 (+0.0%) | same |
| Carbon pillar | 0.595 | 0.595 | 0.000 (+0.0%) | same |
| Water pillar | 0.843 | 0.843 | 0.000 (+0.0%) | same |
| Hazard pillar | 0.697 | 0.697 | 0.000 (+0.0%) | same |
| Permission pillar | 0.811 | 0.811 | 0.000 (+0.0%) | same |
| Land pillar | 0.733 | 0.733 | 0.000 (+0.0%) | same |
| Co-benefit pillar | 0.419 | 0.419 | 0.000 (+0.0%) | same |
| Overall score (geometric mean, base weights) | 0.675 | 0.675 | 0.000 (+0.0%) | same |

Top picks:

| pick_rank | county | state | score | co2_t | energy_cost_musd | time_to_power_yrs | water_ml | hazard |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Cowlitz County | WA | 0.67 | 19,527.1 | 60.81 | 6.00 | 540.6 | 0.70 |
| 2 | Whatcom County | WA | 0.67 | 19,299.2 | 60.10 | 6.00 | 520.1 | 0.72 |
| 3 | Benton County | WA | 0.67 | 20,700.2 | 64.47 | 6.00 | 646.0 | 0.64 |
| 4 | Pierce County | WA | 0.66 | 19,345.5 | 60.25 | 6.00 | 524.3 | 0.73 |
| 5 | Multnomah County | OR | 0.65 | 19,723.6 | 61.42 | 6.00 | 558.2 | 0.75 |
| 6 | Clackamas County | OR | 0.65 | 19,513.3 | 60.77 | 6.00 | 539.3 | 0.69 |
| 7 | King County | WA | 0.65 | 19,370.4 | 60.32 | 6.00 | 526.5 | 0.76 |
| 8 | Clark County | WA | 0.64 | 19,730.5 | 61.45 | 6.00 | 558.9 | 0.79 |
| 9 | Skagit County | WA | 0.64 | 19,315.1 | 60.15 | 6.00 | 521.5 | 0.67 |
| 10 | Yakima County | WA | 0.64 | 19,717.2 | 61.40 | 6.00 | 557.7 | 0.62 |

## 2. Lowest CO2 that still gets power in ≤4 years

**To get the lowest long-run CO2 with power in ≤4 years, you give up Cowlitz (wait 6 yrs, 19527 t/yr) and pick Alameda County, CA at 55285 t/yr (score 0.609).**

Best: **Alameda County, CA** (`06001`). 144 feasible. Objective `co2_t` = 55,285.5.

| Metric | Best | Cowlitz | Change | Verdict |
|---|---:|---:|---:|---|
| PUE (judgment assumption) | 1.184 | 1.120 | 0.064 (+5.7%) | worse |
| WUE (judgment assumption, on-site L/kWh IT) | 0.240 | 0.133 | 0.107 (+80.8%) | worse |
| Facility energy | 829,772.5 | 784,673.5 | 45,099.0 (+5.7%) | worse |
| CO2 (long-run marginal, 2035) | 55,285.5 | 19,527.1 | 35,758.4 (+183.1%) | worse |
| CO2 (today's average grid, reference only) | 161,264.6 | 224,848.3 | -63,583.7 (-28.3%) | better |
| Water (direct + grid-indirect) | 698.4 | 540.6 | 157.8 (+29.2%) | worse |
| Water stress 2050 | 2.181 | 0.000 | 2.181 | worse |
| Energy cost (electricity only; excludes land and construction) | 232.8 | 60.812 | 172.0 (+282.9%) | worse |
| Time to power | 4.000 | 6.000 | -2.000 (-33.3%) | better |
| Power pillar | 0.670 | 0.668 | 0.001 (+0.2%) | better |
| Carbon pillar | 0.727 | 0.595 | 0.132 (+22.2%) | better |
| Water pillar | 0.643 | 0.843 | -0.199 (-23.6%) | worse |
| Hazard pillar | 0.602 | 0.697 | -0.095 (-13.7%) | worse |
| Permission pillar | 0.626 | 0.811 | -0.185 (-22.9%) | worse |
| Land pillar | 0.639 | 0.733 | -0.094 (-12.8%) | worse |
| Co-benefit pillar | 0.308 | 0.419 | -0.111 (-26.5%) | worse |
| Overall score (geometric mean, base weights) | 0.609 | 0.675 | -0.065 (-9.7%) | worse |

Top picks:

| pick_rank | county | state | score | co2_t | energy_cost_musd | time_to_power_yrs | water_ml | hazard |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Alameda County | CA | 0.61 | 55,285.5 | 232.8 | 4.00 | 698.4 | 0.60 |
| 2 | Contra Costa County | CA | 0.61 | 56,284.9 | 237.0 | 4.00 | 733.0 | 0.61 |
| 3 | Solano County | CA | 0.60 | 57,298.0 | 241.3 | 4.00 | 768.0 | 0.58 |
| 4 | Sweetwater County | WY | 0.62 | 59,306.5 | 60.67 | 4.00 | 544.1 | 0.74 |
| 5 | Big Horn County | MT | 0.62 | 60,883.2 | 62.44 | 4.00 | 590.3 | 0.60 |
| 6 | Yellowstone County | MT | 0.64 | 61,355.6 | 63.14 | 4.00 | 604.8 | 0.70 |
| 7 | Rosebud County | MT | 0.63 | 61,430.3 | 63.36 | 4.00 | 629.1 | 0.72 |
| 8 | Albany County | WY | 0.60 | 65,848.8 | 60.78 | 4.00 | 518.0 | 0.60 |
| 9 | Garfield County | CO | 0.62 | 66,372.5 | 61.12 | 4.00 | 529.7 | 0.70 |
| 10 | Lamar County | TX | 0.63 | 67,005.0 | 58.62 | 4.00 | 1,005.8 | 0.35 |

*Without the floor:* Alpine County, CA at 51553 t/yr (score 0.421).

## 3. Accept more climate risk (hazard floor 0.8 → 0.3)

**To accept more climate risk (hazard floor 0.80 → 0.30, hazard ignored in the score), you give up Ottawa County, MI and move to Mayes County, OK: CO2 106,083.3 → 96,588.1 t/yr, energy $67.185M → $51.187M/yr, score 0.629 → 0.664.**

Score ignores hazard; each row adds `hazard >= floor`. What extra risk buys:

| Hazard floor | Feasible | Best | CO2 t/yr | Energy $M/yr | Score | Changed |
|---:|---:|---|---:|---:|---:|---|
| 0.80 | 51 | Ottawa County, MI | 106,083.3 | 67.185 | 0.629 |  |
| 0.73 | 284 | Rock Island County, IL | 109,622.8 | 44.393 | 0.661 | yes |
| 0.66 | 739 | Cowlitz County, WA | 19,527.1 | 60.812 | 0.675 | yes |
| 0.59 | 1252 | Cowlitz County, WA | 19,527.1 | 60.812 | 0.675 |  |
| 0.51 | 1676 | Dallas County, TX | 68,598.9 | 60.036 | 0.660 | yes |
| 0.44 | 2029 | Dallas County, TX | 68,598.9 | 60.036 | 0.660 |  |
| 0.37 | 2393 | Mayes County, OK | 96,588.1 | 51.187 | 0.664 | yes |
| 0.30 | 2475 | Mayes County, OK | 96,588.1 | 51.187 | 0.664 |  |

## 4. Cheapest energy with low water stress

**To get the cheapest electricity in a low-stress basin (BWS 2050 ≤ 1), you give up 9% of overall score and pick Marshall County, KY — energy cost $37.8M/yr vs Cowlitz $60.8M/yr (score 0.617). Dropped 12 counties with missing energy cost.**

Best: **Marshall County, KY** (`21157`). 84 feasible. Objective `energy_cost_musd` = 37.819.

| Metric | Best | Cowlitz | Change | Verdict |
|---|---:|---:|---:|---|
| PUE (judgment assumption) | 1.292 | 1.120 | 0.172 (+15.4%) | worse |
| WUE (judgment assumption, on-site L/kWh IT) | 0.420 | 0.133 | 0.287 (+215.9%) | worse |
| Facility energy | 905,254.2 | 784,673.5 | 120,580.7 (+15.4%) | worse |
| CO2 (long-run marginal, 2035) | 129,703.4 | 19,527.1 | 110,176.3 (+564.2%) | worse |
| CO2 (today's average grid, reference only) | 368,766.0 | 224,848.3 | 143,917.6 (+64.0%) | worse |
| Water (direct + grid-indirect) | 972.8 | 540.6 | 432.3 (+80.0%) | worse |
| Water stress 2050 | 0.000 | 0.000 | 0.000 (+0.0%) | same |
| Energy cost (electricity only; excludes land and construction) | 37.819 | 60.812 | -22.993 (-37.8%) | better |
| Time to power | 4.000 | 6.000 | -2.000 (-33.3%) | better |
| Power pillar | 0.724 | 0.668 | 0.055 (+8.3%) | better |
| Carbon pillar | 0.456 | 0.595 | -0.139 (-23.3%) | worse |
| Water pillar | 0.726 | 0.843 | -0.116 (-13.8%) | worse |
| Hazard pillar | 0.513 | 0.697 | -0.185 (-26.5%) | worse |
| Permission pillar | 0.832 | 0.811 | 0.021 (+2.6%) | better |
| Land pillar | 0.716 | 0.733 | -0.017 (-2.3%) | worse |
| Co-benefit pillar | 0.389 | 0.419 | -0.030 (-7.1%) | worse |
| Overall score (geometric mean, base weights) | 0.617 | 0.675 | -0.058 (-8.5%) | worse |

Top picks:

| pick_rank | county | state | score | co2_t | energy_cost_musd | time_to_power_yrs | water_ml | hazard |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Marshall County | KY | 0.62 | 129,703.4 | 37.82 | 4.00 | 972.8 | 0.51 |
| 2 | Dakota County | NE | 0.63 | 114,456.9 | 39.34 | 4.00 | 706.9 | 0.60 |
| 3 | Hancock County | KY | 0.62 | 113,959.4 | 42.95 | 4.00 | 916.8 | 0.54 |
| 4 | Lucas County | OH | 0.61 | 221,295.5 | 45.89 | 4.00 | 1,161.4 | 0.72 |
| 5 | Mercer County | ND | 0.60 | 109,202.6 | 50.54 | 4.00 | 618.7 | 0.73 |
| 6 | St. Charles Parish | LA | 0.61 | 159,589.5 | 50.64 | 4.00 | 1,521.4 | 0.36 |
| 7 | Woodbury County | IA | 0.64 | 119,239.3 | 50.88 | 4.00 | 700.2 | 0.57 |
| 8 | Mayes County | OK | 0.66 | 96,588.1 | 51.19 | 4.00 | 1,207.5 | 0.39 |
| 9 | Muskogee County | OK | 0.61 | 97,845.5 | 51.68 | 4.00 | 1,239.1 | 0.41 |
| 10 | St. Landry Parish | LA | 0.62 | 159,589.5 | 52.52 | 4.00 | 1,376.7 | 0.39 |

*Without the floor:* Marshall County, KY at $37.8M/yr (score 0.617).

## 5. Faster power (wait ≤ 6, 5, 4 years)

**Power in 4 years costs 98772 more tCO2/yr than power in 6 years.**

How CO2, water and score change as you demand faster power:

| Wait ≤ yrs | Feasible | Best | CO2 t/yr | Water ML | Score | Changed |
|---:|---:|---|---:|---:|---:|---|
| 6 | 2371 | Cowlitz County, WA | 19,527.1 | 540.6 | 0.675 |  |
| 5 | 2305 | Linn County, IA | 118,299.2 | 685.2 | 0.665 | yes |
| 4 | 2305 | Linn County, IA | 118,299.2 | 685.2 | 0.665 |  |

Time to power is a judgment value (6 yrs) for NorthernGrid_West and the national 4-yr default for most other utilities, including Linn IA. Treat the carbon cost of speed as indicative.

## 6. Pareto: CO2 vs energy cost

**To sit on the CO2–energy-cost front (8 counties), you give up Cowlitz (not on the front). Nearest front county: Whatcom County, WA (CO2 19299 t/yr, energy $60.1M/yr).**

Front size: **8** of 2,475 candidates. Cowlitz is not on the front; nearest is Whatcom County, WA (`53073`).

| County | State | CO2 t/yr | Energy $M/yr | Score |
|---|---|---:|---:|---:|
| Whatcom County | WA | 19,299.2 | 60.102 | 0.670 |
| Lamar County | TX | 67,005.0 | 58.619 | 0.635 |
| Mayes County | OK | 96,588.1 | 51.187 | 0.664 |
| San Juan County | NM | 104,583.4 | 48.501 | 0.617 |
| Rock Island County | IL | 109,622.8 | 44.393 | 0.661 |
| Hancock County | KY | 113,959.4 | 42.954 | 0.619 |
| Dakota County | NE | 114,456.9 | 39.343 | 0.634 |
| Marshall County | KY | 129,703.4 | 37.819 | 0.617 |

*Without the floor:* front has 6 counties: Clallam County WA (0.503), Sublette County WY (0.465), Park County MT (0.490), Flathead County MT (0.511), Shoshone County ID (0.577), Sioux County NE (0.414).

