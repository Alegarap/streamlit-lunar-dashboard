"""Shared chart helpers for the Streamlit dashboard."""

from __future__ import annotations

import re
from datetime import datetime

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
    "EXA_CONFERENCE_SOURCING": "Exa: Conference Sourcing",
    "EXA_DEAL_VALIDATION": "Exa: Deal Validation",
    "factory": "Default Key (factory)",
    "unknown": "Unknown",
}


def style_fig(fig):
    """Apply transparent backgrounds, readable grid lines, and safe margins."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=40),
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


def parse_ts(ts):
    """Parse ISO timestamp, stripping timezone info."""
    if not ts:
        return None
    try:
        clean = re.sub(r'[+-]\d{2}:\d{2}$|Z$', '', ts)
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def _safe_md(text):
    """Escape $ signs to prevent Streamlit LaTeX rendering."""
    return text.replace("$", "\\$") if text else text


def item_detail_card(item: dict):
    """Render a single item as a styled detail card (like a Linear issue preview).

    Args:
        item: dict with title, description, summary, source, type, source_date,
              source_url, source_labels, linear_identifier, etc.
    """
    title = item.get("title", "Untitled")
    desc = item.get("description") or item.get("summary") or ""
    source = item.get("source", "")
    item_type = item.get("type", "")
    source_url = item.get("source_url", "")
    linear_id = item.get("linear_identifier", "")
    source_date = item.get("source_date", "")
    labels = item.get("source_labels") or []
    sector_labels = item.get("sector_labels") or []

    source_color = COLORS.get(source, COLORS["other"])

    # Date formatting
    if source_date:
        source_date = str(source_date)[:10]

    # Type badge
    type_color = "#A855F7" if item_type == "theme" else "#F59E0B"
    type_badge = (
        f'<span style="display:inline-block; background:{type_color}22; color:{type_color}; '
        f'border:1px solid {type_color}44; border-radius:4px; padding:1px 8px; '
        f'font-size:0.7rem; font-weight:600; text-transform:uppercase; margin-right:6px;">{item_type}</span>'
    )

    # Source badge
    source_badge = (
        f'<span style="display:inline-block; background:{source_color}22; color:{source_color}; '
        f'border:1px solid {source_color}44; border-radius:4px; padding:1px 8px; '
        f'font-size:0.7rem; font-weight:600; margin-right:6px;">{source}</span>'
    )

    # Linear badge
    linear_badge = ""
    if linear_id:
        linear_badge = (
            f'<span style="display:inline-block; background:rgba(99,102,241,0.15); color:#6366F1; '
            f'border:1px solid rgba(99,102,241,0.3); border-radius:4px; padding:1px 8px; '
            f'font-size:0.7rem; font-weight:600; margin-right:6px;">{linear_id}</span>'
        )

    # Label pills
    label_pills = ""
    all_labels = labels + sector_labels
    if all_labels:
        pills = "".join(
            f'<span style="display:inline-block; background:rgba(148,163,184,0.15); '
            f'border:1px solid rgba(148,163,184,0.25); border-radius:12px; '
            f'padding:1px 8px; font-size:0.65rem; margin:2px 3px 2px 0;">{l}</span>'
            for l in all_labels[:6]
        )
        label_pills = f'<div style="margin-top:8px;">{pills}</div>'

    # Title with link
    title_html = (
        f'<a href="{source_url}" target="_blank" style="color:inherit; text-decoration:none; '
        f'border-bottom:1px solid rgba(255,255,255,0.2);">{_safe_md(title)}</a>'
        if source_url else _safe_md(title)
    )

    # Header
    st.markdown(
        f'<div style="padding:16px 20px; border-radius:12px; '
        f'background:linear-gradient(145deg,#2A3154,#252B45); '
        f'border:1px solid rgba(168,85,247,0.15); '
        f'box-shadow:0 2px 8px rgba(0,0,0,0.3);">'
        f'<div style="display:flex; align-items:center; gap:6px; margin-bottom:8px; flex-wrap:wrap;">'
        f'{type_badge}{source_badge}{linear_badge}'
        f'<span style="font-size:0.75rem; opacity:0.5; margin-left:auto;">{source_date}</span>'
        f'</div>'
        f'<div style="font-size:1.1rem; font-weight:700; margin-bottom:4px;">{title_html}</div>'
        f'{label_pills}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Description body (rendered as markdown, like Linear)
    if desc:
        st.markdown(_safe_md(desc))


def item_detail_viewer(items: list[dict], key_prefix: str):
    """Render a selectbox + detail card for browsing items in a list.

    Args:
        items: list of item dicts (must have 'title', 'description', etc.)
        key_prefix: unique prefix for Streamlit widget keys
    """
    if not items:
        return

    options = {f"{i['title'][:90]} ({i.get('type','')}, {i.get('source','')})": idx
               for idx, i in enumerate(items)}

    selected = st.selectbox(
        "View item details",
        options=["(select an item)"] + list(options.keys()),
        index=0,
        key=f"detail_{key_prefix}",
    )

    if selected and selected != "(select an item)":
        idx = options[selected]
        item_detail_card(items[idx])
