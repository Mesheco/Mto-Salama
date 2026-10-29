"""
Mto Salama - first screen (Streamlit).

Run:  streamlit run app.py
"""

import csv
import json
import os
from datetime import datetime

import streamlit as st

import jaclang  # noqa: F401  (lets Python import .jac files)
import agents   # agents.jac - the four-agent pipeline
from weather import get_upstream_rain

OVERRIDE_LOG = "overrides.csv"

# Demo scenarios: work with no internet and no API key (the 3 required test cases).
SCENARIOS = {
    "Normal - heavy rain upstream, sunny here": {
        "rain": 52.0, "age": 1.0,
        "messages": "Maji imeanza kujaa kwa drift, inakuja na nguvu\n"
                    "watu wanavuka na boda saa hii\n"
                    "Habari za asubuhi wote",
    },
    "Confusing - little rain, but villagers report rising water": {
        "rain": 6.0, "age": 1.0,
        "messages": "Maji imejaa kwa drift ya chini\n"
                    "Drift imeharibika upande wa shule",
    },
    "Failure - weather data unavailable": {
        "rain": -1.0, "age": 0.0,
        "messages": "Mambo vipi, kuna mvua huko juu?",
    },
}

STYLE = {
    "DO NOT CROSS": ("#B42318", "#FEF3F2", "✋ DO NOT CROSS", "USIVUKE"),
    "CAUTION": ("#B54708", "#FFFAEB", "⚠ CAUTION", "TAHADHARI"),
    "SAFE-LOOKING": ("#027A48", "#ECFDF3", "LOOKS CALM - CHECK THE WATER", "INAONEKANA TULIVU"),
}


@st.cache_data
def load_crossings() -> list:
    with open("crossings.json", encoding="utf-8") as f:
        return json.load(f)["crossings"]


def log_override(crossing: str, model_status: str, chosen: str, reason: str) -> None:
    new = not os.path.exists(OVERRIDE_LOG)
    with open(OVERRIDE_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "crossing", "system_status", "leader_status", "reason"])
        w.writerow([datetime.now().isoformat(timespec="minutes"), crossing, model_status, chosen, reason])


def status_card(status: str, override: dict | None) -> None:
    shown = override["status"] if override else status
    fg, bg, en, sw = STYLE.get(shown, STYLE["CAUTION"])
    st.markdown(
        f"""<div style="border:3px solid {fg};background:{bg};border-radius:12px;
        padding:18px;text-align:center;margin:8px 0">
        <div style="font-size:34px;font-weight:800;color:{fg}">{en}</div>
        <div style="font-size:22px;font-weight:700;color:{fg}">{sw}</div></div>""",
        unsafe_allow_html=True,
    )
    if override:
        st.info(f"Local leader override (system said **{status}**): {override['reason']}")


# ------------------------------------------------------------------ page

st.set_page_config(page_title="Mto Salama", page_icon="🌊", layout="centered")
st.title("🌊 Mto Salama")
st.caption("River-crossing flood alerts for local leaders. A prototype that supports "
           "official warnings - it does not replace Kenya Met, county authorities or 1199.")

crossings = load_crossings()
crossing = st.selectbox(
    "Crossing", crossings,
    format_func=lambda c: c["name"] + (" (fictional demo)" if c.get("fictional") else ""),
)

mode = st.radio("Data", ["Demo scenario (works offline)", "Live upstream rain"], horizontal=True)

if mode.startswith("Demo"):
    name = st.selectbox("Scenario", list(SCENARIOS))
    sc = SCENARIOS[name]
    rain, age, default_msgs, points = sc["rain"], sc["age"], sc["messages"], None
else:
    with st.spinner("Checking rain in the hills upstream..."):
        w = get_upstream_rain(crossing)
    rain, age, default_msgs, points = w["rain_3d_mm"], w["data_age_hours"], "", w["points"]
    if not w["ok"]:
        st.warning(w["error"] + " The system will treat the crossing as CAUTION.")

messages = st.text_area(
    "Community messages (one per line, synthetic in this demo)",
    value=default_msgs, height=110,
    help="SMS/WhatsApp reports from people near the crossing. No names or numbers are stored.",
)

if st.button("Check crossing", type="primary", use_container_width=True):
    msgs = [m for m in messages.splitlines() if m.strip()]
    with st.spinner("Agents are reading reports and checking the risk..."):
        st.session_state.result = agents.run_check(crossing["name"], float(rain), float(age), msgs)
        st.session_state.points = points
        st.session_state.override = None
        st.session_state.approved = False

res = st.session_state.get("result")
if res:
    status_card(res["status"], st.session_state.get("override"))
    st.caption(f"Confidence: {res['confidence']}")

    st.subheader("Why")
    for r in res["reasons"]:
        st.write(f"• {r}")

    if st.session_state.get("points"):
        with st.expander("Upstream rain by point"):
            for p in st.session_state.points:
                val = f"{p['rain_3d_mm']} mm" if p["ok"] else "unavailable"
                st.write(f"{p['name']}: {val}")

    if res["reports"]:
        with st.expander("How each community message was read"):
            for row in res["reports"]:
                st.write(f"“{row['text']}” → **{row['kind']}** (read by {row['read_by']})")

    st.subheader("Draft alert")
    st.text_area("Kiswahili", res["alert_sw"], height=120)
    st.text_area("English", res["alert_en"], height=120)
    st.caption(f"Written by: {res['alert_by']} · {len(res['alert_sw'])} characters (Kiswahili)")

    col1, col2 = st.columns(2)
    if col1.button("✅ Approve alert", use_container_width=True):
        st.session_state.approved = True
    if st.session_state.get("approved"):
        st.success("Approved. In a full version this would be sent by SMS. Nothing is sent in this prototype.")

    with col2.popover("🙋 I disagree", use_container_width=True):
        choice = st.selectbox("What do you see at the river?", list(STYLE))
        reason = st.text_input("Reason (e.g. checked the drift at 6 am, water is low)")
        if st.button("Save override"):
            if not reason.strip():
                st.error("Please give a reason.")
            else:
                st.session_state.override = {"status": choice, "reason": reason.strip()}
                log_override(res["crossing"], res["status"], choice, reason.strip())
                st.rerun()

    with st.expander("Agent steps (for judges)"):
        for line in res["trace"]:
            st.write(line)
        st.caption(f"Model setting: {res['model']}")

st.divider()
st.caption("Data: Open-Meteo (CC BY 4.0). Demo crossing and messages are fictional. "
           "Emergency in Kenya: call 1199 (Kenya Red Cross).")
