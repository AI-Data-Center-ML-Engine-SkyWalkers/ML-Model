# Sanity report

## Step 0 notes

- `lnd_pct_buildable` is NLCD barren / shrub / grassland / pasture (31, 52, 71, 81) and does **not** include cropland (82). The land exclusion therefore uses `cand_land_km2 = (lnd_pct_buildable + lnd_pct_cropland) / 100 × meta_land_area_km2`.
- Hazard pillar uses NRI expected-annual-loss-rate national percentiles (RFLD_ALR_NPCTL, WFIR_ALR_NPCTL, ERQK_ALR_NPCTL, TRND_ALR_NPCTL, HRCN_ALR_NPCTL, CFLD_ALR_NPCTL) from cached data/raw/fema_nri/NRI_Table_Counties.csv.

## 1. Legacy persona (power 0.5, land 0.3, hazard 0.2; no veto; power without time-to-power)

- Share of top 100 with `lbl_dc_existing_n` > 0: **50.0%** (50 / 100)
- Base rate among surviving counties: **7.7%**
- Spearman correlation(score, `lbl_dc_existing_n`): **0.295**

Hub counties (Step 1 list):

- Loudoun VA (`51107`): legacy rank 6, score 0.809, existing DCs 146
- Prince William VA (`51153`): legacy rank 45, score 0.764, existing DCs 55
- Maricopa AZ (`04013`): legacy rank 20, score 0.782, existing DCs 56
- Dallas TX (`48113`): legacy rank 24, score 0.779, existing DCs 25
- Polk IA (`19153`): legacy rank 204, score 0.706, existing DCs 7
- Pottawattamie IA (`19155`): legacy rank 42, score 0.764, existing DCs 18
- Licking OH (`39089`): legacy rank 247, score 0.698, existing DCs 27
- Grant WA (`53025`): legacy rank 253, score 0.697, existing DCs 15
- Laramie WY (`56021`): excluded (Extreme water stress)

### Top 10 (legacy)

```
 rank             county state  final_score  power  carbon  water  permission  hazard  land  cobenefit
    1  Montgomery County    PA        0.825  0.882   0.365  0.584       0.658   0.726 0.803      0.207
    2        Cook County    IL        0.823  0.867   0.418  0.534       0.524   0.742 0.809      0.599
    3      DuPage County    IL        0.813  0.855   0.305  0.536       0.620   0.748 0.788      0.413
    4 Rock Island County    IL        0.811  0.815   0.593  0.670       0.712   0.762 0.839      0.315
    5      Fulton County    GA        0.809  0.884   0.494  0.541       0.790   0.654 0.803      0.130
    6     Loudoun County    VA        0.809  0.884   0.350  0.823       0.549   0.715 0.757      0.085
    7        Will County    IL        0.807  0.859   0.499  0.533       0.595   0.714 0.790      0.450
    8     Chester County    PA        0.805  0.823   0.339  0.567       0.665   0.758 0.808      0.117
    9    Cuyahoga County    OH        0.799  0.842   0.259  0.680       0.753   0.789 0.739      0.266
   10      Pierce County    WA        0.795  0.819   0.639  0.880       0.804   0.726 0.802      0.190
```

## 2. Contested projects vs permission (contested feature removed)

Permission pillar recomputed without `prm_contested_total`. Moratorium flags may come from the same news sources as the contested list, so this is a soft check.

- Counties with `lbl_contested_n` > 0: **45**, mean permission (no contested feature) = **0.761**
- All others: **2436**, mean = **0.808**
- Contested lower than others: **yes** (delta -0.047)
- Share of contested counties in the riskiest permission quartile: **60.0%**

## 3. Exclusion recall

**(a) Frontier AI sites only (`lbl_frontier_ai_dc_n` > 0):** 6 / 53 removed (**11.3%**)
  - Protected land: 0
  - Active county moratorium: 0
  - Statewide moratorium: 1
  - Too little candidate land: 0
  - Far from the grid: 1
  - Extreme hurricane: 0
  - Extreme coastal flood: 1
  - Extreme water stress: 3

**(b) All DC counties (existing or frontier):** 61 / 269 removed (**22.7%**)
  - Protected land: 0
  - Active county moratorium: 1
  - Statewide moratorium: 10
  - Too little candidate land: 15
  - Far from the grid: 1
  - Extreme hurricane: 15
  - Extreme coastal flood: 9
  - Extreme water stress: 21

**(c) All DC counties grouped by rule type** (a county can count in more than one group)
- feasibility (land, grid, protected): **16** of 269 DC counties (5.9%)
  - Too little candidate land: 15
  - Far from the grid: 1
  - Protected land: 0
- sustainability/risk (water, hurricane, coastal flood): **42** of 269 DC counties (15.6%)
  - Extreme water stress: 21
  - Extreme hurricane: 15
  - Extreme coastal flood: 9
