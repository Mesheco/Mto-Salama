"""
Train the offline Listener: a small NLP model that reads community messages
in Kiswahili, Sheng and English and says what they report.

Labels: WATER_RISING, PEOPLE_CROSSING, INFRASTRUCTURE_DAMAGED, ALL_CLEAR, IRRELEVANT

How it reads text:
  - character pieces (2-5 letters) catch word stems and spelling variations
    common in SMS and Sheng ("imejaa", "imejaaa", "inapanda", "imepanda")
  - whole words and word pairs catch phrases ("maji imejaa", "daraja limevunjika")
  - logistic regression turns these into a probability for each label

Data (all synthetic, written for this project):
  data/messages.csv       main examples
  data/messages_test.csv  extra messages written separately with new wording

Honest scoring: repeated 5-fold cross-validation over all messages
(each message is scored by a model that never saw it). The separate test
file is reported too, but it was written by the same author, so it is
likely optimistic. The final model learns from all messages.

Add your own messages to data/messages.csv and re-run to improve it:
    python -m nlp.train_listener
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline

from nlp.listen import has_danger_words

MODEL_DIR = "models"
LABELS = ["WATER_RISING", "PEOPLE_CROSSING", "INFRASTRUCTURE_DAMAGED", "ALL_CLEAR", "IRRELEVANT"]
UNSURE_BELOW = 0.45  # if the top label's probability is lower, ask Claude (if available)


def build_model() -> Pipeline:
    features = FeatureUnion([
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True, sublinear_tf=True)),
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), lowercase=True, sublinear_tf=True)),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(C=10.0, max_iter=3000, class_weight="balanced")),
    ])


def main() -> None:
    main_set = pd.read_csv(os.path.join("data", "messages.csv"))
    extra = pd.read_csv(os.path.join("data", "messages_test.csv"))
    data = pd.concat([main_set, extra], ignore_index=True)
    print(f"Messages: {len(data)} ({data.label.value_counts().min()}-{data.label.value_counts().max()} per label)")

    # 1. Realistic accuracy: repeated cross-validation, every message scored by a model that never saw it.
    accs, confs, preds_all, truth_all = [], [], [], []
    for seed in range(3):
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        proba = cross_val_predict(build_model(), data.text, data.label, cv=cv, method="predict_proba")
        classes = np.array(sorted(data.label.unique()))
        pred = classes[proba.argmax(axis=1)]
        accs.append(accuracy_score(data.label, pred))
        confs.append(proba.max(axis=1))
        preds_all.extend(pred)
        truth_all.extend(data.label)
    conf = np.concatenate(confs)
    truth, pred = np.array(truth_all), np.array(preds_all)
    sure = conf >= UNSURE_BELOW
    cv_acc = float(np.mean(accs))
    sure_acc = float((truth[sure] == pred[sure]).mean())
    danger_missed = float(((truth == "WATER_RISING") & (pred == "ALL_CLEAR")).sum() / (truth == "WATER_RISING").sum())
    texts = np.concatenate([data.text.values] * 3)
    guarded = np.array([
        "WATER_RISING" if (p in ("ALL_CLEAR", "IRRELEVANT") and has_danger_words(t)) else p
        for t, p in zip(texts, pred)
    ])
    guarded_acc = float((guarded == truth).mean())
    danger_missed_guarded = float(
        ((truth == "WATER_RISING") & (guarded == "ALL_CLEAR")).sum() / (truth == "WATER_RISING").sum()
    )

    # 2. Separate test file (optimistic: same author as the training messages).
    m = build_model().fit(main_set.text, main_set.label)
    test_acc = accuracy_score(extra.label, m.predict(extra.text))

    print(f"Realistic accuracy (cross-validation): {cv_acc:.0%}")
    print(f"Confident on {sure.mean():.0%} of messages -> {sure_acc:.0%} correct; "
          f"the other {1 - sure.mean():.0%} are flagged as unsure")
    print(f"Rising water misread as 'all clear': {danger_missed:.0%} (model alone) -> "
          f"{danger_missed_guarded:.0%} with the safety guard")
    print(f"Accuracy with the safety guard: {guarded_acc:.0%}")
    print(f"Separate test file (optimistic, same author): {test_acc:.0%}\n")
    cm = confusion_matrix(truth, pred, labels=LABELS)
    print("Confusion over cross-validation (rows = true, columns = predicted):")
    print(pd.DataFrame(cm, index=[l[:12] for l in LABELS], columns=[l[:6] for l in LABELS]))

    # 3. Final model learns from every message.
    final = build_model().fit(data.text, data.label)
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(final, os.path.join(MODEL_DIR, "listener.joblib"), compress=3)
    meta = {
        "messages": int(len(data)),
        "cv_accuracy": round(cv_acc, 3),
        "confident_share": round(float(sure.mean()), 3),
        "confident_accuracy": round(sure_acc, 3),
        "rising_read_as_clear": round(danger_missed, 3),
        "rising_read_as_clear_with_guard": round(danger_missed_guarded, 3),
        "accuracy_with_guard": round(guarded_acc, 3),
        "separate_test_accuracy_optimistic": round(float(test_acc), 3),
        "unsure_below": UNSURE_BELOW,
        "labels": LABELS,
    }
    with open(os.path.join(MODEL_DIR, "listener.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    report = [
        "# Listener (NLP) - results",
        "",
        f"Trained on {len(data)} synthetic messages in Kiswahili, Sheng and English "
        "(no real people's messages).",
        "",
        "| Measure | Result |",
        "| --- | --- |",
        f"| Realistic accuracy (cross-validation) | {cv_acc:.0%} (model) / {guarded_acc:.0%} (with safety guard) |",
        f"| Messages the model is confident about | {sure.mean():.0%} |",
        f"| Accuracy when confident | {sure_acc:.0%} |",
        f"| Rising water misread as 'all clear' | {danger_missed:.0%} (model) / {danger_missed_guarded:.0%} (with safety guard) |",
        "",
        "The safety guard stops messages with clear danger words (imejaa, inapanda, mafuriko, "
        "rising, flood...) from being read as 'all clear' unless they are negated. "
        f"Messages below {UNSURE_BELOW:.0%} confidence are passed to Claude when an AI key is set, "
        "or marked as unsure. An 'all clear' report never lowers the warning, and one report "
        "alone can raise the status to CAUTION at most (DO NOT CROSS needs heavy upstream rain or "
        "two or more reports), so a single misread message cannot make the app say 'safe' or trigger "
        "DO NOT CROSS.",
    ]
    with open(os.path.join(MODEL_DIR, "listener_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print(f"\nSaved model to {MODEL_DIR}/listener.joblib")


if __name__ == "__main__":
    main()
