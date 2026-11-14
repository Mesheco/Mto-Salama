"""
Mto Salama - "Report from the river" page.

Anyone near a crossing can tell the local leader what they see, anonymously.
"""

import json
import time

import streamlit as st

from contacts import show_contacts
from reports_store import MAX_LEN, add_report, recent_reports

CHOICES = {
    "🌊 Maji yanaongezeka · Water is rising": "Maji yanaongezeka kwa drift",
    "🚶 Watu wanavuka · People are crossing": "Watu wanavuka sasa",
    "🌉 Drift / daraja imeharibika · Crossing damaged": "Drift au daraja imeharibika",
    "✅ Maji iko chini · Water is low": "Maji iko chini, hali ni shwari",
    "✏️ Kitu kingine · Something else": "",
}
LIMIT, WINDOW_S = 5, 600  # at most 5 reports per 10 minutes from one browser


@st.cache_data
def load_crossings() -> list:
    with open("crossings.json", encoding="utf-8") as f:
        return json.load(f)["crossings"]


st.title("💬 Report from the river")
st.caption("Ripoti kutoka mtoni")
st.markdown(
    "Are you at a river crossing? Tell your local leader what you see. "
    "**Uko kwa drift?** Mjulishe kiongozi wako unachoona."
)
st.error("In danger right now? Move away from the water and call **999** or **1199**. "
         "/ Uko hatarini sasa? Ondoka karibu na maji na upige **999** au **1199**.")

crossings = load_crossings()
crossing = st.selectbox(
    "Crossing / Drift", crossings,
    format_func=lambda c: c["name"] + (" (fictional demo)" if c.get("fictional") else ""),
)
show_contacts(crossing)

choice = st.radio("What do you see? / Unaona nini?", list(CHOICES), index=None)
details = st.text_area(
    "Add details (optional) / Ongeza maelezo",
    max_chars=MAX_LEN, height=90,
    placeholder="e.g. Maji imefika kwa daraja, inakuja na nguvu",
)
st.caption("🔒 Don't write your name or phone number. We keep only the message and the time, "
           "for 24 hours. / Usiandike jina wala namba ya simu.")

if st.button("Send report / Tuma ripoti", type="primary", use_container_width=True):
    sent = [t for t in st.session_state.get("sent_times", []) if time.time() - t < WINDOW_S]
    text = ". ".join(p for p in [CHOICES.get(choice or "", ""), details.strip()] if p)
    if len(sent) >= LIMIT:
        st.warning("You have sent several reports already - please wait a few minutes. "
                   "/ Subiri dakika chache.")
    elif not text:
        st.error("Choose what you see, or write a short message. / Chagua au andika ujumbe mfupi.")
    else:
        ok, result = add_report(crossing["id"], text)
        if ok:
            st.session_state.sent_times = sent + [time.time()]
            st.success(f"Asante! Ripoti imetumwa. Thank you - the local leader will see it.\n\n"
                       f"Sent: “{result}”")
        else:
            st.error(result)

st.page_link("leader.py", label="Local leader? Check the crossing →", icon="🌊")

n = len(recent_reports(crossing["id"]))
st.caption(f"{n} report(s) received for this crossing in the last 24 hours. "
           "Reports are anonymous. In this prototype, reports reset when the demo server restarts.")
