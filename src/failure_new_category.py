import numpy as np
import pandas as pd

from db import get_engine

LAUNCH_POSITIONS = [20, 40, 60]   # pretend a category launches at these week numbers
WEEKS_KNOWN = [0, 1, 2, 4, 8]     # how many weeks of own data we have
PRIOR_WEIGHT = 4                  # how much we trust the "typical category" guess

engine = get_engine()
df = pd.read_sql(
    "SELECT category, week, units FROM features.weekly_category_units",
    engine, parse_dates=["week"],
)
wide = df.pivot(index="week", columns="category", values="units").sort_index()

rows = []
for launch in LAUNCH_POSITIONS:
    for cat in wide.columns:
        others = wide.drop(columns=cat)
        for n in WEEKS_KNOWN:
            t = launch + n                      # the week we must forecast
            actual = wide.iloc[t][cat]
            ref = others.iloc[max(0, t - 8):t]  # other categories, 8 weeks before t
            mean_all = ref.values.mean()        # average over ALL categories
            typical = ref.mean().median()       # a typical (median) category
            own = wide.iloc[launch:t][cat]      # weeks since launch (n weeks)

            if n == 0:
                own_avg = typical               # no data yet: fall back to typical
                shrunk = typical
            else:
                own_avg = own.mean()
                shrunk = (n * own.mean() + PRIOR_WEIGHT * typical) / (n + PRIOR_WEIGHT)

            forecasts = {
                "zero": 0.0,
                "mean_all_categories": mean_all,
                "typical_category": typical,
                "own_average": own_avg,
                "own_plus_typical": shrunk,
            }
            for name, f in forecasts.items():
                rows.append({"weeks_known": n, "method": name,
                             "actual": actual, "abs_error": abs(f - actual)})

res = pd.DataFrame(rows)
g = res.groupby(["weeks_known", "method"]).agg(
    MAE=("abs_error", "mean"),
    err=("abs_error", "sum"),
    act=("actual", "sum"),
)
g["WAPE"] = g["err"] / g["act"]

order = ["zero", "mean_all_categories", "typical_category",
         "own_average", "own_plus_typical"]
print(f"New-category test: {len(LAUNCH_POSITIONS)} pretend launches x "
      f"{wide.shape[1]} categories")
print()
print("WAPE by weeks of own data (lower is better):")
print(g["WAPE"].unstack("method")[order].round(3).to_string())
print()
print("MAE in units per week (lower is better):")
print(g["MAE"].unstack("method")[order].round(2).to_string())