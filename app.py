"""Lunar Ventures — BI Dashboard

Main entry point. Run with: streamlit run app/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Lunar Ventures BI",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Lunar Ventures — BI Dashboard")
st.markdown(
    "Unified reporting for ambient sourcing, cost tracking, clustering, "
    "and AI-powered data querying."
)

st.markdown("### Pages")
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/1_Ingestion.py", label="📊 Ingestion Dashboard", icon="📊")
    st.page_link("pages/3_Clusters.py", label="🔬 Clusters & What's Hot", icon="🔬")
with col2:
    st.page_link("pages/2_Cost_Tracking.py", label="💰 Cost Tracking", icon="💰")
    st.page_link("pages/4_Ask_Data.py", label="🤖 Ask Data (AI Chat)", icon="🤖")
