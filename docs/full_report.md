# Full report

This is the long version of the project. The short version is in the [README](../README.md). The reasons behind each choice are in [decisions.md](decisions.md).

## 📦 The data

The project uses the Olist dataset: about 99,000 orders, 112,000 order items and 33,000 products from a Brazilian online marketplace. The data runs from late 2016 to October 2018, but the first and last months have almost no orders, so only January 2017 to August 2018 is used. Cancelled and unavailable orders are dropped, because they are not real demand.

The CSV files are loaded into PostgreSQL exactly as they are, and a separate clean copy is built from them. The original data is never changed, and everything can be rebuilt by rerunning the scripts.

Seven automatic checks found three real problems: 8 orders marked "delivered" with no delivery date, 610 products with no category, and 2 products with no weight. Products without a category are labelled `unknown` in the clean layer.

The last week of the data turned out to be incomplete. Daily sales fell from about 300 units to 16 over a few days, which looked like the dataset fading out and not like customers disappearing. The problem showed up because every model failed in the same week, which led to a look at the daily numbers. After that week was cut, all results were rerun.

## 📈 What the sales look like

Revenue grew a lot during 2017, from about 120k in January to about 660k in October, and then stayed between 850k and 990k in 2018. November 2017 (Black Friday) was about 52% higher than October. Delivery times went up around the holidays and came down a lot in 2018.

![Revenue per month](charts/revenue_per_month.png)

The weekly chart shows the same Black Friday spike in all four of the biggest categories at once.

![Weekly units, top 4 categories](charts/weekly_units_top_categories.png)

![Average delivery time per month](charts/delivery_time_per_month.png)

SQL queries also showed that small categories like food, construction tools and art have the most unstable weekly sales, and that no single seller brings more than 1.7% of revenue.

## 🔮 Forecasting

Most products sell only once or twice, and 55% were sold exactly once. Forecasting was tried first at the product level and then at the category level, where there is enough data (74 categories, 85 full weeks).

### Products

Only 309 products sold often enough to try (in at least 15 of the training weeks), and together they cover just 11% of units. Four methods were compared against a "predict zero every week" method:

| Method | Error (WAPE) |
|---|---|
| last week | 0.981 |
| average of 4 weeks | 0.999 |
| always zero | 1.000 |
| average of 12 weeks | 1.180 |
| category forecast times product share | 1.655 |

Nothing beat predicting zero by more than 2%. Demand for a single product is mostly zero with an occasional 1 or 2, so a forecast of "0.4 units" is wrong almost every week. Product-level forecasts were dropped in favour of categories.

### Categories

The category forecasts were tested with a backtest on the last 20 weeks (2018-04-02 to 2018-08-13). For each week, a model could only see earlier weeks and had to forecast that one week. The metric is WAPE (total error divided by total units sold), because 31% of the category-weeks have zero sales, which makes percentage errors unusable.

| Model | Error, all categories | Error, 10 biggest |
|---|---|---|
| last week | 0.275 | 0.218 |
| average of last 4 weeks | 0.279 | 0.236 |
| gradient boosting | 0.287 | 0.240 |
| blend of the three | 0.259 | 0.211 |

The boosting model did slightly worse than the simple methods. A likely reason is that 85 weeks of noisy data is too little for it to learn more than "next week looks like recent weeks", but this was not tested.

Averaging the three forecasts gave the best result. It beat the last-week forecast in 15 of the 20 weeks, so the gain is not just a few lucky weeks. It is still a small gain on a short test, so it should not be read as a big win.

## 🛒 From forecast to order

The rule is simple: order the forecast plus a safety buffer. The buffer is `k` times how much the category's sales swung in the previous 8 weeks. The same 20 weeks were replayed to see what different values of `k` would have done.

| k | Demand served | Categories that ran out | Ordered units left unsold |
|---|---|---|---|
| 0 | 86.9% | 41.5% | 12.9% |
| 1 | 95.7% | 18.6% | 24.9% |
| 3 | 99.5% | 3.6% | 45.5% |

More buffer means fewer empty shelves and more unsold stock, and the right `k` depends on which problem costs the shop more. The same rule was also run with each of the four forecasts. At `k = 1` they all served between 94.6% and 95.7% of demand, so the choice of forecast mattered much less than the size of the buffer.

## 💥 Where it breaks

Four situations that a real shop would run into were tested.

**🛍️ Black Friday.** In the week of 2017-11-20, sales were 3,490 units against 1,487 the week before, about 2.3 times more. Every model missed it (error about 0.6, normally 0.2 to 0.3), and the order rule served only 46.3% of demand. Two fixes were tried. Using the median instead of the average helped a little in the weeks after the spike, but not in the spike itself. A manual multiplier on that week worked (a factor of 2.55 would have been exactly right), but that number is only known after the fact and is tuned on one event. With only one Black Friday in the data, a model cannot learn it. A real system would need a holiday calendar and a manager's judgment.

**📉 A sudden drop.** In the week of 2018-05-21, sales fell to 1,100 from 2,130. The cause is unknown and has not been confirmed. The order rule never ran out (99.5% served), but 57.8% of the ordered units were left over, compared with about 25% normally. It took about two weeks to return to normal. This is the opposite problem to Black Friday: the shelves stay full, but money sits in stock.

**🆕 A new category.** Each category was treated as if it had just launched, with its history hidden. With no data, every method was within 4% of predicting zero. After one week of its own sales, the error fell from 0.96 to 0.25. The practical answer is a small fixed first order, then switching to the category's own sales after one week. This test used established categories, so a real launch would probably be harder.

**🕳️ A missing week.** One full week was removed at 61 different points. If the gap is recorded as zero sales, the 4-week average gets worse (0.263 to 0.371) and a last-week forecast predicts nothing at all. Filling the gap with the previous week or a 4-week average brings the error back to about 0.286. Finding incomplete weeks matters more than the choice of forecast method, which is the same problem that appeared with the last week of the data.

## ⚠️ Limits

- `k` was chosen and tested on the same 20 weeks. A proper version would choose it on older weeks.
- The simulation has no delivery delay and does not carry unsold stock into the next week, so leftover stock is overstated.
- Leftover stock was not measured for the Black Friday multipliers.
- The blend's advantage over the single models is small, and the test covers only 20 weeks.
- The new-category test is a simulation on established categories.
- The cause of the May 2018 drop is not confirmed.