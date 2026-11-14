"""
Mto Salama - "Check a crossing" page, for the local leader.

Opened through app.py:  streamlit run app.py
"""

import csv
import json
import os
from datetime import datetime, timedelta, timezone

import streamlit as st
import streamlit.components.v1 as components

import jaclang  # noqa: F401  (lets Python import .jac files)
import agents   # agents.jac - the four-agent pipeline
from contacts import show_contacts
from ml.predict import predict_surge
from reports_store import recent_reports
from weather import get_upstream_rain

OVERRIDE_LOG = "overrides.csv"
REPORT_PATH = os.path.join("models", "report.md")
LISTENER_REPORT = os.path.join("models", "listener_report.md")

# Demo scenarios: work with no internet and no API key (the 3 required test cases).
# "features" are the upstream-rain numbers the surge model would see.
SCENARIOS = {
    "Sunny here, heavy rain upstream": {
        "rain": 52.0, "age": 1.0,
        "features": {"rain_1d": 18, "rain_3d": 46, "rain_7d": 78, "rain_14d": 104,
                     "max_point_3d": 52, "month": 4, "long_rains": 1, "short_rains": 0},
        "messages": "Habari za asubuhi wote\n"
                    "Maji imeanza kujaa kwa drift, inakuja na nguvu\n"
                    "Watu wanavuka na boda saa hii",
    },
    "Little rain, but villagers see rising water": {
        "rain": 6.0, "age": 1.0,
        "features": {"rain_1d": 1, "rain_3d": 4, "rain_7d": 9, "rain_14d": 15,
                     "max_point_3d": 6, "month": 8, "long_rains": 0, "short_rains": 0},
        "messages": "Maji imejaa kwa drift ya chini\n"
                    "Drift imeharibika upande wa shule",
    },
    "Weather service down": {
        "rain": -1.0, "age": 0.0, "features": None,
        "messages": "Mambo vipi, kuna mvua huko juu?",
    },
}

STYLE = {
    "DO NOT CROSS": ("#B42318", "#FEF3F2", "✋ DO NOT CROSS", "USIVUKE"),
    "CAUTION": ("#B54708", "#FFFAEB", "⚠ CAUTION", "TAHADHARI"),
    "SAFE-LOOKING": ("#027A48", "#ECFDF3", "LOOKS CALM - CHECK THE WATER", "INAONEKANA TULIVU"),
}

# What the leader should do right now, for each status.
ACTION = {
    "DO NOT CROSS": "Tell people to wait. Nobody should enter flowing water - on foot, boda or vehicle.",
    "CAUTION": "Watch the water before anyone crosses. If it is flowing or rising, wait.",
    "SAFE-LOOKING": "No warning signs found - still look at the water before crossing.",
}

NAIROBI = timezone(timedelta(hours=3))  # East Africa Time (no daylight saving)


@st.cache_data
def load_crossings() -> list:
    with open("crossings.json", encoding="utf-8") as f:
        return json.load(f)["crossings"]


@st.cache_data(ttl=600, show_spinner=False)
def live_rain(crossing_id: str) -> dict:
    """Fetch upstream rain at most once every 10 minutes per crossing."""
    c = next(c for c in load_crossings() if c["id"] == crossing_id)
    return get_upstream_rain(c)


def log_override(crossing: str, model_status: str, chosen: str, reason: str) -> None:
    new = not os.path.exists(OVERRIDE_LOG)
    with open(OVERRIDE_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "crossing", "system_status", "leader_status", "reason"])
        w.writerow([datetime.now(NAIROBI).isoformat(timespec="minutes"), crossing, model_status, chosen, reason])


def status_card(status: str, override: dict | None) -> None:
    shown = override["status"] if override else status
    fg, bg, en, sw = STYLE.get(shown, STYLE["CAUTION"])
    st.markdown(
        f"""<div role="alert" aria-live="assertive" style="border:3px solid {fg};background:{bg};
        border-radius:12px;padding:18px;text-align:center;margin:8px 0">
        <div style="font-size:34px;font-weight:800;color:{fg};line-height:1.2">{en}</div>
        <div style="font-size:22px;font-weight:700;color:{fg}">{sw}</div>
        <div style="font-size:16px;color:#344054;margin-top:8px">{ACTION.get(shown, "")}</div></div>""",
        unsafe_allow_html=True,
    )
    if override:
        st.info(f"Local leader override (system said **{status}**): {override['reason']}")


