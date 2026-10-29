"""
Feature builder shared by training (history) and the live app.

Using the SAME function for both is important: the model must see
features calculated exactly the way it was trained on.

Input: a daily table with columns
    date       (YYYY-MM-DD)
    rain_mean  mean rain across the upstream points that day (mm)
    rain_max   rain at the wettest upstream point that day (mm)

Output: one row per day with these model features.
Only rain and season are used - no river-flow input - because small
seasonal streams (like the Makueni demo crossing) have no flow data.
"""

import pandas as pd

FEATURES = [
    "rain_1d",       # upstream rain today (mean of points)
    "rain_3d",       # last 3 days
    "rain_7d",       # last 7 days
    "rain_14d",      # last 14 days: how wet the ground already is
    "max_point_3d",  # wettest single upstream point, last 3 days
    "month",
    "long_rains",    # March-May
    "short_rains",   # October-December
]

FEATURE_LABELS = {
    "rain_1d": "upstream rain today",
    "rain_3d": "upstream rain in the last 3 days",
    "rain_7d": "upstream rain in the last 7 days",
    "rain_14d": "upstream rain in the last 14 days (wet ground)",
    "max_point_3d": "rain at the wettest upstream point (3 days)",
    "month": "time of year",
    "long_rains": "long rains season",
    "short_rains": "short rains season",
}


def make_features(daily: pd.DataFrame) -> pd.DataFrame:
    df = daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["rain_mean"] = df["rain_mean"].fillna(0.0)
    df["rain_max"] = df["rain_max"].fillna(0.0)

    df["rain_1d"] = df["rain_mean"]
    df["rain_3d"] = df["rain_mean"].rolling(3, min_periods=1).sum()
    df["rain_7d"] = df["rain_mean"].rolling(7, min_periods=1).sum()
    df["rain_14d"] = df["rain_mean"].rolling(14, min_periods=1).sum()
    df["max_point_3d"] = df["rain_max"].rolling(3, min_periods=1).sum()
    df["month"] = df["date"].dt.month
    df["long_rains"] = df["month"].isin([3, 4, 5]).astype(int)
    df["short_rains"] = df["month"].isin([10, 11, 12]).astype(int)
    return df
