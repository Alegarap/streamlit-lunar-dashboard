"""Shared chart helpers for the Streamlit dashboard."""

from __future__ import annotations

import plotly.graph_objects as go
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

# Human-readable names for workflow keys (from OpenRouter API key names)
WORKFLOW_NAMES = {
    "OPENROUTER_KEY_TT_RESEARCH_THEMES": "Research Themes",
    "OPENROUTER_KEY_TT_DEEP_RESEARCH_RESULTS": "Deep Research",
    "OPENROUTER_KEY_TT_SETUP_FIND_ALL": "Setup Find All",
    "OPENROUTER_KEY_TT_CHECK_PUSH_CANDIDATES": "Check & Push Candidates",
    "OPENROUTER_KEY_AS_AMBIENT_SOURCING": "Ambient Sourcing",
    "OPENROUTER_KEY_AS_HN_SOURCING": "HN Sourcing",
    "OPENROUTER_KEY_AS_ACADEMIC_SOURCING": "Academic Sourcing",
    "OPENROUTER_KEY_AS_CONFERENCE_SOURCING": "Conference Sourcing",
    "OPENROUTER_KEY_DEAL_VALIDATION": "Deal Validation",
    "OPENROUTER_KEY_FALLBACK": "Fallback",
    "OPENROUTER_KEY_CHOP_SHOP": "Chop Shop",
    "OPENROUTER_KEY_STREAMLIT": "Streamlit Dashboard",
    "Streamlit Dashboard": "Streamlit Dashboard",
    "factory": "Default Key (factory)",
    "unknown": "Unknown",
}


def workflow_display_name(key: str) -> str:
    """Convert a workflow key like OPENROUTER_KEY_FALLBACK to a human-readable name."""
    return WORKFLOW_NAMES.get(key, key)


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


def plotly_theme_layout() -> dict:
    """Return Plotly layout kwargs matching the current light/dark theme."""
    if st.session_state.get("theme_dark", False):
        return dict(
            paper_bgcolor="#0F172A",
            plot_bgcolor="#1E293B",
            font_color="#E2E8F0",
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="#334155"),
            legend=dict(font=dict(color="#E2E8F0")),
        )
    return {}


def apply_plotly_theme(fig: go.Figure) -> go.Figure:
    """Apply the current theme to a Plotly figure and return it."""
    layout_kwargs = plotly_theme_layout()
    if layout_kwargs:
        fig.update_layout(**layout_kwargs)
    return fig
