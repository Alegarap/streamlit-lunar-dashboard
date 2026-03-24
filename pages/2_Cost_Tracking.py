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
from lib.charts import format_cost, style_fig, workflow_display_name

style.apply()
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
    df["total_input_tokens"] = (
        pd.to_numeric(df["total_input_tokens"], errors="coerce").fillna(0).astype(int)
    )
if "total_output_tokens" in df.columns:
    df["total_output_tokens"] = (
        pd.to_numeric(df["total_output_tokens"], errors="coerce").fillna(0).astype(int)
    )
if "request_count" in df.columns:
    df["request_count"] = (
        pd.to_numeric(df["request_count"], errors="coerce").fillna(0).astype(int)
    )
else:
    df["request_count"] = 1

# Map workflow keys to human-readable names
if "workflow_key" in df.columns:
    df["workflow"] = df["workflow_key"].apply(workflow_display_name)

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
ninety_start = today - timedelta(days=89)
all_cost, all_reqs = cost_for_period(ninety_start)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Today", format_cost(today_cost), f"{int(today_reqs)} reqs")
c2.metric("This Week", format_cost(week_cost), f"{int(week_reqs)} reqs")
c3.metric("This Month", format_cost(month_cost), f"{int(month_reqs)} reqs")
c4.metric("90d Total", format_cost(all_cost), f"{int(all_reqs)} reqs")

# --- Provider breakdown (inline caption) ---
if "api_type" in df.columns:
    exa_mask = df["api_type"] == "exa"
    exa_cost = df.loc[exa_mask, "total_cost"].sum()
    openrouter_cost = df.loc[~exa_mask, "total_cost"].sum()
    exa_reqs = int(df.loc[exa_mask, "request_count"].sum())
    or_reqs = int(df.loc[~exa_mask, "request_count"].sum())

    parts = [f"OpenRouter {format_cost(openrouter_cost)} ({or_reqs} reqs)"]
    if exa_cost > 0:
        parts.append(f"Exa {format_cost(exa_cost)} ({exa_reqs} reqs)")
    st.caption(" · ".join(parts))

# --- Chart helper ---
CHART_FONT = dict(family="Fira Sans, sans-serif", size=13)


def _style_chart(fig, height=380, dollar_y=True):
    """Style a plotly figure with Fira Sans, legend size 13, transparent bg."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=40, t=50, b=40),
        legend=dict(font=CHART_FONT),
        font=CHART_FONT,
        height=height,
    )
    fig.update_xaxes(gridcolor="rgba(226,232,240,0.15)", gridwidth=1)
    fig.update_yaxes(gridcolor="rgba(226,232,240,0.15)", gridwidth=1)
    if dollar_y:
        fig.update_yaxes(tickprefix="$")
    return fig


# --- Two-column chart layout ---
left, right = st.columns(2)

with left:
    daily = (
        df.groupby("day")
        .agg({"total_cost": "sum"})
        .reset_index()
        .sort_values("day")
    )
    if len(daily) > 1:
        fig = px.area(
            daily, x="day", y="total_cost",
            labels={"day": "Date", "total_cost": "Cost"},
        )
    else:
        fig = px.bar(
            daily, x="day", y="total_cost",
            labels={"day": "Date", "total_cost": "Cost"},
        )
    fig.update_layout(title="Daily Cost Trend", xaxis_tickformat="%b %d")
    _style_chart(fig, height=380)
    st.plotly_chart(fig, use_container_width=True)

with right:
    if "workflow" in df.columns:
        by_wf = (
            df.groupby("workflow")
            .agg({"total_cost": "sum"})
            .reset_index()
            .sort_values("total_cost", ascending=True)
        )
        fig = px.bar(
            by_wf, x="total_cost", y="workflow",
            orientation="h",
            labels={"total_cost": "Cost", "workflow": "Workflow"},
        )
        fig.update_layout(title="Cost by Workflow")
        _style_chart(fig, height=380)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No workflow breakdown available in current data.")

# --- Cost by Model table ---
if "model" in df.columns:
    st.subheader("Cost by Model")
    agg_cols = {"total_cost": "sum", "request_count": "sum"}
    if "total_input_tokens" in df.columns:
        agg_cols["total_input_tokens"] = "sum"
    if "total_output_tokens" in df.columns:
        agg_cols["total_output_tokens"] = "sum"
    by_model = (
        df.groupby("model")
        .agg(agg_cols)
        .reset_index()
        .sort_values("total_cost", ascending=False)
    )

    max_cost = by_model["total_cost"].max() if len(by_model) > 0 else 1.0

    rename_map = {
        "model": "Model",
        "total_cost": "Cost",
        "request_count": "Requests",
        "total_input_tokens": "Input Tokens",
        "total_output_tokens": "Output Tokens",
    }
    display_df = by_model.rename(columns=rename_map)

    col_config = {
        "Cost": st.column_config.ProgressColumn(
            "Cost",
            format="$%.4f",
            min_value=0,
            max_value=float(max_cost),
        ),
        "Requests": st.column_config.NumberColumn(format="%d"),
    }
    if "Input Tokens" in display_df.columns:
        col_config["Input Tokens"] = st.column_config.NumberColumn(format="%d")
    if "Output Tokens" in display_df.columns:
        col_config["Output Tokens"] = st.column_config.NumberColumn(format="%d")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
    )

# --- Daily Cost by Workflow (full width stacked area) ---
if "workflow" in df.columns:
    daily_wf = (
        df.groupby(["day", "workflow"])
        .agg({"total_cost": "sum"})
        .reset_index()
        .sort_values("day")
    )
    if len(daily_wf) > 1:
        fig = px.area(
            daily_wf, x="day", y="total_cost", color="workflow",
            labels={"day": "Date", "total_cost": "Cost", "workflow": "Workflow"},
        )
    else:
        fig = px.bar(
            daily_wf, x="day", y="total_cost", color="workflow",
            labels={"day": "Date", "total_cost": "Cost", "workflow": "Workflow"},
        )
    fig.update_layout(
        title="Daily Cost by Workflow",
        xaxis_tickformat="%b %d",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=CHART_FONT,
        ),
    )
    _style_chart(fig, height=350)
    st.plotly_chart(fig, use_container_width=True)
