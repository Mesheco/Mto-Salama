"""
Step 2 of the ML surge predictor: train and test the model.

Question the model answers:
    "Given the rain upstream (and the season), will the river surge TOMORROW?"

A SURGE day (the label) is a day when the river's flow is either
  - in the top 10% for that river, or
  - at least 1.5x the day before AND in the top 25% (a sudden flash rise).

Honest testing: the model learns from 2000-2014, thresholds are chosen on
2015-2018, and the scores reported are on 2019-2025 - years it never saw.

Run from the project folder (after download_history):
    python -m ml.train

Saves:
    models/surge_model.joblib   the trained model
    models/surge_model.json     thresholds, scores, explanations data
    models/report.md            plain-language results for your Devpost page
"""

import glob
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, roc_auc_score

from ml.features import FEATURE_LABELS, FEATURES, make_features

MODEL_DIR = "models"
TRAIN_END, VALID_END = "2014-12-31", "2018-12-31"


def label_river(df: pd.DataFrame) -> pd.DataFrame:
    q = df["discharge_m3s"]
    p90, p75 = q.quantile(0.90), q.quantile(0.75)
    q_next = q.shift(-1)
    surge = (q_next >= p90) | ((q_next >= 1.5 * q) & (q_next >= p75))
    df["surge_tomorrow"] = surge.astype(int)
    return df.iloc[:-1].dropna(subset=["discharge_m3s"])


def load_data() -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(os.path.join("data", "history_*.csv"))):
        river = os.path.basename(path)[len("history_"):-4]
        df = make_features(pd.read_csv(path))
        df = label_river(df)
        df["river"] = river
        frames.append(df)
        print(f"  {river}: {len(df)} days, {df['surge_tomorrow'].mean():.1%} surge days")
    if not frames:
        raise SystemExit("No data/history_*.csv files. Run: python -m ml.download_history")
    return pd.concat(frames, ignore_index=True)


def new_model() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=200, max_depth=10, min_samples_leaf=10,
        class_weight="balanced", n_jobs=-1, random_state=42,
    )


def pick_threshold(y: np.ndarray, p: np.ndarray, target_recall: float) -> float:
    """Highest threshold that still catches at least `target_recall` of surges."""
    best = 0.05
    for t in np.arange(0.05, 0.96, 0.01):
        if y.sum() and recall_score(y, p >= t, zero_division=0) >= target_recall:
            best = float(t)
    return round(best, 2)


def scores(y: np.ndarray, p: np.ndarray, t: float) -> dict:
    flagged = p >= t
    return {
        "recall": round(recall_score(y, flagged, zero_division=0), 3),
        "precision": round(precision_score(y, flagged, zero_division=0), 3),
        "false_alarm_rate": round(float(flagged[y == 0].mean()) if (y == 0).any() else 0.0, 3),
    }


def main() -> None:
    print("Loading history:")
    data = load_data()
    dates = data["date"]
    train = data[dates <= TRAIN_END]
    valid = data[(dates > TRAIN_END) & (dates <= VALID_END)]
    test = data[dates > VALID_END]
    X, y = FEATURES, "surge_tomorrow"

    print(f"\nTraining on {len(train)} days (to {TRAIN_END})...")
    model = new_model().fit(train[X], train[y])

    pv = model.predict_proba(valid[X])[:, 1]
    caution_t = pick_threshold(valid[y].values, pv, 0.85)   # catch 85% of surges
    danger_t = max(pick_threshold(valid[y].values, pv, 0.50), caution_t + 0.05)

    pt = model.predict_proba(test[X])[:, 1]
    yt = test[y].values
    result = {
        "trained_on": f"2000-01-01 to {TRAIN_END}",
        "tested_on": f"{VALID_END[:4]}-12-31 onwards (unseen years)",
        "rivers": sorted(data["river"].unique().tolist()),
        "test_days": int(len(test)),
        "test_surge_days": int(yt.sum()),
        "roc_auc": round(float(roc_auc_score(yt, pt)), 3) if 0 < yt.sum() < len(yt) else None,
        "caution_threshold": caution_t,
        "danger_threshold": round(danger_t, 2),
        "at_caution": scores(yt, pt, caution_t),
        "at_danger": scores(yt, pt, danger_t),
    }

    # Final model: learn from all years before the test period.
    final = new_model().fit(pd.concat([train, valid])[X], pd.concat([train, valid])[y])
    importances = sorted(
        zip(FEATURES, final.feature_importances_), key=lambda kv: kv[1], reverse=True
    )
    result["importance"] = {k: round(float(v), 3) for k, v in importances}
    # Percentile tables so the app can say "wetter than 95% of days".
    result["percentiles"] = {
        f: [round(float(v), 2) for v in np.percentile(data[f], range(0, 101))]
        for f in ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "max_point_3d"]
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(final, os.path.join(MODEL_DIR, "surge_model.joblib"), compress=3)
    with open(os.path.join(MODEL_DIR, "surge_model.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    c, d = result["at_caution"], result["at_danger"]
    lines = [
        "# Surge predictor - results",
        "",
        f"Rivers: {', '.join(result['rivers'])}. Trained on {result['trained_on']}; "
        f"scored on {result['test_days']} days the model never saw "
        f"({result['test_surge_days']} surge days).",
        "",
        "| Alert level | Probability | Surges caught (recall) | Alerts that were right (precision) | Calm days wrongly flagged |",
        "| --- | --- | --- | --- | --- |",
        f"| CAUTION | >= {caution_t:.0%} | {c['recall']:.0%} | {c['precision']:.0%} | {c['false_alarm_rate']:.0%} |",
        f"| DO NOT CROSS | >= {danger_t:.0%} | {d['recall']:.0%} | {d['precision']:.0%} | {d['false_alarm_rate']:.0%} |",
        "",
        f"ROC AUC on unseen years: {result['roc_auc']}",
        "",
        "What the model relies on most:",
        "",
    ] + [f"- {FEATURE_LABELS[k]}: {v:.0%}" for k, v in result["importance"].items()]
    lines += [
        "",
        "Missing a surge is the costly mistake, so thresholds favour catching surges "
        "over avoiding false alarms. Flow is modelled (GloFAS), not measured.",
    ]
    with open(os.path.join(MODEL_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n" + "\n".join(lines))
    print(f"\nSaved model to {MODEL_DIR}/. Restart the app to use it.")


if __name__ == "__main__":
    main()
