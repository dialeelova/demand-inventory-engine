# Demand and Inventory Decision Engine

## What this project is

Every online shop faces the same question: how many units of each product should be kept in stock? If the shop orders too little, customers find empty shelves and the shop loses sales. If it orders too much, money is tied up in goods that do not sell.

This project builds a small decision system for that question. It uses real order data from Olist, a Brazilian online marketplace (about 100,000 orders from January 2017 to August 2018). The system looks at what was sold in the past, estimates how much will be sold next week, and suggests how many units to order.

## What it does

1. **Prepares the data.** It loads the raw files into a PostgreSQL database, checks them for errors (for example, orders marked as delivered that have no delivery date) and builds a clean version for analysis.
2. **Forecasts demand.** It predicts the number of units sold next week for each of 74 product categories, and compares several forecasting methods using a fair test on the most recent 20 weeks.
3. **Recommends order quantities.** The suggested order is the forecast plus a safety buffer. A larger buffer means fewer empty shelves but more unsold stock.
4. **Tests the advice on past data.** It replays past weeks and measures how much demand would have been served and how much stock would have been left over.
5. **Tests where it fails.** It is deliberately exposed to a holiday sales spike, a sudden drop in demand, a new category without history and a week of missing data.

Data: [Olist e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Tools: Python, SQL, PostgreSQL, pandas, scikit-learn.

## Main findings

- Forecasting single products does not work with this data. Most products sell only once or twice, so no method beat predicting zero.
- Forecasting by category works better. The average of three simple forecasts was slightly better than any single one, including gradient boosting (error 0.259 against 0.275 for the best single method).
- The size of the safety buffer changed the results more than the choice of forecasting method.
- Black Friday caused the largest failure: in that week the order rule served only 46% of demand.

![Weekly units, top 4 categories](docs/charts/weekly_units_top_categories.png)

## More detail

- [Full report with all results and failure tests](docs/full_report.md)
- [Decisions and the reasons behind them](docs/decisions.md)

## How to run it

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up PostgreSQL with a database `olist` (user and password `demo`)
4. Download the [data from Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and put the CSV files in `data/raw/`
5. Load and clean the data: `python src/load_raw.py` then `python src/build_clean.py`
6. Build the weekly table: `python src/build_weekly.py`
7. Run the forecasts: `python src/baseline.py`, `python src/model.py`, then `python src/blend.py`