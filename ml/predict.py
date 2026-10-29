"""
Use the trained surge model.

predict_surge(features) -> dict
    available   False if the model hasn't been trained yet (app falls back to rules)
    probability chance of a surge tomorrow (0-1)
    level       "high" | "medium" | "low"
    reasons     plain-language explanation, e.g.
                "48 mm upstream rain in the last 3 days - wetter than 97% of days"
"""

import bisect
import json
import os

import joblib
import pandas as pd

from ml.features import FEATURE_LABELS, FEATURES

MODEL_PATH = os.path.join("models", "surge_model.joblib")
META_PATH = os.path.join("models", "surge_model.json")
_cache: dict = {}


def _load():
    if "model" not in _cache:
        if not (os.path.exists(MODEL_PATH) and os.path.exists(META_PATH)):
            return None, None
        _cache["model"] = joblib.load(MODEL_PATH)
        with open(META_PATH, encoding="utf-8") as f:
            _cache["meta"] = json.load(f)
    return _cache["model"], _cache["meta"]


def _percentile(meta: dict, feature: str, value: float) -> int:
    table = meta["percentiles"][feature]
    return max(0, min(100, bisect.bisect_left(table, value) - 1))


def predict_surge(features: dict) -> dict:
    model, meta = _load()
    if model is None:
        return {"available": False, "probability": None, "level": None,
                "reasons": ["Surge model not trained yet - using simple rain rules."]}

    row = pd.DataFrame([{f: float(features[f]) for f in FEATURES}])
    prob = float(model.predict_proba(row)[0, 1])
    if prob >= meta["danger_threshold"]:
        level = "high"
    elif prob >= meta["caution_threshold"]:
        level = "medium"
    else:
        level = "low"

    reasons = []
    rain_feats = [f for f in meta["importance"] if f in meta["percentiles"]]
    for f in rain_feats[:3]:
        pct = _percentile(meta, f, float(features[f]))
        if pct >= 75:
            reasons.append(f"{float(features[f]):.0f} mm {FEATURE_LABELS[f]} - "
                           f"wetter than {pct}% of days")
    if not reasons:
        reasons.append("Upstream rain is around or below normal for these rivers.")
    if features.get("long_rains") or features.get("short_rains"):
        reasons.append("It is the rainy season, when surges are more common.")

    return {"available": True, "probability": round(prob, 3), "level": level, "reasons": reasons}
