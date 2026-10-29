"""
Step 1 of the ML surge predictor: download ~25 years of history.

For each training river (ml/rivers.json):
  - daily rainfall at each upstream point (Open-Meteo historical weather)
  - daily modelled river flow (Open-Meteo Flood API, GloFAS)

Saves one file per river:  data/history_<river>.csv
Columns: date, rain_mean, rain_max, discharge_m3s

Run from the project folder:
    python -m ml.download_history

Takes 1-3 minutes. If your connection drops, just run it again:
rivers already saved are skipped.
"""

import json
import os
import time

import pandas as pd
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"
START, END = "2000-01-01", "2025-12-31"
DATA_DIR = "data"


def get_json(url: str, params: dict, tries: int = 4) -> dict:
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, params=params, timeout=90)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == tries:
                raise
            print(f"    connection problem ({e.__class__.__name__}), retrying in {5 * attempt}s...")
            time.sleep(5 * attempt)
    return {}


def rain_history(lat: float, lon: float) -> pd.Series:
    d = get_json(ARCHIVE_URL, {
        "latitude": lat, "longitude": lon,
        "start_date": START, "end_date": END,
        "daily": "precipitation_sum", "timezone": "Africa/Nairobi",
    })["daily"]
    return pd.Series(d["precipitation_sum"], index=pd.to_datetime(d["time"]), dtype="float")


def flow_history(lat: float, lon: float) -> pd.Series | None:
    d = get_json(FLOOD_URL, {
        "latitude": lat, "longitude": lon,
        "start_date": START, "end_date": END,
        "daily": "river_discharge",
    }).get("daily", {})
    values = d.get("river_discharge")
    if not values or all(v is None for v in values):
        return None
    return pd.Series(values, index=pd.to_datetime(d["time"]), dtype="float")


def best_river_cell(lat: float, lon: float) -> tuple[float, float, pd.Series]:
    """The 5 km river grid may miss by one cell: try neighbours, keep the biggest river."""
    best = None
    for dlat in (0.0, -0.05, 0.05):
        for dlon in (0.0, -0.05, 0.05):
            la, lo = round(lat + dlat, 3), round(lon + dlon, 3)
            s = flow_history(la, lo)
            if s is None:
                continue
            mean = s.mean()
            print(f"    river cell ({la}, {lo}): mean flow {mean:.1f} m3/s")
            if best is None or mean > best[2].mean():
                best = (la, lo, s)
    if best is None:
        raise RuntimeError("No modelled river found near this point.")
    return best


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join("ml", "rivers.json"), encoding="utf-8") as f:
        rivers = json.load(f)["rivers"]

    for river in rivers:
        out = os.path.join(DATA_DIR, f"history_{river['id']}.csv")
        if os.path.exists(out):
            print(f"[skip] {river['name']} already downloaded ({out})")
            continue
        print(f"\n{river['name']}")

        print("  river flow:")
        lat, lon, flow = best_river_cell(river["river_point"]["lat"], river["river_point"]["lon"])

        print("  upstream rain:")
        rains = {}
        for p in river["upstream_points"]:
            rains[p["name"]] = rain_history(p["lat"], p["lon"])
            print(f"    {p['name']}: {rains[p['name']].sum() / 26:.0f} mm per year on average")
        rain_df = pd.DataFrame(rains)

        df = pd.DataFrame({
            "date": rain_df.index.strftime("%Y-%m-%d"),
            "rain_mean": rain_df.mean(axis=1).round(2).values,
            "rain_max": rain_df.max(axis=1).round(2).values,
        })
        df["discharge_m3s"] = flow.reindex(rain_df.index).round(3).values
        df.to_csv(out, index=False)
        print(f"  saved {len(df)} days -> {out}  (river cell {lat}, {lon})")

    print("\nDone. Next: python -m ml.train")


if __name__ == "__main__":
    main()
