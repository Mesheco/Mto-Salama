"""
Use the offline Listener model.

classify_local(text) -> dict
    available   False if the model file is missing
    label       e.g. "WATER_RISING"
    confidence  0-1
    unsure      True if confidence is below the model's threshold
    guarded     True if the safety guard overruled an "all clear" reading

Safety guard: the model sometimes confuses "water rising" with "all clear"
because both talk about maji / mto. If a message has clear danger words and
no negation, it is never read as ALL_CLEAR or IRRELEVANT.
"""

import json
import os
import re

import joblib

MODEL_PATH = os.path.join("models", "listener.joblib")
META_PATH = os.path.join("models", "listener.json")
_cache: dict = {}

DANGER_WORDS = [
    "imejaa", "inajaa", "kujaa", "imepanda", "inapanda", "inaongezeka", "yanaongezeka",
    "imeongezeka", "mafuriko", "imefurika", "inafurika", "unafurika", "yamefurika",
    "rising", "flood", "flooding", "swollen", "overflow", "under water",
]
NEGATIONS = [
    "hakuna", "haujajaa", "hayajaongezeka", "haijajaa", "haijapanda", "hapana",
    "imepungua", "imeshuka", "not", "no ", "gone down", "dropped",
]


def _load():
    if "model" not in _cache:
        if not (os.path.exists(MODEL_PATH) and os.path.exists(META_PATH)):
            _cache["model"], _cache["meta"] = None, None
        else:
            _cache["model"] = joblib.load(MODEL_PATH)
            with open(META_PATH, encoding="utf-8") as f:
                _cache["meta"] = json.load(f)
    return _cache["model"], _cache["meta"]


def has_danger_words(text: str) -> bool:
    t = " " + re.sub(r"\s+", " ", text.lower()) + " "
    if any(n in t for n in NEGATIONS):
        return False
    return any(w in t for w in DANGER_WORDS)


def classify_local(text: str) -> dict:
    model, meta = _load()
    if model is None:
        return {"available": False, "label": "", "confidence": 0.0, "unsure": True, "guarded": False}
    proba = model.predict_proba([text])[0]
    i = int(proba.argmax())
    label, conf = str(model.classes_[i]), float(proba[i])
    guarded = False
    if label in ("ALL_CLEAR", "IRRELEVANT") and has_danger_words(text):
        label, guarded = "WATER_RISING", True
    return {
        "available": True,
        "label": label,
        "confidence": round(conf, 3),
        "unsure": conf < float(meta["unsure_below"]) or guarded,
        "guarded": guarded,
    }
