"""Custom CSS for a polished, modern dashboard look."""

import streamlit as st

CUSTOM_CSS = """
<style>
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


def apply():
    """Inject custom CSS into the Streamlit page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
