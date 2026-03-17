"""Lunar Ventures — BI Dashboard

Main entry point. Run with: streamlit run app/app.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import supabase_client as sb
from lib import style
from lib.charts import COLORS, SOURCE_ORDER, metric_row, format_cost

st.set_page_config(
    page_title="Lunar Ventures BI",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

style.apply()

# --- Sidebar ---
with st.sidebar:
    st.caption("Data refreshes every 5 minutes")
    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.title("Lunar Ventures — BI Dashboard")

# --- Key metrics overview ---
try:
    today = datetime.now().date()
    today_str = today.isoformat()

    # Ingestion stats
    raw = sb.rpc_call("get_ingestion_stats", {"p_days": 7})
    today_items = sum(r["item_count"] for r in (raw or []) if r["day"] == today_str)
    week_items = sum(r["item_count"] for r in (raw or []))

    # Cluster stats
    total_items = sb.count_rows("items")
    hot_count = len(sb.query_table("clusters", {
        "select": "id",
        "hotness_score": "gt.0.3",
        "limit": "100",
    }))

    # Cost stats (may not exist yet)
    try:
        cost_data = sb.rpc_call("get_cost_stats", {"p_days": 7})
        week_cost = sum(float(r.get("total_cost", 0)) for r in (cost_data or []))
        cost_str = format_cost(week_cost)
    except Exception:
        cost_str = "—"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Items Today", today_items)
    col2.metric("Items This Week", week_items)
    col3.metric("Hot Clusters", hot_count)
    col4.metric("Cost This Week", cost_str)

except Exception:
    st.info("Loading overview metrics...")

st.divider()

# --- Page navigation ---
st.markdown("### Pages")
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/1_Ingestion.py", label="Ingestion Dashboard", icon="📊")
    st.page_link("pages/3_Clusters.py", label="Clusters & What's Hot", icon="🔬")
with col2:
    st.page_link("pages/2_Cost_Tracking.py", label="Cost Tracking", icon="💰")
    st.page_link("pages/4_Ask_Data.py", label="Ask Data (AI Chat)", icon="🤖")

# --- Recent activity ---
st.divider()
st.markdown("### Recent Items")
try:
    latest = sb.query_table("items", {
        "select": "created_at,source,type,title",
        "order": "created_at.desc",
        "limit": "10",
    })
    if latest:
        for item in latest:
            created = item.get("created_at", "")
            if created:
                created = created.replace("T", " ").split(".")[0][:16]
            source = item.get("source", "")
            item_type = item.get("type", "")
            title = item.get("title", "Untitled")
            st.markdown(
                f"<small><code>{created}</code> &nbsp; "
                f"<b>{source}</b> · {item_type} &nbsp; {title}</small>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No recent items.")
except Exception:
    pass
