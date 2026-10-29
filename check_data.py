"""
Phase 0 - Day 1 check: can we get the data Mto Salama needs?

Test 1: recent + forecast rainfall at the upstream points of the demo crossing.
Test 2: modelled river discharge near Makueni (scans a small grid, because
        small seasonal streams may not be in the 5 km global river model).
Test 3: river discharge for River Nyando at Ahero (backup training river).

Run:  python check_data.py
"""

import json
import requests
import pandas as pd

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"


def get_rainfall(lat, lon):
    """Daily rainfall: last 7 days + next 3 days."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "past_days": 7,
        "forecast_days": 3,
        "timezone": "Africa/Nairobi",
    }
    r = requests.get(WEATHER_URL, params=params, timeout=30)
    r.raise_for_status()
    d = r.json()["daily"]
    return pd.DataFrame({"date": d["time"], "rain_mm": d["precipitation_sum"]})


def get_discharge(lat, lon, past_days=92):
    """Daily modelled river discharge (m3/s). Returns None if no river found."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "river_discharge",
        "past_days": past_days,
        "forecast_days": 7,
    }
    r = requests.get(FLOOD_URL, params=params, timeout=30)
    r.raise_for_status()
    d = r.json().get("daily", {})
    values = d.get("river_discharge")
    if not values or all(v is None for v in values):
        return None
    return pd.DataFrame({"date": d["time"], "discharge_m3s": values})


def main():
    with open("crossings.json", encoding="utf-8") as f:
        crossing = json.load(f)["crossings"][0]

    # ---------- Test 1: upstream rainfall ----------
    print("=" * 60)
    print(f"TEST 1 - Upstream rainfall for {crossing['name']}")
    print("=" * 60)
    for p in crossing["upstream_points"]:
        df = get_rainfall(p["lat"], p["lon"])
        print(f"\n{p['name']} ({p['lat']}, {p['lon']})")
        print(df.to_string(index=False))

    # ---------- Test 2: scan for a modelled river near Makueni ----------
    print("\n" + "=" * 60)
    print("TEST 2 - Scanning for modelled rivers near the demo area")
    print("=" * 60)
    base_lat = crossing["crossing_point"]["lat"]
    base_lon = crossing["crossing_point"]["lon"]
    results = []
    for dlat in (-0.2, -0.1, 0.0, 0.1, 0.2):
        for dlon in (-0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4):
            lat, lon = round(base_lat + dlat, 2), round(base_lon + dlon, 2)
            try:
                df = get_discharge(lat, lon)
            except requests.RequestException as e:
                print(f"  ({lat}, {lon}) request failed: {e}")
                continue
            if df is None:
                continue
            s = df["discharge_m3s"].dropna()
            results.append({
                "lat": lat, "lon": lon,
                "mean_m3s": round(s.mean(), 2),
                "max_m3s": round(s.max(), 2),
                "peak_to_mean": round(s.max() / s.mean(), 1) if s.mean() > 0 else None,
            })
    if results:
        table = pd.DataFrame(results).sort_values("mean_m3s", ascending=False)
        print("\nPoints with river data (largest river first):")
        print(table.head(10).to_string(index=False))
        print("\nTip: a good training point has a clear mean flow and a high"
              " peak_to_mean (it shows flood spikes).")
    else:
        print("No modelled river found near the demo area -> use Nyando for training.")

    # ---------- Test 3: River Nyando at Ahero (backup) ----------
    print("\n" + "=" * 60)
    print("TEST 3 - River Nyando near Ahero (backup training river)")
    print("=" * 60)
    df = get_discharge(-0.17, 34.92)
    if df is None:
        print("No data at this point - try shifting lat/lon by 0.1.")
    else:
        s = df["discharge_m3s"].dropna()
        print(f"Mean {s.mean():.1f} m3/s | Max {s.max():.1f} m3/s | "
              f"Last value {s.iloc[-1]:.1f} m3/s")

    print("\nDone. Copy this output into DEVLOG.md (or paste it to Claude).")


if __name__ == "__main__":
    main()