- policy (moratoria): **11** of 269 DC counties (4.1%)
  - Active county moratorium: 1
  - Statewide moratorium: 10

Counties removed by **too little candidate land** (51), with `cand_land_km2`:

```
 fips                county state  cand_land_km2
51610     Falls Church city    VA          0.000
51600          Fairfax city    VA          0.000
51013      Arlington County    VA          0.001
36061       New York County    NY          0.012
51510       Alexandria city    VA          0.012
51540  Charlottesville city    VA          0.027
51685    Manassas Park city    VA          0.040
51570 Colonial Heights city    VA          0.043
51678        Lexington city    VA          0.063
51670         Hopewell city    VA          0.076
51830     Williamsburg city    VA          0.098
11001  District of Columbia    DC          0.129
51735         Poquoson city    VA          0.186
51630   Fredericksburg city    VA          0.271
34013          Essex County    NJ          0.292
29510        St. Louis city    MO          0.355
51710          Norfolk city    VA          0.409
51690     Martinsville city    VA          0.444
51683         Manassas city    VA          0.537
51760         Richmond city    VA          0.542
34039          Union County    NJ          0.558
24510        Baltimore city    MD          0.609
51775            Salem city    VA          0.638
34017         Hudson County    NJ          0.755
51580        Covington city    VA          0.788
36005          Bronx County    NY          0.856
51840       Winchester city    VA          0.982
51720           Norton city    VA          1.005
06075  San Francisco County    CA          1.258
51530      Buena Vista city    VA          1.460
34003         Bergen County    NJ          1.544
51750          Radford city    VA          1.894
51770          Roanoke city    VA          1.920
51595          Emporia city    VA          1.987
51650          Hampton city    VA          2.028
51520          Bristol city    VA          2.050
25025        Suffolk County    MA          2.053
42101   Philadelphia County    PA          2.267
22071        Orleans Parish    LA          2.809
51700     Newport News city    VA          2.843
51640            Galax city    VA          3.006
44001        Bristol County    RI          3.088
51660     Harrisonburg city    VA          3.389
12087         Monroe County    FL          3.632
36047          Kings County    NY          3.671
51730       Petersburg city    VA          3.673
51620         Franklin city    VA          4.017
34031        Passaic County    NJ          4.174
36087       Rockland County    NY          4.803
36081         Queens County    NY          4.936
51820       Waynesboro city    VA          4.961
```

## 4. Top 10 by persona

### base

```
 rank             county state  final_score  power  carbon  water  permission  hazard  land  cobenefit
    1     Cowlitz County    WA        0.675  0.668   0.595  0.843       0.811   0.697 0.733      0.419
    2     Whatcom County    WA        0.670  0.618   0.672  0.846       0.835   0.718 0.751      0.335
    3      Benton County    WA        0.666  0.643   0.771  0.762       0.790   0.640 0.680      0.355
    4        Linn County    IA        0.665  0.762   0.562  0.728       0.790   0.648 0.729      0.418
    5       Mayes County    OK        0.664  0.834   0.642  0.682       0.855   0.390 0.752      0.423
    6      Pierce County    WA        0.662  0.763   0.639  0.880       0.804   0.726 0.802      0.190
    7 Rock Island County    IL        0.661  0.800   0.593  0.670       0.712   0.762 0.839      0.315
    8      Dallas County    TX        0.660  0.858   0.662  0.608       0.701   0.529 0.820      0.383
    9     Calhoun County    MI        0.653  0.659   0.569  0.635       0.790   0.748 0.691      0.527
   10   Multnomah County    OR        0.652  0.718   0.717  0.880       0.748   0.753 0.716      0.180
```

### legacy

```
 rank             county state  final_score  power  carbon  water  permission  hazard  land  cobenefit
    1  Montgomery County    PA        0.825  0.882   0.365  0.584       0.658   0.726 0.803      0.207
    2        Cook County    IL        0.823  0.867   0.418  0.534       0.524   0.742 0.809      0.599
    3      DuPage County    IL        0.813  0.855   0.305  0.536       0.620   0.748 0.788      0.413
    4 Rock Island County    IL        0.811  0.815   0.593  0.670       0.712   0.762 0.839      0.315
    5      Fulton County    GA        0.809  0.884   0.494  0.541       0.790   0.654 0.803      0.130
    6     Loudoun County    VA        0.809  0.884   0.350  0.823       0.549   0.715 0.757      0.085
    7        Will County    IL        0.807  0.859   0.499  0.533       0.595   0.714 0.790      0.450
    8     Chester County    PA        0.805  0.823   0.339  0.567       0.665   0.758 0.808      0.117
    9    Cuyahoga County    OH        0.799  0.842   0.259  0.680       0.753   0.789 0.739      0.266
   10      Pierce County    WA        0.795  0.819   0.639  0.880       0.804   0.726 0.802      0.190
```