def _js_string(text: str) -> str:
    """Safe JavaScript string: alert text may come from an AI, so it must never break out of the script."""
    return json.dumps(text).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def read_aloud(sw_text: str, en_text: str) -> None:
    """Free text-to-speech in the browser, for people who cannot read the alert easily."""
    page = f"""
        <div style="display:flex;gap:8px;font-family:sans-serif">
          <button id="sw" style="flex:1;padding:10px;font-size:16px;border-radius:8px;
            border:1px solid #d0d5dd;background:#fff;cursor:pointer">🔊 Soma kwa sauti (Kiswahili)</button>
          <button id="en" style="flex:1;padding:10px;font-size:16px;border-radius:8px;
            border:1px solid #d0d5dd;background:#fff;cursor:pointer">🔊 Read aloud (English)</button>
        </div>
        <div id="note" style="font-family:sans-serif;font-size:12px;color:#667085;margin-top:4px"></div>
        <script>
          const texts = {{sw: {_js_string(sw_text)}, en: {_js_string(en_text)}}};
          function speak(lang) {{
            const synth = window.speechSynthesis;
            const note = document.getElementById("note");
            if (!synth) {{ note.textContent = "This browser cannot read aloud."; return; }}
            synth.cancel();
            const u = new SpeechSynthesisUtterance(texts[lang]);
            const voices = synth.getVoices();
            const want = lang === "sw" ? "sw" : "en";
            const v = voices.find(v => v.lang.toLowerCase().startsWith(want));
            if (v) {{ u.voice = v; u.lang = v.lang; note.textContent = ""; }}
            else {{
              u.lang = lang === "sw" ? "sw-KE" : "en-GB";
              note.textContent = lang === "sw" ?
                "No Kiswahili voice on this device - using the default voice." : "";
            }}
            u.rate = 0.9;
            synth.speak(u);
          }}
          document.getElementById("sw").onclick = () => speak("sw");
          document.getElementById("en").onclick = () => speak("en");
        </script>
        """
    if hasattr(st, "iframe"):   # newer Streamlit
        st.iframe(page, height=72)
    else:                       # older Streamlit
        components.html(page, height=72)


# ------------------------------------------------------------------ page

LOGO = os.path.join("assets", "logo.jpg")
if os.path.exists(LOGO):
    st.image(LOGO, width="stretch")
st.title("🌊 Mto Salama")
st.markdown("**River-crossing flood alerts for local leaders. A prototype that supports "
            "official warnings - it does not replace Kenya Met, county authorities or 1199.**")

with st.expander("ℹ️ How it works (30 seconds)", expanded="result" not in st.session_state):
    st.markdown(
        "**The danger:** it is dry and sunny at the crossing, but heavy rain fell in the hills "
        "upstream. A surge arrives hours later, and people are caught mid-crossing.\n\n"
        "1. 🌧️ **Machine learning** reads the rain in the hills upstream and predicts the chance "
        "of a surge by tomorrow (trained on 26 years of Kenyan river data).\n"
        "2. 💬 **NLP** reads messages from people at the river in Kiswahili, Sheng or English "
        "(anyone can send one on the **Report from the river** page).\n"
        "3. 🤝 **Agents** combine both, check each other for missing data or disagreement, and "
        "draft a short SMS in Kiswahili and English.\n"
        "4. 🙋 **A local leader decides**: approve the alert, or overrule it with a reason.\n\n"
        "Pick a scenario below and press **Check crossing**."
    )

st.page_link("report.py", label="Someone at the river? Send a report →", icon="💬")

if agents.USE_LLM:
    st.caption(f"🤖 AI mode: Claude reads unclear messages and writes alerts ({agents.MODEL_NAME}).")
else:
    st.caption("📴 Offline mode: our own Swahili/English reader and alert templates "
               "(no AI service needed). The surge model and safety rules work the same.")

crossings = load_crossings()
crossing = st.selectbox(
    "Crossing", crossings,
    format_func=lambda c: c["name"] + (" (fictional demo)" if c.get("fictional") else ""),
)

show_contacts(crossing)

mode = st.radio("Data", ["Demo scenario (works offline)", "Live upstream rain"], horizontal=True)

name = "live"
if mode.startswith("Demo"):
    name = st.selectbox("Scenario", list(SCENARIOS))
    sc = SCENARIOS[name]
    rain, age, default_msgs, points = sc["rain"], sc["age"], sc["messages"], None
    features = sc["features"]
