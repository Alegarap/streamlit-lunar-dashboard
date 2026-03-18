"""Custom CSS polish that works with both Streamlit's native light and dark themes.

Theme switching: use Streamlit's built-in menu (⋮ → Settings → Theme).
"""

import streamlit as st

CUSTOM_CSS = """
<style>
/* Sidebar: hide the "app" entry since home is accessible via title */
[data-testid="stSidebarNav"] li:first-child {
    display: none;
}

/* Metric card styling — transparent overlays work in both themes */
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

/* Expanders */
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
</style>
"""


def apply():
    """Inject custom CSS polish. Works with both native light and dark themes."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def sidebar_brand():
    """Render the Lunar Ventures logo at the top of the sidebar using st.logo()."""
    # st.logo() places the image above the navigation — the only way to
    # get content above the auto-generated page links.
    # Using a data URI SVG so no external file is needed.
    import base64

    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 40">
      <text x="28" y="26" font-family="sans-serif" font-size="18" font-weight="600" fill="#6366F1">🌙 Lunar Ventures</text>
    </svg>"""
    svg_b64 = base64.b64encode(svg.encode()).decode()
    data_uri = f"data:image/svg+xml;base64,{svg_b64}"

    try:
        st.logo(data_uri)
    except Exception:
        # st.logo() not available in older Streamlit — fall back to sidebar markdown
        with st.sidebar:
            st.markdown("**🌙 Lunar Ventures**")
