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
from lib.charts import format_cost, metric_row

st.title("Cost Tracking")

# --- Check if cost_log table / RPC exists ---
try:
    cost_data = sb.rpc_call("get_cost_stats", {"p_days": 90})
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
        "No cost data yet. The n8n Broadcast Receiver needs to be updated to write to "
        "the `cost_log` table. Cost data will appear here once that's configured."
    )
    st.stop()

# --- Process data ---
df = pd.DataFrame(cost_data)
df["day"] = pd.to_datetime(df["day"])
df["total_cost"] = pd.to_numeric(df["total_cost"], errors="coerce").fillna(0)
df["total_input_tokens"] = pd.to_numeric(df.get("total_input_tokens", 0), errors="coerce").fillna(0).astype(int)
df["total_output_tokens"] = pd.to_numeric(df.get("total_output_tokens", 0), errors="coerce").fillna(0).astype(int)
df["request_count"] = pd.to_numeric(df.get("request_count", 0), errors="coerce").fillna(0).astype(int)

today = datetime.now().date()


# --- Scorecards ---
def cost_for_period(start_date, end_date=None):
    end_date = end_date or today
    mask = (df["day"].dt.date >= start_date) & (df["day"].dt.date <= end_date)
    subset = df[mask]
    return subset["total_cost"].sum(), subset["request_count"].sum()


today_cost, today_reqs = cost_for_period(today)
week_start = today - timedelta(days=today.weekday())
week_cost, week_reqs = cost_for_period(week_start)
month_start = today.replace(day=1)
month_cost, month_reqs = cost_for_period(month_start)
all_cost, all_reqs = df["total_cost"].sum(), df["request_count"].sum()

metric_row([
    ("Today", format_cost(today_cost), f"{int(today_reqs)} requests"),
    ("This Week", format_cost(week_cost), f"{int(week_reqs)} requests"),
    ("This Month", format_cost(month_cost), f"{int(month_reqs)} requests"),
    ("All Time (90d)", format_cost(all_cost), f"{int(all_reqs)} requests"),
])

st.divider()

# --- Cost trend ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Daily Cost Trend")
    daily = df.groupby("day").agg({"total_cost": "sum"}).reset_index()
    if len(daily) > 1:
        fig = px.area(
            daily, x="day", y="total_cost",
            title="Daily Spend",
            labels={"day": "Date", "total_cost": "Cost ($)"},
        )
    else:
        fig = px.bar(
            daily, x="day", y="total_cost",
            title="Daily Spend",
            labels={"day": "Date", "total_cost": "Cost ($)"},
        )
    fig.update_layout(xaxis_tickformat="%b %d")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Cost by Workflow")
    if "workflow_key" in df.columns:
        by_wf = df.groupby("workflow_key").agg({"total_cost": "sum"}).reset_index()
        by_wf = by_wf.sort_values("total_cost", ascending=True)
        fig = px.bar(
            by_wf, x="total_cost", y="workflow_key",
            orientation="h",
            title="Total Spend by Workflow",
            labels={"total_cost": "Cost ($)", "workflow_key": "Workflow"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No workflow breakdown available in current data.")

# --- Cost by model ---
if "model" in df.columns:
    st.subheader("Cost by Model")
    agg_cols = {"total_cost": "sum", "request_count": "sum"}
    if "total_input_tokens" in df.columns:
        agg_cols["total_input_tokens"] = "sum"
    if "total_output_tokens" in df.columns:
        agg_cols["total_output_tokens"] = "sum"
    by_model = df.groupby("model").agg(agg_cols).reset_index().sort_values("total_cost", ascending=False)

    rename_map = {
        "model": "Model",
        "total_cost": "Total Cost ($)",
        "request_count": "Requests",
        "total_input_tokens": "Input Tokens",
        "total_output_tokens": "Output Tokens",
    }
    st.dataframe(
        by_model.rename(columns=rename_map),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Cost ($)": st.column_config.NumberColumn(format="$%.4f"),
        },
    )

# --- Cost by workflow over time ---
if "workflow_key" in df.columns:
    st.subheader("Daily Cost by Workflow")
    daily_wf = df.groupby(["day", "workflow_key"]).agg({"total_cost": "sum"}).reset_index()
    if len(daily_wf) > 1:
        fig = px.area(
            daily_wf, x="day", y="total_cost", color="workflow_key",
            title="Cost Breakdown Over Time",
            labels={"day": "Date", "total_cost": "Cost ($)", "workflow_key": "Workflow"},
        )
    else:
        fig = px.bar(
            daily_wf, x="day", y="total_cost", color="workflow_key",
            title="Cost Breakdown Over Time",
            labels={"day": "Date", "total_cost": "Cost ($)", "workflow_key": "Workflow"},
        )
    fig.update_layout(xaxis_tickformat="%b %d")
    st.plotly_chart(fig, use_container_width=True)
