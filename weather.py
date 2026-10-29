"""
Live upstream rainfall for a crossing, from the free Open-Meteo API.

get_upstream_rain(crossing) returns a dict:
    rain_3d_mm      3-day rain at the wettest upstream point (-1 if unavailable)
    features        model features for the surge predictor (None if unavailable)
    points          per-point details for the screen
    data_age_hours  0 when freshly fetched
    ok              True if at least one upstream point answered
    error           message when nothing could be fetched
"""

from datetime import date

import pandas as pd
import requests

from ml.features import FEATURES, make_features

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def _daily_rain(lat: float, lon: float) -> pd.Series:
    """Daily rain for the last 14 days up to today (mm)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "past_days": 14,
        "forecast_days": 1,
        "timezone": "Africa/Nairobi",
    }
    r = requests.get(WEATHER_URL, params=params, timeout=15)
    r.raise_for_status()
    d = r.json()["daily"]
    s = pd.Series(d["precipitation_sum"], index=d["time"], dtype="float")
    return s[s.index <= date.today().isoformat()].fillna(0.0)


def get_upstream_rain(crossing: dict) -> dict:
    series, points = {}, []
    for p in crossing["upstream_points"]:
        try:
            s = _daily_rain(p["lat"], p["lon"])
            series[p["name"]] = s
            points.append({"name": p["name"], "rain_3d_mm": round(float(s.tail(3).sum()), 1), "ok": True})
        except (requests.RequestException, KeyError, ValueError) as e:
            points.append({"name": p["name"], "rain_3d_mm": None, "ok": False, "error": str(e)[:120]})

    if not series:
        return {
            "rain_3d_mm": -1.0,
            "features": None,
            "points": points,
            "data_age_hours": 0.0,
            "ok": False,
            "error": "Could not reach the weather service.",
        }

    df = pd.DataFrame(series)
    daily = pd.DataFrame({
        "date": df.index,
        "rain_mean": df.mean(axis=1).values,
        "rain_max": df.max(axis=1).values,
    })
    today = make_features(daily).iloc[-1]
    features = {f: float(today[f]) for f in FEATURES}

    return {
        "rain_3d_mm": round(features["max_point_3d"], 1),  # wettest point: the cautious choice
        "features": features,
        "points": points,
        "data_age_hours": 0.0,
        "ok": True,
        "error": "",
    }


if __name__ == "__main__":
    import json

    with open("crossings.json", encoding="utf-8") as f:
        c = json.load(f)["crossings"][0]
    print(json.dumps(get_upstream_rain(c), indent=2))