else:
    with st.spinner("Checking rain in the hills upstream..."):
        w = live_rain(crossing["id"])
    rain, age, default_msgs, points = w["rain_3d_mm"], w["data_age_hours"], "", w["points"]
    features = w["features"]
    if not w["ok"]:
        live_rain.clear()  # don't remember a failure; try again next time
        st.warning(w["error"] + " The system will treat the crossing as CAUTION.")

river = recent_reports(crossing["id"])
river_text = "\n".join(r["text"] for r in river)
if mode.startswith("Live"):
    default_msgs = river_text  # live check: use what people at the river reported

# Reset the message box when the crossing, data mode or scenario changes.
source = f"{crossing['id']}|{mode}|{name}|{len(river) if mode.startswith('Live') else ''}"
if st.session_state.get("msg_source") != source:
    st.session_state.msg_source = source
    st.session_state.msgs = default_msgs


def add_river_reports() -> None:
    have = st.session_state.get("msgs", "").strip()
    st.session_state.msgs = (have + "\n" + river_text).strip() if have else river_text


if river:
    latest = river[-1]["time"][11:16]
    c1, c2 = st.columns([3, 2])
    c1.info(f"📥 **{len(river)} report(s) from the river** in the last 24 hours (latest {latest}).")
    if mode.startswith("Demo"):
        c2.button("Add them to the messages", on_click=add_river_reports, width="stretch")
    else:
        c2.caption("Included in the messages below.")

messages = st.text_area(
    "Community messages - one message per line, each from a different person",
    key="msgs", height=110,
    help="Reports from people near the crossing. Demo scenarios use synthetic messages. "
         "No names or numbers are stored.",
)

if st.button("Check crossing", type="primary", width="stretch"):
    msgs = [m for m in messages.splitlines() if m.strip()]
    with st.spinner("Agents are reading reports and checking the risk..."):
        ml = predict_surge(features) if features else {"available": False}
        st.session_state.ml = ml
        st.session_state.result = agents.run_check(crossing["name"], float(rain), float(age), msgs, ml)
        st.session_state.points = points
        st.session_state.override = None
        st.session_state.approved = False
        st.session_state.checked_at = datetime.now(NAIROBI).strftime("%d %b %Y, %H:%M")
        st.session_state.checked_with = "demo scenario" if mode.startswith("Demo") else "live rain data"
        st.rerun()  # redraw so the "How it works" panel folds away

res = st.session_state.get("result")
if res:
    status_card(res["status"], st.session_state.get("override"))
    st.caption(f"Checked {st.session_state.get('checked_at', '')} (Nairobi time) · "
               f"{st.session_state.get('checked_with', '')} · Confidence: {res['confidence']}")

    st.subheader("Why")
    for r in res["reasons"]:
        st.write(f"• {r}")

    ml = st.session_state.get("ml", {})
    with st.expander("Surge model (machine learning)"):
        if ml.get("available"):
            st.write(f"Chance the river surges by tomorrow: **{ml['probability']:.0%}** "
                     f"({ml['level']} risk)")
            st.progress(min(1.0, max(0.0, ml["probability"])))
            if os.path.exists(REPORT_PATH):
                with open(REPORT_PATH, encoding="utf-8") as f:
                    st.markdown(f.read())
        elif ml.get("reasons"):
            st.write(ml["reasons"][0])
        else:
            st.write("No rain data, so the surge model could not run.")

    if st.session_state.get("points"):
        with st.expander("Upstream rain by point"):
            for p in st.session_state.points:
                val = f"{p['rain_3d_mm']} mm" if p["ok"] else "unavailable"
                st.write(f"{p['name']}: {val}")

    if res["reports"]:
        with st.expander("How each community message was read (NLP)"):
            for row in res["reports"]:
                st.write(f"“{row['text']}” → **{row['kind']}** ({row['read_by']})")
            if os.path.exists(LISTENER_REPORT):
                st.divider()
                with open(LISTENER_REPORT, encoding="utf-8") as f:
                    st.markdown(f.read())

    st.subheader("Draft alert")
    st.text_area("Kiswahili", res["alert_sw"], height=120)
    st.text_area("English", res["alert_en"], height=120)
    st.caption(f"Written by: {res['alert_by']} · {len(res['alert_sw'])} characters (Kiswahili)")
    read_aloud(res["alert_sw"], res["alert_en"])

    col1, col2 = st.columns(2)
    if col1.button("✅ Approve alert", width="stretch"):
        st.session_state.approved = True
    if st.session_state.get("approved"):
        st.success("Approved. In a full version this would be sent by SMS. Nothing is sent in this prototype.")

    with col2.popover("🙋 I disagree", width="stretch"):
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
