# Demand and Inventory Decision Engine

A system that looks at past orders of an online shop, forecasts weekly demand per product category, turns the forecast into "order this many units", and tests that advice on past data. It also documents where it breaks.

Data: [Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (99,441 orders, 112,650 order items, 32,951 products).
Stack: Python, SQL, PostgreSQL, pandas, scikit-learn, matplotlib, Git.

## The short story

1. Forecasting single products does not work here. Only 309 of 32,197 products sold often enough, and they cover 11% of units. No method beat "always predict zero" by more than 2%.
2. So I forecast at category level (74 categories, weekly). A blend of three simple forecasts was slightly better than any single model, including a gradient boosting model.
3. The safety buffer in the order rule mattered more than the choice of forecast model.
4. I broke the system on purpose four ways (holiday spike, sudden drop, new category, missing data) and measured each one.

## Pipeline

```
CSV files -> raw tables -> quality checks -> clean tables -> weekly table -> forecasts -> order rule -> failure tests
```

- `raw` layer: the CSV files loaded as they are. The loading script can be rerun safely and never creates duplicates.
- 7 automated quality checks found 3 real problems: 8 "delivered" orders with no delivery date, 610 products with no category, 2 products with no weight.
- `clean` layer: only real sales (no cancelled or unavailable orders), only January 2017 to August 2018, categories translated to English.
- `features` layer: units per category per week (74 categories x 85 full weeks, zero-filled; 110,429 units, checked against the clean layer).

Decisions and their reasons are in [docs/decisions.md](docs/decisions.md). Business findings are in [docs/findings.md](docs/findings.md).

## Business findings

- Monthly revenue grew from about 120k (Jan 2017) to about 660k (Oct 2017), then stayed around 850k to 990k in 2018.
- Black Friday 2017: revenue was about 52% higher than the month before.
- Niche categories (food, construction tools, art) have the most unstable weekly demand. No single seller has more than 1.7% of revenue.

![Revenue per month](docs/charts/revenue_per_month.png)
![Weekly units, top 4 categories](docs/charts/weekly_units_top_categories.png)
![Average delivery time per month](docs/charts/delivery_time_per_month.png)

## Forecasting results

Backtest: the last 20 weeks (2018-04-02 to 2018-08-13). For each week, models trained only on earlier weeks and forecast one week ahead. The metric is WAPE (total error divided by total units sold; lower is better). MAPE was not used because 31% of the category-weeks have zero sales.

| Model | WAPE, all 74 categories | WAPE, 10 biggest categories |
|---|---|---|
| last week | 0.275 | 0.218 |
| average of last 4 weeks | 0.279 | 0.236 |
| gradient boosting (lag features) | 0.287 | 0.240 |
| **blend (average of the three)** | **0.259** | **0.211** |

- The blend beat the last-week forecast in 15 of 20 weeks, but the gain is small and the sample is only 20 weeks.
- The boosting model alone did not beat the simple baselines. With about 85 weeks of history, weekly sales are too noisy for a model to learn much more than "next week looks like recent weeks".

### Single products (failed)

309 products had enough history. Product-level WAPE: last week 0.981, 4-week average 0.999, always zero 1.000, 12-week average 1.180, category share 1.655. Demand is mostly 0 with an occasional 1 or 2, so point forecasts are not useful.

## From forecast to order

Rule: `order = forecast + k x (standard deviation of the previous 8 weeks)`. Replayed on the same 20 weeks.

| k | Fill rate (share of demand served) | Category-weeks with a stockout | Ordered units left unsold |
|---|---|---|---|
| 0 | 86.9% | 41.5% | 12.9% |
| 1 | 95.7% | 18.6% | 24.9% |
| 3 | 99.5% | 3.6% | 45.5% |

At k = 1 the four forecast models were within one point of each other (fill rate 94.6% to 95.7%). The blend reached 95.7% with 24.9% leftover; the last-week forecast reached 95.1% with 24.9% leftover. The size of the safety buffer changed the result far more than the forecast model.

## Failure report

| Test | What happened | Result |
|---|---|---|
| Black Friday 2017 (week of 2017-11-20) | Units were 3,490 vs 1,487 the week before (2.3x). All models missed it. | WAPE about 0.6 (normal 0.2 to 0.3). The order rule served only 46.3% of demand, and 57% of categories ran out. |
| Fix: median instead of mean | Less pollution from the spike in later weeks. | Small gain after the spike (for example 0.220 vs 0.236), none in the spike week. |
| Fix: manual holiday multiplier | A multiplier of 2.55 would have been exactly right. | Fill rate at x1.5 / x2.0 / x2.5: 64% / 80% / 91.5%. Tuned on one event and known only afterwards, so it is a manager's rule, not a model result. |
| Demand drop (week of 2018-05-21) | Units fell to 1,100 from 2,130. Cause not confirmed. | WAPE 0.954. Shelves stayed full (99.5% fill rate), but 57.8% of ordered units were left over. Back to normal in about 2 weeks. |
| New category, no history | Simulated launches of established categories. | With 0 weeks of data every method was within 4% of predicting zero (WAPE 0.964). After 1 week of own data: 0.248. |
| Missing week of data | One full week recorded as zero sales, tested at 61 positions. | A 4-week average went from 0.263 to 0.371, and a last-week forecast predicted nothing (1.000). Filling the gap with the previous week or a 4-week average brought it back to about 0.286. |

An incomplete week at the end of the data (2018-08-20, sales fading to 16 units a day) made every model look worse than it was. I found it by checking daily sales, cut it from the data, and reran all results.

## What did not work, and limits

- Product-level forecasting failed (see above). Individual products need a stock rule, not a point forecast.
- The boosting model did not beat the baselines on its own.
- The value of k was picked and tested on the same 20 weeks. A real system would choose it on older weeks.
- The order simulation has no delivery delay and does not carry unsold stock into the next week, so leftover stock is overstated.
- Only one Black Friday exists in the data, so a model cannot learn it.
- The new-category test uses established categories, so real launches would give higher errors.
- Leftover stock was not measured for the holiday multipliers.

## How to run it

Requires Python 3.14 and PostgreSQL 16 with a database `olist` and a user `demo` (see `src/db.py`). Put the Olist CSV files in `data/raw/`.

```
git clone https://github.com/dialeelova/demand-inventory-engine.git
cd demand-inventory-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/load_raw.py
python src/quality_checks.py
python src/build_clean.py
python src/build_weekly.py
python src/baseline.py
python src/model.py
python src/blend.py
python src/decision_layer.py
```

The other scripts in `src/` reproduce the exploration, charts, product-level experiment, policy comparison and failure tests.
