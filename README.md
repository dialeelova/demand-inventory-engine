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

You need Python 3, PostgreSQL and a free Kaggle account (to download the data). The commands below are for Linux or a GitHub Codespace.

**Step 1. Download the code and install the libraries.**

```
git clone https://github.com/dialeelova/demand-inventory-engine.git
cd demand-inventory-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Step 2. Create the database.**

```
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER demo WITH PASSWORD 'demo';"
sudo -u postgres createdb -O demo olist
```

**Step 3. Add the data.** Download the dataset from the Kaggle link above, unzip it, and put the CSV files into a folder named `data/raw/`.

**Step 4. Run the pipeline.** Run these commands one after another, in this order.

```
python src/load_raw.py
python src/quality_checks.py
python src/build_clean.py
python src/build_weekly.py
python src/baseline.py
python src/model.py
python src/blend.py
```

**Step 5. Check the result.** The last command prints a table comparing the forecasting methods. The row `blend` should show an error (WAPE) of about 0.259 for all categories.

The remaining scripts in `src/` run the order-quantity test, the charts and the failure tests.