"""Shared chart helpers for the Streamlit dashboard."""

import streamlit as st

# Consistent color palette across all pages
COLORS = {
    "linear": "#6366F1",      # Indigo
    "hackernews": "#F97316",   # Orange
    "arxiv": "#EC4899",        # Pink
    "conference": "#14B8A6",   # Teal
    "tigerclaw": "#8B5CF6",    # Violet
    "other": "#94A3B8",        # Slate
}

SOURCE_ORDER = ["linear", "hackernews", "arxiv", "conference", "tigerclaw"]


def metric_row(cols_data: list[tuple[str, str | int | float, str | None]]):
    """Render a row of st.metric() cards.

    cols_data: list of (label, value, delta_or_None)
    """
    cols = st.columns(len(cols_data))
    for col, (label, value, delta) in zip(cols, cols_data):
        col.metric(label, value, delta)


def format_cost(cost: float) -> str:
    """Format a cost value for display."""
    if cost >= 1.0:
        return f"${cost:,.2f}"
    return f"${cost:,.4f}"
