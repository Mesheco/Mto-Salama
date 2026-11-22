"""
Automated checks for Mto Salama. Run:  python -m pytest -q

They cover the safety promises in the README: the three required scenarios, "never says safe",
the danger-word guard, Kikamba (beta) reading, and privacy of river reports.
No internet and no API key needed.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.pop("ANTHROPIC_API_KEY", None)  # always test the offline path

import jaclang  # noqa: E402,F401
import agents  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402
from ml.predict import predict_surge  # noqa: E402
from nlp.kikamba import kikamba_classify  # noqa: E402
from nlp.listen import classify_local  # noqa: E402
from reports_store import clean_text  # noqa: E402

CROSSING = "Mto Kavuthu drift (fictional demo)"


def check(name):
    sc = SCENARIOS[name]
    ml = predict_surge(sc["features"]) if sc["features"] else {"available": False}
    msgs = [m for m in sc["messages"].splitlines() if m.strip()]
    return agents.run_check(CROSSING, sc["rain"], sc["age"], msgs, ml)


# --- The required test cases (normal, confusing, failure) ---------------------------------

def test_normal_heavy_rain_upstream():
    assert check("Sunny here, heavy rain upstream")["status"] == "DO NOT CROSS"


def test_confusing_reports_disagree_with_rain():
    r = check("Little rain, but villagers see rising water")
    assert r["status"] == "DO NOT CROSS"
    assert r["confidence"].lower() == "low"


def test_failure_weather_down_never_says_safe():
    assert check("Weather service down")["status"] == "CAUTION"


def test_kikamba_scenario_is_not_calm():
    assert check("Kikamba reports, little rain upstream (beta)")["status"] in ("CAUTION", "DO NOT CROSS")


def test_alert_has_emergency_number():
    r = check("Sunny here, heavy rain upstream")
    assert "1199" in str(r)


# --- Listener (NLP) safety guard -------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Maji imejaa kwa drift",
    "Water is rising fast at the crossing",
    "Mafuriko yanakuja",
])
def test_danger_messages_never_read_as_all_clear(text):
    assert classify_local(text)["label"] not in ("ALL_CLEAR", "IRRELEVANT")


# --- Kikamba (beta) ----------------------------------------------------------------------------

@pytest.mark.parametrize("text,label", [
    ("usi wausia kiwu ndukilika", "WATER_RISING"),
    ("Kĩw'ũ nĩ kĩingĩ usi", "WATER_RISING"),
    ("andu nimaiinga usi yu", "PEOPLE_CROSSING"),
    ("kiwu kinini usi", "ALL_CLEAR"),
])
def test_kikamba_reports(text, label):
    assert classify_local(text)["label"] == label


@pytest.mark.parametrize("text", ["Usiache kuangalia maji", "Habari za asubuhi wote", "Watu wanavuka sasa"])
def test_kikamba_rules_ignore_kiswahili(text):
    assert kikamba_classify(text)[0] == ""


def test_kikamba_rules_do_not_touch_training_messages():
    import pandas as pd
    texts = pd.concat([pd.read_csv("data/messages.csv"), pd.read_csv("data/messages_test.csv")])["text"]
    assert sum(1 for t in texts if kikamba_classify(str(t))[0]) == 0


# --- Privacy -------------------------------------------------------------------------------------

def test_phone_numbers_removed_from_reports():
    cleaned = clean_text("Maji imejaa, nipigie 0712 345 678 au +254712345678")
    assert "712" not in cleaned
