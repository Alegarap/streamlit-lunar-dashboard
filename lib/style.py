"""Custom CSS polish that works with both Streamlit's native light and dark themes.

Theme switching is handled by Streamlit's built-in Settings menu
(hamburger → Settings → Theme). No custom toggle needed — no flash.
"""

import streamlit as st

CUSTOM_CSS = """
<style>
/* Sidebar: hide the "app" entry since home is accessible via title */
[data-testid="stSidebarNav"] li:first-child {
    display: none;
}

/* Metric card styling — uses transparent overlays that work in both themes */
[data-testid="stMetric"] {
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    opacity: 0.7;
}

[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
}

/* Cleaner expanders */
[data-testid="stExpander"] {
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    border-radius: 8px !important;
    margin-bottom: 8px;
}

/* Tabs */
[data-testid="stTabs"] button {
    font-weight: 500 !important;
}

/* Dividers */
hr {
    margin: 1.5rem 0 !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    border-radius: 12px;
}

/* Buttons */
[data-testid="stButton"] button {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    transition: all 0.15s ease;
}

/* DataFrames */
[data-testid="stDataFrame"] {
    border-radius: 8px;
}

/* Page links */
[data-testid="stPageLink"] {
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 10px;
    padding: 4px 8px;
    transition: all 0.15s ease;
}
[data-testid="stPageLink"]:hover {
    border-color: #6366F1;
}

/* Branding logo area */
.sidebar-brand {
    padding: 0.5rem 0 1rem 0;
    border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    margin-bottom: 0.75rem;
}
.sidebar-brand h3 {
    margin: 0 !important;
    padding: 0 !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
}
.sidebar-brand p {
    margin: 0 !important;
    font-size: 0.7rem !important;
    opacity: 0.5;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
</style>
"""


def apply():
    """Inject custom CSS polish. Works with both native light and dark themes."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def sidebar_brand():
    """Render the Lunar Ventures branding in the sidebar."""
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">'
            '<h3>🌙 Lunar Ventures</h3>'
            '<p>BI Dashboard</p>'
            '</div>',
            unsafe_allow_html=True,
        )
