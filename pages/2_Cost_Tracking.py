"""Cost Tracking Dashboard — replaces the Google Sheet cost dashboard.

Shows spend by workflow, model, and time period.
Data from cost_log table (populated by n8n Broadcast Receiver).
"""

import sys
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib import style
from lib.charts import format_cost, metric_row, style_fig, workflow_display_name

style.apply()
st.markdown(
    '<style>[data-testid="stMetricValue"] { color: #A7F3D0 !important; }</style>',
    unsafe_allow_html=True,
)
st.title("Cost Tracking")

with st.sidebar:
    st.caption("Data refreshes every 5 minutes")
    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Check if cost_log table / RPC exists ---
try:
    with st.spinner("Loading cost data..."):
        cost_data = sb.rpc_fresh("get_cost_stats", {"p_days": 90})
except urllib.error.HTTPError as e:
    if e.code == 404:
        st.warning(
            "The `get_cost_stats` RPC doesn't exist yet. "
            "Run migration `011_cost_log.sql` in the Supabase SQL Editor first."
        )
    else:
        st.warning(f"Failed to fetch cost data (HTTP {e.code}). Check Supabase logs.")
    st.info(
        "Once the migration is applied and the n8n Broadcast Receiver is updated "
        "to dual-write to Supabase, cost data will appear here."
    )
    st.stop()
except Exception as e:
    st.error(f"Unexpected error fetching cost data: {e}")
    st.stop()

if not cost_data:
    st.info(
        "No cost data yet. Cost data will appear here once natural workflow "
        "executions start flowing through the n8n Broadcast Receiver."
    )
    st.stop()

# --- Process data ---
df = pd.DataFrame(cost_data)
df["day"] = pd.to_datetime(df["day"])
df["total_cost"] = pd.to_numeric(df["total_cost"], errors="coerce").fillna(0)
if "total_input_tokens" in df.columns:
    df["total_input_tokens"] = pd.to_numeric(df["total_input_tokens"], errors="coerce").fillna(0).astype(int)
if "total_output_tokens" in df.columns:
    df["total_output_tokens"] = pd.to_numeric(df["total_output_tokens"], errors="coerce").fillna(0).astype(int)
if "request_count" in df.columns:
    df["request_count"] = pd.to_numeric(df["request_count"], errors="coerce").fillna(0).astype(int)
else:
    df["request_count"] = 1

# Map workflow keys to human-readable names
if "workflow_key" in df.columns:
    df["workflow"] = df["workflow_key"].apply(workflow_display_name)

today = datetime.now().date()
week_start = today - timedelta(days=today.weekday())
month_start = today.replace(day=1)


# --- Scorecards (use the day column from the RPC, which is in UTC like the Home page) ---
def cost_for_p_days(p_days):
    """Filter df using the same p_days logic as the RPC: day >= CURRENT_DATE - p_days."""
    # The RPC's "day" column is already in UTC. Use the min date from the df
    # to match the same boundary the RPC would use.
    cutoff = today - timedelta(days=p_days)
    mask = df["day"].dt.date >= cutoff
    subset = df[mask]
    return subset["total_cost"].sum(), subset["request_count"].sum()


today_cost, today_reqs = cost_for_p_days(0)
week_cost, week_reqs = cost_for_p_days((today - week_start).days)
month_cost, month_reqs = cost_for_p_days((today - month_start).days)
all_cost, all_reqs = df["total_cost"].sum(), df["request_count"].sum()

metric_row([
    ("Today", format_cost(today_cost), f"{int(today_reqs)} requests"),
    ("This Week", format_cost(week_cost), f"{int(week_reqs)} requests"),
    ("This Month", format_cost(month_cost), f"{int(month_reqs)} requests"),
    ("All Time (90d)", format_cost(all_cost), f"{int(all_reqs)} requests"),
])

st.divider()

