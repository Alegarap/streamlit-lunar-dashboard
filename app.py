"""Lunar Ventures — BI Dashboard

Main entry point. Run with: streamlit run app/app.py
"""

import re
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

# --- Title + Period pills on same row ---
title_col, period_col = st.columns([3, 1])
with title_col:
    st.title("Lunar Ventures — BI Dashboard")
with period_col:
    st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
    period = st.segmented_control(
        "Period",
        ["Today", "This Week", "This Month"],
        default="Today",
        label_visibility="collapsed",
    )

today = datetime.now().date()
if period == "Today":
    p_days = 0
elif period == "This Week":
    date_start = today - timedelta(days=today.weekday())
    p_days = (today - date_start).days
else:  # This Month
    date_start = today.replace(day=1)
    p_days = (today - date_start).days

# --- Fetch data ---
with st.spinner("Loading..."):
    try:
        raw_ingestion = sb.rpc_fresh("get_ingestion_stats", {"p_days": p_days})
    except Exception:
        raw_ingestion = []

    try:
        raw_cost = sb.rpc_fresh("get_cost_stats", {"p_days": p_days})
    except Exception:
        raw_cost = []

# --- Process ingestion ---
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

# --- Process cost ---
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
# KPI ROW — all 5 metrics in one row
# ---------------------------------------------------------------------------

