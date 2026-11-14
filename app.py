"""
Mto Salama - app entry point (two pages).

  🌊 Check a crossing     leader.py   for the local leader
  💬 Report from the river report.py  for anyone at the crossing

Run:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="Mto Salama", page_icon="🌊", layout="centered")

pages = [
    st.Page("leader.py", title="Check a crossing", icon="🌊", default=True),
    st.Page("report.py", title="Report from the river", icon="💬"),
]
try:
    nav = st.navigation(pages, position="top")   # menu across the top: easy to see on phones
except TypeError:
    nav = st.navigation(pages)                   # older Streamlit: menu in the sidebar
nav.run()
