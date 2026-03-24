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
from lib.charts import COLORS, SOURCE_ORDER, style_fig

style.apply()
st.title("Ingestion Dashboard")

with st.sidebar:
    st.caption("Data refreshes every 5 minutes")
    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Fetch data ---
with st.spinner("Loading ingestion data..."):
    raw = sb.rpc_fresh("get_ingestion_stats", {"p_days": 180})

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
week_dates = [
    (last_monday + timedelta(days=i)).isoformat()
    for i in range((today - last_monday).days + 1)
]
week_stats = sum_period(week_dates)

prev_monday = last_monday - timedelta(weeks=1)
prev_week_dates = [(prev_monday + timedelta(days=i)).isoformat() for i in range(7)]
prev_week_stats = sum_period(prev_week_dates)

# ---------------------------------------------------------------------------
# Scorecards — single row of 6
# ---------------------------------------------------------------------------
td = today_stats
yd = yesterday_stats
ws = week_stats
pw = prev_week_stats

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric(
    "Today Themes", td["themes"],
    f"{td['themes'] - yd['themes']:+d}" if td["themes"] != yd["themes"] else None,
)
c2.metric(
    "Today Deals", td["deals"],
    f"{td['deals'] - yd['deals']:+d}" if td["deals"] != yd["deals"] else None,
)
c3.metric(
    "Today Total", td["total"],
    f"{td['total'] - yd['total']:+d}" if td["total"] != yd["total"] else None,
)
c4.metric(
    "Week Themes", ws["themes"],
    f"{ws['themes'] - pw['themes']:+d}" if ws["themes"] != pw["themes"] else None,
)
c5.metric(
    "Week Deals", ws["deals"],
    f"{ws['deals'] - pw['deals']:+d}" if ws["deals"] != pw["deals"] else None,
)
c6.metric(
    "Week Total", ws["total"],
    f"{ws['total'] - pw['total']:+d}" if ws["total"] != pw["total"] else None,
)

# Date-range caption
week_start_str = last_monday.strftime("%b %d")
today_display = today.strftime("%b %d, %Y")
st.caption(
    f"Today: {today_display}  \u00b7  "
    f"This week: {week_start_str} \u2013 {today_display}  \u00b7  "
    f"Previous week: {prev_monday.strftime('%b %d')} \u2013 "
    f"{(prev_monday + timedelta(days=6)).strftime('%b %d')}"
)

# ---------------------------------------------------------------------------
# Chart styling helper
# ---------------------------------------------------------------------------

_CHART_LEGEND = dict(
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="left",
    x=0,
    font=dict(size=13, family="Fira Sans"),
)


def _polish_chart(fig, title: str):
    """Apply consistent styling to an ingestion chart."""
    style_fig(fig)
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=16, family="Fira Sans", color="white"),
            x=0.01,
            y=0.95,
        ),
        legend=_CHART_LEGEND,
        height=400,
        xaxis_title=None,
        yaxis_title="Items",
        yaxis_title_font=dict(size=13, family="Fira Sans"),
        xaxis_tickfont=dict(size=12, family="Fira Sans"),
        yaxis_tickfont=dict(size=12, family="Fira Sans"),
    )
    fig.update_traces(textposition="none")
    return fig


# ---------------------------------------------------------------------------
# Source breakdown charts — tabs
# ---------------------------------------------------------------------------
st.divider()
tab_daily, tab_weekly, tab_monthly = st.tabs([
    "Daily  (30 days)",
    "Weekly  (12 weeks)",
    "Monthly  (6 months)",
])

with tab_daily:
    rows = []
    for i in range(29, -1, -1):
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
    )
    fig.update_layout(barmode="stack", xaxis_tickformat="%b %d")
    _polish_chart(fig, "Daily Ingestion by Source")
    st.plotly_chart(fig, use_container_width=True)

with tab_weekly:
    rows = []
    for w in range(11, -1, -1):
        ws_start = last_monday - timedelta(weeks=w)
        dates = [(ws_start + timedelta(days=i)).isoformat() for i in range(7)]
        for src in SOURCE_ORDER:
            count = sum(
                by_day[ds][src]["theme"] + by_day[ds][src]["deal"] for ds in dates
            )
            rows.append({"Week": ws_start, "Source": src, "Items": count})
    df = pd.DataFrame(rows)
    fig = px.bar(
        df, x="Week", y="Items", color="Source",
        color_discrete_map=COLORS,
        category_orders={"Source": SOURCE_ORDER},
    )
    fig.update_layout(barmode="stack", xaxis_tickformat="%b %d")
    _polish_chart(fig, "Weekly Ingestion by Source")
    st.plotly_chart(fig, use_container_width=True)

with tab_monthly:
    rows = []
    for m in range(5, -1, -1):
        month = today.month - m
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        label = f"{year}-{month:02d}"
        dates = [ds for ds in by_day if ds.startswith(label)]
        for src in SOURCE_ORDER:
            count = sum(
                by_day[ds][src]["theme"] + by_day[ds][src]["deal"] for ds in dates
            )
            rows.append({"Month": label, "Source": src, "Items": count})
    df = pd.DataFrame(rows)
    fig = px.bar(
        df, x="Month", y="Items", color="Source",
        color_discrete_map=COLORS,
        category_orders={"Source": SOURCE_ORDER},
    )
    fig.update_layout(barmode="stack")
    _polish_chart(fig, "Monthly Ingestion by Source")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Latest items table
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Latest Items")

try:
    with st.spinner("Loading latest items..."):
        latest = sb.query_fresh("items", {
            "select": "created_at,source,type,title",
            "order": "created_at.desc",
            "limit": "100",
        })

    if latest:
        df_latest = pd.DataFrame(latest)
        df_latest["created_at"] = pd.to_datetime(
            df_latest["created_at"], errors="coerce"
        ).dt.strftime("%Y-%m-%d %H:%M")
        df_latest = df_latest.rename(columns={
            "created_at": "Created",
            "source": "Source",
            "type": "Type",
            "title": "Title",
        })

        # Source filter
        available_sources = sorted(df_latest["Source"].dropna().unique().tolist())
        selected_sources = st.multiselect(
            "Filter by source",
            options=available_sources,
            default=available_sources,
            key="ingestion_source_filter",
        )

        if selected_sources:
            df_filtered = df_latest[df_latest["Source"].isin(selected_sources)]
        else:
            df_filtered = df_latest

        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "Source": st.column_config.TextColumn("Source", width="small"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Created": st.column_config.TextColumn("Created", width="medium"),
                "Title": st.column_config.TextColumn("Title", width="large"),
            },
        )
    else:
        st.info("No items found.")
except Exception as e:
    st.error(f"Failed to load latest items: {e}")
