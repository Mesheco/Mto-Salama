"""
Live upstream rainfall for a crossing, from the free Open-Meteo API.

get_upstream_rain(crossing) returns a dict:
    rain_3d_mm      highest 3-day rain total among the upstream points (-1 if unavailable)
    points          per-point details for the screen
    data_age_hours  0 when freshly fetched
    ok              True if at least one upstream point answered
    error           message when nothing could be fetched
"""

from datetime import date, timedelta

import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def _rain_last_3_days(lat: float, lon: float) -> float:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "past_days": 3,
        "forecast_days": 1,
        "timezone": "Africa/Nairobi",
    }
    r = requests.get(WEATHER_URL, params=params, timeout=15)
    r.raise_for_status()
    daily = r.json()["daily"]
    today = date.today()
    start = today - timedelta(days=2)  # today + the 2 days before = 3 days
    total = 0.0
    for day, mm in zip(daily["time"], daily["precipitation_sum"]):
        if mm is not None and start.isoformat() <= day <= today.isoformat():
            total += float(mm)
    return round(total, 1)


def get_upstream_rain(crossing: dict) -> dict:
    points = []
    for p in crossing["upstream_points"]:
        try:
            mm = _rain_last_3_days(p["lat"], p["lon"])
            points.append({"name": p["name"], "rain_3d_mm": mm, "ok": True})
        except (requests.RequestException, KeyError, ValueError) as e:
            points.append({"name": p["name"], "rain_3d_mm": None, "ok": False, "error": str(e)[:120]})

    good = [p["rain_3d_mm"] for p in points if p["ok"]]
    if not good:
        return {
            "rain_3d_mm": -1.0,
            "points": points,
            "data_age_hours": 0.0,
            "ok": False,
            "error": "Could not reach the weather service.",
        }
    # Use the wettest upstream point: the cautious choice.
    return {
        "rain_3d_mm": max(good),
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