### carbon-first

```
 rank           county state  final_score  power  carbon  water  permission  hazard  land  cobenefit
    1    Benton County    WA        0.704  0.643   0.771  0.762       0.790   0.640 0.680      0.355
    2 Multnomah County    OR        0.704  0.718   0.717  0.880       0.748   0.753 0.716      0.180
    3   Whatcom County    WA        0.694  0.618   0.672  0.846       0.835   0.718 0.751      0.335
    4    Pierce County    WA        0.690  0.763   0.639  0.880       0.804   0.726 0.802      0.190
    5 Clackamas County    OR        0.688  0.718   0.684  0.851       0.789   0.688 0.761      0.185
    6     Clark County    WA        0.682  0.710   0.644  0.878       0.769   0.791 0.759      0.175
    7      Lane County    OR        0.682  0.613   0.718  0.821       0.833   0.698 0.686      0.198
    8    Yakima County    WA        0.680  0.644   0.727  0.796       0.742   0.615 0.755      0.246
    9      King County    WA        0.679  0.723   0.658  0.816       0.742   0.758 0.833      0.183
   10  Kittitas County    WA        0.677  0.690   0.750  0.735       0.866   0.558 0.807      0.167
```

### cost-first

```
 rank               county state  final_score  power  carbon  water  permission  hazard  land  cobenefit
    1   Rock Island County    IL        0.728  0.800   0.593  0.670       0.712   0.762 0.839      0.315
    2        Pierce County    WA        0.723  0.763   0.639  0.880       0.804   0.726 0.802      0.190
    3        Dallas County    TX        0.721  0.858   0.662  0.608       0.701   0.529 0.820      0.383
    4         Wayne County    MI        0.719  0.802   0.503  0.820       0.618   0.740 0.791      0.362
    5         Mayes County    OK        0.714  0.834   0.642  0.682       0.855   0.390 0.752      0.423
    6          Linn County    IA        0.713  0.762   0.562  0.728       0.790   0.648 0.729      0.418
    7         Lucas County    OH        0.712  0.794   0.266  0.836       0.731   0.720 0.719      0.509
    8 Pottawattamie County    IA        0.711  0.826   0.553  0.649       0.789   0.603 0.757      0.277
    9       Dauphin County    PA        0.710  0.802   0.350  0.766       0.773   0.659 0.741      0.372
   10         Scott County    IA        0.707  0.752   0.465  0.794       0.781   0.691 0.815      0.262
```

### community-first

```
 rank           county state  final_score  power  carbon  water  permission  hazard  land  cobenefit
    1   Cowlitz County    WA        0.649  0.668   0.595  0.843       0.811   0.697 0.733      0.419
    2   Calhoun County    MI        0.645  0.659   0.569  0.635       0.790   0.748 0.691      0.527
    3      Linn County    IA        0.634  0.762   0.562  0.728       0.790   0.648 0.729      0.418
    4 Muscatine County    IA        0.632  0.710   0.486  0.698       0.808   0.669 0.740      0.480
    5     Macon County    IL        0.632  0.698   0.529  0.702       0.684   0.655 0.608      0.567
    6   Whatcom County    WA        0.632  0.618   0.672  0.846       0.835   0.718 0.751      0.335
    7     Huron County    MI        0.630  0.769   0.596  0.621       0.776   0.767 0.416      0.467
    8     Mayes County    OK        0.629  0.834   0.642  0.682       0.855   0.390 0.752      0.423
    9    Benton County    WA        0.629  0.643   0.771  0.762       0.790   0.640 0.680      0.355
   10  Woodbury County    IA        0.622  0.777   0.443  0.786       0.789   0.567 0.648      0.464
```

## Manual adjustments

These are judgment values, not published interconnection waits or statutory county tax codes.

- **PNW time-to-power = 6 years**, `basis=constrained_judgment` for every county with `crb_cambium_gea` == `NorthernGrid_West` (**75** rows in this table).
  Source: BPA load requests ~65 GW vs 11-12 GW typical; Cowlitz PUD says BPA cannot process its transmission queue in time; no published wait time. Judgment value between national 4 and Dominion 7. Applied to every county in Cambium GEA NorthernGrid_West (WA/OR), not just the original eight utilities.
- **Large-load industrial price = 7.75 ¢/kWh** (national median) on the same counties. Applied to the power-pillar price feature and to `energy_cost_musd` (electricity only; not an embedded tariff).
- **Tax status overrides** (`not_eligible` → 0.2): 53015=not_eligible, 53011=not_eligible.
  Source: Washington's data center sales-tax exemption is site- and qualification-based. Cowlitz (53015) and Clark (53011) are treated as not_eligible (score 0.2), not unknown (0.5).
- Sensitivities (not the base table): PNW wait at 5 and 7 years; replace industrial price scores for the same region with the national-median price score.