# --- Period selector ---
chart_period = st.radio(
    "Chart period",
    ["Today", "This Week", "This Month", "Last 90 Days"],
    index=1,
    horizontal=True,
    label_visibility="collapsed",
)

_period_days = {
    "Today": 0,
    "This Week": (today - week_start).days,
    "This Month": (today - month_start).days,
    "Last 90 Days": 90,
}
chart_start = today - timedelta(days=_period_days[chart_period])
df_period = df[df["day"].dt.date >= chart_start]

# --- API provider breakdown ---
if "api_type" in df_period.columns:
    exa_mask = df_period["api_type"] == "exa"
    exa_cost = df_period.loc[exa_mask, "total_cost"].sum()
    openrouter_cost = df_period.loc[~exa_mask, "total_cost"].sum()
    exa_reqs = df_period.loc[exa_mask, "request_count"].sum()
    or_reqs = df_period.loc[~exa_mask, "request_count"].sum()

    if exa_cost > 0 or openrouter_cost > 0:
        st.subheader("By Provider")
        metric_row([
            ("OpenRouter", format_cost(openrouter_cost), f"{int(or_reqs)} requests"),
            ("Exa Search", format_cost(exa_cost), f"{int(exa_reqs)} requests"),
        ])

# --- Cost trend ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Daily Cost Trend")
    daily = df_period.groupby("day").agg({"total_cost": "sum"}).reset_index().sort_values("day")
    if len(daily) > 1:
        fig = px.area(
            daily, x="day", y="total_cost",
            labels={"day": "Date", "total_cost": "Cost (USD)"},
        )
    else:
        fig = px.bar(
            daily, x="day", y="total_cost",
            labels={"day": "Date", "total_cost": "Cost (USD)"},
        )
    fig.update_layout(xaxis_tickformat="%b %d")
    style_fig(fig)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Cost by Workflow")
    if "workflow" in df_period.columns:
        by_wf = df_period.groupby("workflow").agg({"total_cost": "sum"}).reset_index()
        by_wf = by_wf.sort_values("total_cost", ascending=True)
        fig = px.bar(
            by_wf, x="total_cost", y="workflow",
            orientation="h",
            labels={"total_cost": "Cost (USD)", "workflow": "Workflow"},
        )
        style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No workflow breakdown available in current data.")

# --- Cost by model ---
if "model" in df_period.columns:
    st.subheader("Cost by Model")
    agg_cols = {"total_cost": "sum", "request_count": "sum"}
    if "total_input_tokens" in df_period.columns:
        agg_cols["total_input_tokens"] = "sum"
    if "total_output_tokens" in df_period.columns:
        agg_cols["total_output_tokens"] = "sum"
    by_model = df_period.groupby("model").agg(agg_cols).reset_index().sort_values("total_cost", ascending=False)

    rename_map = {
        "model": "Model",
        "total_cost": "Total Cost (USD)",
        "request_count": "Requests",
        "total_input_tokens": "Input Tokens",
        "total_output_tokens": "Output Tokens",
    }
    st.dataframe(
        by_model.rename(columns=rename_map),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Cost (USD)": st.column_config.NumberColumn(format="%.4f USD"),
        },
    )

# --- Cost by workflow over time ---
if "workflow" in df_period.columns:
    st.subheader("Daily Cost by Workflow")
    daily_wf = df_period.groupby(["day", "workflow"]).agg({"total_cost": "sum"}).reset_index().sort_values("day")
    if len(daily_wf) > 1:
        fig = px.area(
            daily_wf, x="day", y="total_cost", color="workflow",
            labels={"day": "Date", "total_cost": "Cost (USD)", "workflow": "Workflow"},
        )
    else:
        fig = px.bar(
            daily_wf, x="day", y="total_cost", color="workflow",
            labels={"day": "Date", "total_cost": "Cost (USD)", "workflow": "Workflow"},
        )
    fig.update_layout(xaxis_tickformat="%b %d")
    style_fig(fig)
    st.plotly_chart(fig, use_container_width=True)
