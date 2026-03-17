"""Custom CSS for a polished, modern dashboard look with light/dark theme support."""

import streamlit as st

# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------

LIGHT_CSS = """
<style>
/* --- LIGHT THEME --- */

/* Clean metric cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
    color: #64748b !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #1e293b !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
}

/* Cleaner expanders */
[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    margin-bottom: 8px;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}

/* Sidebar: hide the "app" entry since home is accessible via title */
[data-testid="stSidebarNav"] li:first-child {
    display: none;
}

/* Tabs */
[data-testid="stTabs"] button {
    font-weight: 500 !important;
}

/* Dividers */
hr {
    margin: 1.5rem 0 !important;
    border-color: #e2e8f0 !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    border-radius: 12px;
}

/* Quick query buttons */
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
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 4px 8px;
    transition: all 0.15s ease;
}
[data-testid="stPageLink"]:hover {
    border-color: #6366F1;
    background: #f8fafc;
}
</style>
"""

DARK_CSS = """
<style>
/* --- DARK THEME --- */

/* Main app background */
.stApp, [data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    background-color: #0F172A !important;
    color: #E2E8F0 !important;
}

.stApp > header {
    background-color: #0F172A !important;
}

/* All text elements */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp span, .stApp label, .stApp div,
.stMarkdown, .stMarkdown p, .stMarkdown span,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] code,
[data-testid="stMarkdownContainer"] small {
    color: #E2E8F0 !important;
}

/* Clean metric cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1E293B 0%, #1A2332 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
    color: #94A3B8 !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #F1F5F9 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
}

/* Cleaner expanders */
[data-testid="stExpander"] {
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    margin-bottom: 8px;
    background-color: #1E293B !important;
}
[data-testid="stExpander"] summary {
    color: #E2E8F0 !important;
}

/* Sidebar styling */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%) !important;
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #E2E8F0 !important;
}

/* Sidebar: hide the "app" entry since home is accessible via title */
[data-testid="stSidebarNav"] li:first-child {
    display: none;
}

/* Sidebar nav links */
[data-testid="stSidebarNav"] a {
    color: #CBD5E1 !important;
}
[data-testid="stSidebarNav"] a:hover {
    color: #F1F5F9 !important;
    background-color: #334155 !important;
}

/* Tabs */
[data-testid="stTabs"] button {
    font-weight: 500 !important;
    color: #94A3B8 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #E2E8F0 !important;
}

/* Dividers */
hr {
    margin: 1.5rem 0 !important;
    border-color: #334155 !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    border-radius: 12px;
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
}

/* Quick query buttons */
[data-testid="stButton"] button {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    transition: all 0.15s ease;
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
    border-color: #334155 !important;
}
[data-testid="stButton"] button:hover {
    background-color: #334155 !important;
    border-color: #6366F1 !important;
}

/* DataFrames — dark theme for the embedded component */
[data-testid="stDataFrame"] {
    border-radius: 8px;
}
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] [data-testid="glide-data-grid-canvas"],
[data-testid="stDataFrame"] .gdg-style {
    color-scheme: dark !important;
}
/* Dark background for dataframe container */
[data-testid="stDataFrame"] > div > div {
    background-color: #1E293B !important;
}
/* Column headers */
[data-testid="stDataFrame"] [role="columnheader"] {
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
}

/* Table element (st.table) */
.stTable, .stTable table {
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
}
.stTable th {
    background-color: #0F172A !important;
    color: #94A3B8 !important;
}
.stTable td {
    color: #E2E8F0 !important;
    border-color: #334155 !important;
}

/* Page links */
[data-testid="stPageLink"] {
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 4px 8px;
    transition: all 0.15s ease;
}
[data-testid="stPageLink"]:hover {
    border-color: #6366F1;
    background: #1E293B;
}

/* Input fields */
[data-testid="stTextInput"] input,
[data-testid="stChatInput"] textarea,
.stChatInput textarea,
.stTextInput input {
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
    border-color: #334155 !important;
}

/* Select boxes */
.stSelectbox div[data-baseweb="select"] {
    background-color: #1E293B !important;
}
.stSelectbox div[data-baseweb="select"] span {
    color: #E2E8F0 !important;
}

/* Info/Warning boxes */
[data-testid="stAlert"] {
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
    border-color: #334155 !important;
}

/* Captions */
.stCaption, [data-testid="stCaption"] {
    color: #94A3B8 !important;
}

/* Toggle label */
.stToggle label span {
    color: #E2E8F0 !important;
}

/* Column config NumberColumn, ProgressColumn */
[data-testid="stDataFrame"] [role="gridcell"] {
    color: #E2E8F0 !important;
}
</style>
"""


def _is_dark() -> bool:
    """Return True if the user has selected dark mode."""
    return st.session_state.get("_theme_dark_persist", False)


def _on_toggle_change():
    """Callback: sync widget key to persistent key."""
    st.session_state._theme_dark_persist = st.session_state._theme_toggle_widget


def theme_toggle():
    """Render a light/dark theme toggle in the sidebar. Call once per page."""
    # Initialize persistent key if needed
    if "_theme_dark_persist" not in st.session_state:
        st.session_state._theme_dark_persist = False

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
