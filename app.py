"""Lunar Ventures — BI Dashboard

Main entry point. Run with: streamlit run app/app.py
"""

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import supabase_client as sb
from lib import style
from lib.charts import (
    COLORS,
    SOURCE_ORDER,
    format_cost,
    metric_row,
    style_fig,
    workflow_display_name,
)

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

# --- Period selector ---
period = st.selectbox(
    "Period",
    ["Today", "This Week", "This Month"],
    index=0,
    label_visibility="collapsed",
)

today = datetime.now().date()
if period == "Today":
    p_days = 0
    date_start = today
elif period == "This Week":
    date_start = today - timedelta(days=today.weekday())
    p_days = (today - date_start).days
else:  # This Month
    date_start = today.replace(day=1)
    p_days = (today - date_start).days

# --- Fetch data ---
try:
    raw_ingestion = sb.rpc_fresh("get_ingestion_stats", {"p_days": p_days})
except Exception:
    raw_ingestion = []

try:
    raw_cost = sb.rpc_fresh("get_cost_stats", {"p_days": p_days})
except Exception:
    raw_cost = []

# ---------------------------------------------------------------------------
# INGESTION
# ---------------------------------------------------------------------------
themes_total = 0
deals_total = 0
ingestion_by_source = defaultdict(lambda: {"theme": 0, "deal": 0})

for row in raw_ingestion or []:
    count = row.get("item_count", 0)
    src = row.get("source", "other")
    typ = row.get("type", "theme")
    ingestion_by_source[src][typ] += count
    if typ == "theme":
        themes_total += count
    else:
        deals_total += count

items_total = themes_total + deals_total

# --- Ingestion KPIs ---
st.subheader("Ingestion")
metric_row([
    ("Themes", f"{themes_total:,}", None),
    ("Deals", f"{deals_total:,}", None),
    ("Total Items", f"{items_total:,}", None),
])

# --- Ingestion chart: stacked bar by source, split themes/deals ---
if ingestion_by_source:
    rows = []
    for src in SOURCE_ORDER:
        if src in ingestion_by_source:
            rows.append({"Source": src, "Type": "theme", "Count": ingestion_by_source[src]["theme"]})
            rows.append({"Source": src, "Type": "deal", "Count": ingestion_by_source[src]["deal"]})
    # Include sources not in SOURCE_ORDER
    for src in ingestion_by_source:
        if src not in SOURCE_ORDER:
            rows.append({"Source": src, "Type": "theme", "Count": ingestion_by_source[src]["theme"]})
            rows.append({"Source": src, "Type": "deal", "Count": ingestion_by_source[src]["deal"]})

    if rows:
        df_ing = pd.DataFrame(rows)
        fig = px.bar(
            df_ing, x="Source", y="Count", color="Type",
            barmode="group",
            color_discrete_map={"theme": "#A855F7", "deal": "#14B8A6"},
            title=f"Ingestion by Source — {period}",
        )
        style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# COST
# ---------------------------------------------------------------------------
cost_by_key = defaultdict(lambda: {"cost": 0.0, "requests": 0})
total_cost = 0.0
total_requests = 0

for row in raw_cost or []:
    cost = float(row.get("total_cost", 0))
    reqs = int(row.get("request_count", 0))
    key = row.get("workflow_key", "unknown")
    cost_by_key[key]["cost"] += cost
    cost_by_key[key]["requests"] += reqs
    total_cost += cost
    total_requests += reqs

# --- Cost KPIs ---
st.subheader("Cost")
metric_row([
    ("Total Spend", format_cost(total_cost), None),
    ("Requests", f"{total_requests:,}", None),
    ("Workflows", str(len(cost_by_key)), None),
])

# --- Cost chart: horizontal bar by workflow key ---
if cost_by_key:
    rows = []
    for key, vals in cost_by_key.items():
        rows.append({
            "Workflow": workflow_display_name(key),
            "Cost": vals["cost"],
            "Requests": vals["requests"],
        })
    df_cost = pd.DataFrame(rows).sort_values("Cost", ascending=True)

    fig = px.bar(
        df_cost, x="Cost", y="Workflow",
        orientation="h",
        title=f"Spend by API Key — {period}",
        labels={"Cost": "Cost ($)", "Workflow": ""},
    )
    style_fig(fig)
    st.plotly_chart(fig, use_container_width=True)

# --- Recent activity ---
st.divider()
st.markdown("### Recent Items")
try:
    latest = sb.query_fresh("items", {
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
