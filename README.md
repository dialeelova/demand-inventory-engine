# Demand and Inventory Decision Engine

An online shop has to decide how much of each product to keep in stock. Too little, and customers can't buy. Too much, and money sits unsold on shelves.

This project tackles that decision using real order data from a Brazilian online marketplace (about 100,000 orders over 20 months). It does four things:

1. Loads and cleans the raw data in PostgreSQL, with automatic checks for bad rows.
2. Forecasts how many units each product category will sell next week.
3. Turns the forecast into an order quantity: the forecast plus a safety buffer.
4. Replays past weeks to see how often that advice would have avoided empty shelves and wasted stock, then breaks it on purpose to see where it fails.

Data: [Olist e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Stack: Python, SQL, PostgreSQL, pandas, scikit-learn.

## What I found

- Forecasting single products doesn't work here. Most products sell once or twice, so no method beat predicting zero.
- Forecasting categories works better. Averaging three simple forecasts was slightly better than any single one, including gradient boosting (error 0.259 vs 0.275 for the best single model).
- The safety buffer in the order rule mattered more than the forecast model.
- Black Friday broke everything: the order rule served only 46% of demand that week.

![Weekly units, top 4 categories](docs/charts/weekly_units_top_categories.png)

## More detail

- [Full report with all results and failure tests](docs/full_report.md)
- [Decisions and why I made them](docs/decisions.md)

## Run it
 
pip install -r requirements.txt
python src/load_raw.py
python src/build_clean.py
python src/build_weekly.py
python src/blend.py
 

Needs PostgreSQL and the Olist CSVs in `data/raw/`.