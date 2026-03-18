"""Custom CSS for a polished, modern dashboard look with light/dark theme support.

The native Streamlit theme is set to dark in config.toml, so dark mode has no
white flash on page navigation. Light mode overrides via CSS injection.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Shared CSS (applied in both themes)
# ---------------------------------------------------------------------------

SHARED_CSS = """
/* Sidebar: hide the "app" entry since home is accessible via title */
[data-testid="stSidebarNav"] li:first-child {
    display: none;
}

/* Metric card layout */
[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
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

/* Expanders */
[data-testid="stExpander"] {
    border-radius: 8px !important;
    margin-bottom: 8px;
}

/* Page links */
[data-testid="stPageLink"] {
    border-radius: 10px;
    padding: 4px 8px;
    transition: all 0.15s ease;
}
"""

# ---------------------------------------------------------------------------
# Dark theme — minimal polish on top of native dark theme from config.toml
# ---------------------------------------------------------------------------

DARK_CSS = """
<style>
""" + SHARED_CSS + """

/* Metric card styling */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1E293B 0%, #1A2332 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

/* Expander borders */
[data-testid="stExpander"] {
    border: 1px solid #334155 !important;
}

/* Page links */
[data-testid="stPageLink"] {
    border: 1px solid #334155;
}
[data-testid="stPageLink"]:hover {
    border-color: #6366F1;
    background: #1E293B;
}

/* Divider color */
hr {
    border-color: #334155 !important;
}
</style>
"""

# ---------------------------------------------------------------------------
# Light theme — full override of the native dark theme back to light
# ---------------------------------------------------------------------------

LIGHT_CSS = """
<style>
""" + SHARED_CSS + """

/* Override native dark backgrounds to light */
.stApp, [data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
}
.stApp > header {
    background-color: #FFFFFF !important;
}

/* All text back to dark */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp span, .stApp label, .stApp div,
.stMarkdown, .stMarkdown p, .stMarkdown span,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] code,
[data-testid="stMarkdownContainer"] small {
    color: #1E293B !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

[data-testid="stMetricLabel"] {
    color: #64748b !important;
}

[data-testid="stMetricValue"] {
    color: #1e293b !important;
}

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    background-color: #FFFFFF !important;
}
[data-testid="stExpander"] summary {
    color: #1E293B !important;
}

/* Sidebar */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #1E293B !important;
}
[data-testid="stSidebarNav"] a {
    color: #334155 !important;
}
[data-testid="stSidebarNav"] a:hover {
    background-color: #e2e8f0 !important;
}

/* Tabs */
[data-testid="stTabs"] button {
    color: #64748b !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #1E293B !important;
}

/* Dividers */
hr {
    border-color: #e2e8f0 !important;
}

/* Buttons */
[data-testid="stButton"] button {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
    border-color: #e2e8f0 !important;
}
[data-testid="stButton"] button:hover {
    background-color: #f8fafc !important;
    border-color: #6366F1 !important;
}

/* Page links */
[data-testid="stPageLink"] {
    border: 1px solid #e2e8f0;
}
[data-testid="stPageLink"]:hover {
    border-color: #6366F1;
    background: #f8fafc;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background-color: #f8fafc !important;
    color: #1E293B !important;
}

/* Input fields */
[data-testid="stChatInput"] textarea,
.stChatInput textarea {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
    border-color: #e2e8f0 !important;
}

/* Alerts */
[data-testid="stAlert"] {
    background-color: #f8fafc !important;
    color: #1E293B !important;
    border-color: #e2e8f0 !important;
}

/* Captions */
.stCaption, [data-testid="stCaption"] {
    color: #64748b !important;
}
</style>
"""


def _is_dark() -> bool:
    """Return True if the user has selected dark mode."""
    return st.session_state.get("_theme_dark_persist", True)


def _on_toggle_change():
    """Callback: sync widget key to persistent key."""
    st.session_state._theme_dark_persist = st.session_state._theme_toggle_widget


def theme_toggle():
    """Render a light/dark theme toggle in the sidebar. Call once per page."""
    # Default to dark (matches native config.toml theme)
    if "_theme_dark_persist" not in st.session_state:
        st.session_state._theme_dark_persist = True

    with st.sidebar:
        st.toggle(
            "Dark mode",
            value=st.session_state._theme_dark_persist,
            key="_theme_toggle_widget",
            on_change=_on_toggle_change,
        )


def apply():
    """Inject custom CSS matching the current theme choice."""
    if _is_dark():
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    else:
        st.markdown(LIGHT_CSS, unsafe_allow_html=True)
