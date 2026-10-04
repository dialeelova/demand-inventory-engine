from functools import reduce

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from db import get_engine

TEST_START, TEST_END = "2017-10-30", "2017-12-25"
BF_WEEK = pd.Timestamp("2017-11-20")
UPLIFTS = [1.0, 1.5, 2.0, 2.5]   # manual multipliers for the Black Friday week

engine = get_engine()
df = pd.read_sql(
    "SELECT category, week, units FROM features.weekly_category_units",
    engine, parse_dates=["week"],
)
wide = df.pivot(index="week", columns="category", values="units").sort_index()

hints = {
    "lag1": wide.shift(1),
    "lag2": wide.shift(2),
    "lag3": wide.shift(3),
    "lag4": wide.shift(4),
    "avg4": wide.shift(1).rolling(4).mean(),
    "med4": wide.shift(1).rolling(4).median(),
    "avg8": wide.shift(1).rolling(8).mean(),
    "size": wide.shift(1).expanding().mean(),
    "buf": wide.shift(1).rolling(8).std(),
    "actual": wide,
}


def to_long(frame, name):
    return frame.melt(ignore_index=False, var_name="category",
                      value_name=name).reset_index()


data = reduce(lambda a, b: a.merge(b, on=["week", "category"]),
              [to_long(f, n) for n, f in hints.items()]).dropna()
FEATURES = ["lag1", "lag2", "lag3", "lag4", "avg4", "avg8", "size"]

weeks = wide.index[(wide.index >= TEST_START) & (wide.index <= TEST_END)]
rows = []
for week in weeks:
    train = data[data["week"] < week]
    test = data[data["week"] == week]
    model = HistGradientBoostingRegressor(
        loss="poisson", max_iter=200, learning_rate=0.05, random_state=0)
    model.fit(train[FEATURES], train["actual"])
    boost = model.predict(test[FEATURES]).clip(min=0)

    blend = (test["lag1"].values + test["avg4"].values + boost) / 3
    blend_med = (test["lag1"].values + test["med4"].values + boost) / 3
    actual = test["actual"].values
    buf = test["buf"].values

    row = {"week": week.date(), "units": int(actual.sum()),
           "WAPE_blend": np.abs(blend - actual).sum() / actual.sum(),
           "WAPE_median_blend": np.abs(blend_med - actual).sum() / actual.sum(),
           "fill_blend": np.minimum(blend + buf, actual).sum() / actual.sum(),
           "fill_median": np.minimum(blend_med + buf, actual).sum() / actual.sum()}
    if week == BF_WEEK:
        row["needed_multiplier"] = actual.sum() / blend.sum()
        for u in UPLIFTS:
            order = blend * u + buf
            row[f"fill_x{u}"] = np.minimum(order, actual).sum() / actual.sum()
    rows.append(row)

out = pd.DataFrame(rows).set_index("week")
print("Fix 1: median instead of mean in the blend (k = 1 order rule):")
print(out[["units", "WAPE_blend", "WAPE_median_blend",
           "fill_blend", "fill_median"]].round(3).to_string())

print()
print("Fix 2: manual uplift on the Black Friday week only (2017-11-20):")
bf = out.loc[BF_WEEK.date()]
print(f"  multiplier that would have been exactly right: {bf['needed_multiplier']:.2f}")
for u in UPLIFTS:
    print(f"  uplift x{u}: fill rate {bf[f'fill_x{u}']:.3f}")