def colored_metric(label, value, color):
    """Render a metric card with a colored value."""
    st.markdown(
        f'<div style="border:1px solid rgba(168,85,247,0.15); border-radius:12px; '
        f'padding:16px 20px; margin-bottom:16px; background:linear-gradient(145deg,#2A3154,#252B45); '
        f'box-shadow:0 2px 8px rgba(0,0,0,0.3),0 1px 2px rgba(0,0,0,0.2),'
        f'inset 0 1px 0 rgba(255,255,255,0.04);">'
        f'<p style="font-family:Fira Sans,sans-serif; font-size:0.8rem; font-weight:500; text-transform:uppercase; '
        f'letter-spacing:0.08em; opacity:0.7; margin:0 0 4px 0;">{label}</p>'
        f'<p style="font-family:Fira Code,monospace; font-size:1.8rem; font-weight:600; margin:0; color:{color}; '
        f'font-variant-numeric:tabular-nums;">{value}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    colored_metric("Themes", f"{themes_total:,}", "#F4A7C8")
with c2:
    colored_metric("Deals", f"{deals_total:,}", "#F4A7C8")
with c3:
    colored_metric("Total Items", f"{items_total:,}", "#F4A7C8")
with c4:
    colored_metric("Spend", format_cost(total_cost), "#A7F3D0")
with c5:
    colored_metric("Requests", f"{total_requests:,}", "#A7F3D0")

# ---------------------------------------------------------------------------
# TOP CLUSTERS — moved UP, this is the most important section
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Top Clusters")

def parse_ts(ts):
    if not ts:
        return None
    try:
        clean = re.sub(r'[+-]\d{2}:\d{2}$|Z$', '', ts)
        return datetime.fromisoformat(clean)
    except Exception:
        return None

try:
    top_clusters = sb.query_fresh("clusters", {
        "select": "label,hotness_score,item_count,source_diversity,first_seen_at,last_surfaced_at",
        "order": "hotness_score.desc.nullslast",
        "limit": "8",
    })

    if top_clusters:
        # Two-column grid of cluster cards
        left_col, right_col = st.columns(2)
        for idx, cluster in enumerate(top_clusters):
            rank = idx + 1
            score = float(cluster.get("hotness_score") or 0)
            label = cluster.get("label") or "Unlabeled"
            items = cluster.get("item_count", 0)
            diversity = cluster.get("source_diversity", 0)

            first_dt = parse_ts(cluster.get("first_seen_at", ""))
            age_days = (datetime.now() - first_dt).days if first_dt else 0
            if age_days <= 1:
                age_str = "new today"
            elif age_days < 7:
                age_str = f"{age_days}d old"
            elif age_days < 30:
                age_str = f"{age_days // 7}w old"
            else:
                age_str = f"{age_days // 30}mo old"

            last_dt = parse_ts(cluster.get("last_surfaced_at", ""))
            days_since = (datetime.now() - last_dt).days if last_dt else 999
            if days_since == 0:
                momentum = "🟢 active today"
            elif days_since <= 2:
                momentum = "🟢 active this week"
            elif days_since <= 7:
                momentum = "🟡 last week"
            else:
                momentum = "🔴 cooling off"

            score_color = "#EF4444" if score >= 0.6 else "#F59E0B" if score >= 0.4 else "#94A3B8"
            bar_width = int(score * 100)

            card_html = (
                f'<div style="display:flex; align-items:center; gap:16px; padding:12px 16px; '
                f'margin-bottom:8px; border-radius:10px; '
                f'background:linear-gradient(145deg,#2A3154,#252B45); '
                f'border:1px solid rgba(168,85,247,0.1);">'
                f'<span style="font-size:1.4rem; font-weight:800; opacity:0.3; min-width:28px;">#{rank}</span>'
                f'<div style="flex:1; min-width:0;">'
                f'<div style="display:flex; align-items:baseline; gap:10px; margin-bottom:4px;">'
                f'<span style="font-weight:700; font-size:1rem;">{label}</span>'
                f'<span style="font-size:0.75rem; color:{score_color}; font-weight:700;">{score:.2f}</span>'
                f'</div>'
                f'<div style="background:rgba(255,255,255,0.06); border-radius:4px; height:6px; width:100%; margin-bottom:6px;">'
                f'<div style="background:{score_color}; border-radius:4px; height:6px; width:{bar_width}%;"></div>'
                f'</div>'
                f'<div style="display:flex; gap:12px; font-size:0.75rem; opacity:0.6;">'
                f'<span>{items} items</span>'
                f'<span>{diversity} source{"s" if diversity != 1 else ""}</span>'
                f'<span>{age_str}</span>'
                f'<span>{momentum}</span>'
                f'</div>'
                f'</div>'
                f'</div>'
            )

            with (left_col if idx % 2 == 0 else right_col):
                st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("No cluster data available.")
except Exception:
    st.info("Cluster data not available.")

# ---------------------------------------------------------------------------
# CHARTS — in expanders so they don't push important content down
# ---------------------------------------------------------------------------
st.divider()

col_ing, col_cost = st.columns(2)

with col_ing:
    with st.expander("\U0001f4ca Ingestion by Source", expanded=False):
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
        else:
            st.caption("No ingestion data for this period.")

with col_cost:
    with st.expander("\U0001f4b0 Cost by Workflow", expanded=False):
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
        else:
            st.caption("No cost data for this period.")

# ---------------------------------------------------------------------------
# RECENT ITEMS — with source color dots
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Recent Items")
try:
    latest = sb.query_fresh("items", {
        "select": "created_at,source,type,title,source_url",
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
            url = item.get("source_url", "")
            src_color = COLORS.get(source, COLORS.get("other", "#94A3B8"))

            title_html = (
                f'<a href="{url}" target="_blank" style="color:inherit; text-decoration:none; '
                f'border-bottom:1px solid rgba(255,255,255,0.15);">{title}</a>'
                if url else title
            )

            st.markdown(
                f'<div style="padding:6px 0; border-bottom:1px solid rgba(128,128,128,0.08);">'
                f'<small><code>{created}</code> &nbsp; '
                f'<span style="display:inline-block; width:8px; height:8px; border-radius:50%; '
                f'background:{src_color}; margin-right:4px; vertical-align:middle;"></span>'
                f'<b>{source}</b> · {item_type} &nbsp; {title_html}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No recent items.")
except Exception:
    pass
