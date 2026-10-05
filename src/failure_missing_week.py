import numpy as np
import pandas as pd

from db import get_engine

# Weeks that are already known shocks. We keep them out of this test so that
# the missing-data effect is not mixed up with Black Friday or the May drop.
SHOCK_WEEKS = [pd.Timestamp("2017-11-20"), pd.Timestamp("2018-05-21")]

engine = get_engine()
df = pd.read_sql(
    "SELECT category, week, units FROM features.weekly_category_units",
    engine, parse_dates=["week"],
)
wide = df.pivot(index="week", columns="category", values="units").sort_index()
wide = wide.astype(float)
shock_pos = [wide.index.get_loc(w) for w in SHOCK_WEEKS]

HANDLING = ["no_outage", "missing_as_zero", "fill_previous_week", "fill_avg_4_weeks"]
rows = []

for m in range(8, len(wide) - 2):          # m = the week with the outage
    # skip positions where a known shock is close by
    if any(m - 4 <= s <= m + 2 for s in shock_pos):
        continue

    true_m = wide.iloc[m]
    fill_value = {
        "no_outage": true_m,
        "missing_as_zero": true_m * 0,
        "fill_previous_week": wide.iloc[m - 1],
        "fill_avg_4_weeks": wide.iloc[m - 4:m].mean(),
    }

    for h in HANDLING:
        series = wide.iloc[:m + 2].copy()   # weeks up to m+1, all we could know
        series.iloc[m] = fill_value[h]

        # forecast week m+1 (seen: up to m) and week m+2 (seen: up to m+1)
        for ahead, target in ((1, m + 1), (2, m + 2)):
            actual = wide.iloc[target]
            known = series.iloc[:target]
            forecasts = {
                "last_week": known.iloc[-1],
                "avg_4_weeks": known.iloc[-4:].mean(),
            }
            for name, f in forecasts.items():
                rows.append({
                    "handling": h, "weeks_after_outage": ahead, "method": name,
                    "abs_error": (f - actual).abs().sum(),
                    "actual": actual.sum(),
                })

res = pd.DataFrame(rows)
g = res.groupby(["handling", "weeks_after_outage", "method"]).agg(
    err=("abs_error", "sum"), act=("actual", "sum"))
g["WAPE"] = g["err"] / g["act"]

n_pos = res.groupby("handling").size().iloc[0] // 4
print(f"Outage positions tested: {n_pos} (weeks near known shocks skipped)")
print()
for ahead in (1, 2):
    print(f"WAPE for the forecast {ahead} week(s) after the outage (lower is better):")
    table = (g["WAPE"].xs(ahead, level="weeks_after_outage")
             .unstack("method").reindex(HANDLING))
    print(table.round(3).to_string())
    print()