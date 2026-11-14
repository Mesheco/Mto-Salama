"""
Emergency contacts shown in the app.

National numbers checked on 14 Nov 2026 against public listings
(e.g. hapakenya.com "How to contact emergency services in Nairobi & nationwide", Mar 2026).
Local numbers (chief, county disaster office) differ per area: add them per crossing in
crossings.json under "local_contacts" once confirmed with the county.
"""

import streamlit as st

NATIONAL = [
    ("999 / 112", "Police and general emergencies (any network)"),
    ("1199", "Kenya Red Cross - disaster response, toll-free"),
    ("911", "Emergency dispatch - Safaricom lines only"),
]

FIRST_AID = (
    "If someone is swept away: do not jump in. Throw a rope, stick or anything that floats, "
    "and call for help. / Mtu akisombwa na maji: usiruke majini. Mrushie kamba, fimbo au "
    "kitu kinachoelea, na uite msaada."
)


def show_contacts(crossing: dict | None = None, expanded: bool = False) -> None:
    with st.expander("🆘 Emergency contacts / Nambari za dharura", expanded=expanded):
        for number, what in NATIONAL:
            st.markdown(f"**{number}** - {what}")
        local = (crossing or {}).get("local_contacts", [])
        if local:
            st.markdown("**Local contacts for this crossing**")
            for c in local:
                st.markdown(f"**{c['number']}** - {c['name']}")
        else:
            st.caption("Local chief and county disaster office numbers: to be added for each "
                       "real crossing after confirming them with the county.")
        st.info(FIRST_AID)
        st.caption("National numbers checked 14 Nov 2026. Mto Salama is a prototype and does "
                   "not replace emergency services.")
