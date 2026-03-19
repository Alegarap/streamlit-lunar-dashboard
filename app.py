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

# ---------------------------------------------------------------------------
# COST (process data before layout)
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

# ---------------------------------------------------------------------------
# TWO-COLUMN LAYOUT: Ingestion | Cost
# ---------------------------------------------------------------------------
def colored_metric(label, value, color):
    """Render a metric card with a colored value."""
    st.markdown(
        f'<div style="border:1px solid rgba(168,85,247,0.15); border-radius:12px; '
        f'padding:16px 20px; margin-bottom:16px; background:linear-gradient(145deg,#2A3154,#252B45); '
        f'box-shadow:0 2px 8px rgba(0,0,0,0.3),0 1px 2px rgba(0,0,0,0.2),'
        f'inset 0 1px 0 rgba(255,255,255,0.04);">'
        f'<p style="font-size:0.8rem; font-weight:500; text-transform:uppercase; '
        f'letter-spacing:0.02em; opacity:0.7; margin:0 0 4px 0;">{label}</p>'
        f'<p style="font-size:1.8rem; font-weight:700; margin:0; color:{color};">{value}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


col_ing, col_cost = st.columns(2)

with col_ing:
    st.subheader("Ingestion")
    c1, c2, c3 = st.columns(3)
    with c1:
        colored_metric("Themes", f"{themes_total:,}", "#F4A7C8")
    with c2:
        colored_metric("Deals", f"{deals_total:,}", "#F4A7C8")
    with c3:
        colored_metric("Total", f"{items_total:,}", "#F4A7C8")

    if ingestion_by_source:
        rows = []
        for src in SOURCE_ORDER:
            if src in ingestion_by_source:
                rows.append({"Source": src, "Type": "theme", "Count": ingestion_by_source[src]["theme"]})
                rows.append({"Source": src, "Type": "deal", "Count": ingestion_by_source[src]["deal"]})
        for src in ingestion_by_source:
            if src not in SOURCE_ORDER:
                rows.append({"Source": src, "Type": "theme", "Count": ingestion_by_source[src]["theme"]})
                rows.append({"Source": src, "Type": "deal", "Count": ingestion_by_source[src]["deal"]})

        if rows:
            df_ing = pd.DataFrame(rows)
            fig = px.bar(
                df_ing, x="Source", y="Count", color="Type",
                barmode="group",
                color_discrete_map={"theme": "#A855F7", "deal": "#F59E0B"},
            )
            style_fig(fig)
            fig.update_layout(
                height=350,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

with col_cost:
    st.subheader("Cost")
    c1, c2, c3 = st.columns(3)
    with c1:
        colored_metric("Spend", format_cost(total_cost), "#A7F3D0")
    with c2:
        colored_metric("Requests", f"{total_requests:,}", "#A7F3D0")
    with c3:
        colored_metric("Keys", str(len(cost_by_key)), "#A7F3D0")

    if cost_by_key:
        rows = []
        for key, vals in cost_by_key.items():
            rows.append({
                "Workflow": workflow_display_name(key),
                "Cost": vals["cost"],
            })
        df_cost = pd.DataFrame(rows).sort_values("Cost", ascending=True)

        fig = px.bar(
            df_cost, x="Cost", y="Workflow",
            orientation="h",
            labels={"Cost": "Cost ($)", "Workflow": ""},
        )
        style_fig(fig)
        fig.update_layout(height=350)
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
