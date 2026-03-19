"""Shared chart helpers for the Streamlit dashboard."""

from __future__ import annotations

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


def style_fig(fig):
    """Apply transparent backgrounds, readable grid lines, and safe margins."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(r=20),
        legend=dict(font=dict(size=12)),
    )
    fig.update_xaxes(gridcolor="rgba(226,232,240,0.15)", gridwidth=1)
    fig.update_yaxes(gridcolor="rgba(226,232,240,0.15)", gridwidth=1)
    return fig


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
