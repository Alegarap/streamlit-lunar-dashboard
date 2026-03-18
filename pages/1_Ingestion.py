"""Ingestion Dashboard — replaces the Google Sheet ingestion dashboard.

Shows daily/weekly/monthly ingestion counts by source, scorecards,
and a latest items table. Data from get_ingestion_stats RPC + items table.
"""

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib import style
from lib.charts import COLORS, SOURCE_ORDER, apply_plotly_theme, metric_row

style.theme_toggle()
style.apply()
st.title("Ingestion Dashboard")

with st.sidebar:
    st.caption("Data refreshes every 5 minutes")
    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Fetch data ---
raw = sb.rpc_call("get_ingestion_stats", {"p_days": 180})
if not raw:
    st.warning("No ingestion data returned from Supabase.")
    st.stop()

# --- Build day index ---
by_day = defaultdict(lambda: defaultdict(lambda: {"theme": 0, "deal": 0}))
for row in raw:
    by_day[row["day"]][row["source"]][row["type"]] += row["item_count"]

today = datetime.now().date()
today_str = today.isoformat()


def sum_period(dates: list[str]) -> dict:
    themes = deals = 0
    by_src = {s: 0 for s in SOURCE_ORDER}
    for ds in dates:
        for src in SOURCE_ORDER:
            t = by_day[ds][src]["theme"]
            d = by_day[ds][src]["deal"]
            by_src[src] += t + d
            themes += t
            deals += d
        for src, counts in by_day[ds].items():
            if src not in SOURCE_ORDER:
                themes += counts["theme"]
                deals += counts["deal"]
    return {"themes": themes, "deals": deals, "total": themes + deals, "by_src": by_src}


today_stats = sum_period([today_str])
yesterday_stats = sum_period([(today - timedelta(days=1)).isoformat()])

last_monday = today - timedelta(days=today.weekday())
week_dates = [(last_monday + timedelta(days=i)).isoformat()
              for i in range((today - last_monday).days + 1)]
week_stats = sum_period(week_dates)

prev_monday = last_monday - timedelta(weeks=1)
prev_week_dates = [(prev_monday + timedelta(days=i)).isoformat() for i in range(7)]
prev_week_stats = sum_period(prev_week_dates)

# --- Scorecards ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("Today")
    td = today_stats
    yd = yesterday_stats
    metric_row([
        ("Themes", td["themes"],
         f"{td['themes'] - yd['themes']:+d}" if td["themes"] != yd["themes"] else None),
        ("Deals", td["deals"],
         f"{td['deals'] - yd['deals']:+d}" if td["deals"] != yd["deals"] else None),
        ("Total", td["total"],
         f"{td['total'] - yd['total']:+d}" if td["total"] != yd["total"] else None),
    ])
with col2:
    st.subheader("This Week")
    ws = week_stats
    pw = prev_week_stats
    metric_row([
        ("Themes", ws["themes"],
         f"{ws['themes'] - pw['themes']:+d}" if ws["themes"] != pw["themes"] else None),
        ("Deals", ws["deals"],
         f"{ws['deals'] - pw['deals']:+d}" if ws["deals"] != pw["deals"] else None),
        ("Total", ws["total"],
         f"{ws['total'] - pw['total']:+d}" if ws["total"] != pw["total"] else None),
    ])

# --- Source breakdown charts ---
st.divider()
tab_daily, tab_weekly, tab_monthly = st.tabs(["Daily (30d)", "Weekly (12w)", "Monthly (6m)"])

with tab_daily:
    rows = []
    for i in range(29, -1, -1):  # oldest first for correct chart ordering
        d = today - timedelta(days=i)
        ds = d.isoformat()
        for src in SOURCE_ORDER:
            count = by_day[ds][src]["theme"] + by_day[ds][src]["deal"]
            rows.append({"Date": d, "Source": src, "Items": count})
    df = pd.DataFrame(rows)
    fig = px.bar(
        df, x="Date", y="Items", color="Source",
        color_discrete_map=COLORS,
        category_orders={"Source": SOURCE_ORDER},
        title="Daily Ingestion by Source",
    )
    fig.update_layout(barmode="stack", xaxis_tickformat="%b %d")
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

with tab_weekly:
    rows = []
    for w in range(11, -1, -1):  # oldest first
        ws = last_monday - timedelta(weeks=w)
        dates = [(ws + timedelta(days=i)).isoformat() for i in range(7)]
        for src in SOURCE_ORDER:
            count = sum(by_day[ds][src]["theme"] + by_day[ds][src]["deal"] for ds in dates)
            rows.append({"Week": ws, "Source": src, "Items": count})
    df = pd.DataFrame(rows)
    fig = px.bar(
        df, x="Week", y="Items", color="Source",
        color_discrete_map=COLORS,
        category_orders={"Source": SOURCE_ORDER},
        title="Weekly Ingestion by Source",
    )
    fig.update_layout(barmode="stack", xaxis_tickformat="%b %d")
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

with tab_monthly:
    rows = []
    for m in range(5, -1, -1):  # oldest first
        month = today.month - m
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        label = f"{year}-{month:02d}"
        dates = [ds for ds in by_day if ds.startswith(label)]
        for src in SOURCE_ORDER:
            count = sum(by_day[ds][src]["theme"] + by_day[ds][src]["deal"] for ds in dates)
            rows.append({"Month": label, "Source": src, "Items": count})
    df = pd.DataFrame(rows)
    fig = px.bar(
        df, x="Month", y="Items", color="Source",
        color_discrete_map=COLORS,
        category_orders={"Source": SOURCE_ORDER},
        title="Monthly Ingestion by Source",
    )
    fig.update_layout(barmode="stack")
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

# --- Latest items table ---
st.divider()
st.subheader("Latest Items")
latest = sb.query_table("items", {
    "select": "created_at,source,type,title,source_url",
    "order": "created_at.desc",
    "limit": "100",
})
if latest:
    df_latest = pd.DataFrame(latest)
    df_latest["created_at"] = pd.to_datetime(df_latest["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(
        df_latest.rename(columns={
            "created_at": "Created",
            "source": "Source",
            "type": "Type",
            "title": "Title",
            "source_url": "URL",
        }),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No items found.")
