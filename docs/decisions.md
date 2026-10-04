# Project decisions

## Data scope
- Dataset: Olist Brazilian e-commerce (9 CSV files).
- Usable period: 2017-01-01 to 2018-08-31. Before and after that, order counts are near zero.
- Dropped orders with status `canceled` or `unavailable`. They are not real demand.
- Partial first and last weeks are dropped when building weekly data.
- `olist_geolocation_dataset.csv` (261,831 duplicate rows) is not used.

## Known data problems (quality checks must report these)
- 8 orders marked `delivered` have no delivery date.
- 610 products have no category, name, description or photo count.
- 2 products have no weight or size.

## Forecasting level
- 55% of products were sold only once. Only 286 products sold in 20+ weeks.
- Main forecast: weekly units per product category (71 categories).
- Second experiment: the 286 products with 20+ active weeks.
- Rare products: fallback to the category forecast.

## Known risks to test later
- Black Friday (Nov 2017) spike: 7,544 orders vs 4,631 the month before.
- Strong growth during 2017, so the past is not a stable guide to the future.
## Updates after exploring the weekly data
- There are 74 categories, not 71: 2 categories have no English translation, and `unknown` is the 74th.
- The last week of data (from 2018-08-20) is cut. Sales fade out to 16 units on 2018-08-29, so the data is incomplete.
- Weekly table: 85 full weeks (2017-01-02 to 2018-08-19), 74 categories.
- Metrics: MAE and WAPE. MAPE is not used because 31% of the cells are zero.
- Backtest: the last 20 weeks, one week ahead, training only on earlier weeks.
- Unexplained demand drop in the week of 2018-05-21 (about half of the previous week). All models fail there. The cause is not confirmed.

## Product-level experiment (result)
- 309 products had 15+ active training weeks. They cover only 11% of test-period units.
- Backtest WAPE: last_week 0.981, avg_4_weeks 0.999, always_zero 1.000, avg_12_weeks 1.180, category_share 1.655.
- No method beat "always predict zero" by more than 2%. Product-level point forecasts are not useful here.
- Decision: forecast at category level (blend model). Individual products get a stock rule, not a point forecast.

## Decision layer (result)
- Order rule: blend forecast + k x (std of the previous 8 weeks). Each week starts fresh, no carry-over stock, no delivery delay.
- k = 0: fill rate 86.9%, stockouts in 41.5% of category-weeks. k = 1: fill rate 95.7%, 24.9% of ordered units left over. k = 3: fill rate 99.5%, 45.5% left over.
- At k = 1 the four models are within 1 point of fill rate. The blend (95.7%) is slightly ahead of last_week (95.1%) with the same leftover stock. avg_4_weeks needs k = 1.25 and leaves 27.5% over.
- The safety buffer matters more than the choice of forecasting model.
- Limits: k was chosen on the same 20 weeks it was tested on, and leftover stock is overstated because it is not carried over.

## Failure test 1: Black Friday 2017 (result)
- Week of 2017-11-20: units 3,490 vs 1,487 the week before (2.3x). WAPE about 0.6 for all models (normal: 0.2 to 0.3).
- Order rule (blend + 1 buffer): fill rate 46.3%, stockouts in 57% of categories (normal: about 95%).
- last_week overreacts the week after (WAPE 0.534). avg_4_weeks stays polluted for weeks (WAPE 1.154 on 2017-12-18).
- The buffer (8-week std) is inflated after the spike, so ordering is probably too high then (not measured).
- Only one Black Friday in the data, so a model cannot learn it.

## Failure test 1 fixes (result)
- Median-of-4 in the blend: slightly better after the spike (WAPE 0.220 vs 0.236 on 2017-11-27, 0.659 vs 0.717 on 2017-12-18). No effect on the spike week (0.624).
- Manual uplift on 2017-11-20: the exact multiplier would have been 2.55. Fill rate at x1.0 / x1.5 / x2.0 / x2.5: 46% / 64% / 80% / 91.5%.
- The uplift is tuned on a single event and known only after the fact. Leftover stock at each multiplier was not measured. A real system needs a holiday calendar and manager judgment.
