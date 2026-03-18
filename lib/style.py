"""Custom CSS polish + dark/light theme toggle + Lunar Ventures branding.

Native config.toml is set to dark. Toggle switches to light via CSS override.
Dark mode has zero flash. Light mode may briefly show dark on page switch.
"""

import base64
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Shared CSS (both themes)
# ---------------------------------------------------------------------------

SHARED_CSS = """
/* Sidebar: hide auto-generated nav — replaced by custom page links */
[data-testid="stSidebarNav"] {
    display: none !important;
}

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
[data-testid="stExpander"] {
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    border-radius: 8px !important;
    margin-bottom: 8px;
}
[data-testid="stTabs"] button {
    font-weight: 500 !important;
}
hr {
    margin: 1.5rem 0 !important;
}
[data-testid="stChatMessage"] {
    border-radius: 12px;
}
[data-testid="stButton"] button {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    transition: all 0.15s ease;
}
[data-testid="stDataFrame"] {
    border-radius: 8px;
}
[data-testid="stPageLink"] {
    border: 1px solid rgba(128, 128, 128, 0.15);
    border-radius: 10px;
    padding: 4px 8px;
    transition: all 0.15s ease;
}
[data-testid="stPageLink"]:hover {
    border-color: #A855F7;
}
"""

# ---------------------------------------------------------------------------
# Dark theme — Lunar gradient sidebar
# ---------------------------------------------------------------------------

DARK_CSS = """
<style>
""" + SHARED_CSS + """

/* Lunar gradient on sidebar */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(195deg, #1a0a2e 0%, #16082b 30%, #1c0a30 60%, #220e35 100%) !important;
}

/* Subtle gradient accent line at top of sidebar */
[data-testid="stSidebar"]::before {
    content: "";
    display: block;
    height: 3px;
    background: linear-gradient(90deg, #EC4899, #A855F7, #6366F1);
    margin: 0 0 0.5rem 0;
}
</style>
"""

# ---------------------------------------------------------------------------
# Light theme — full override from native dark back to light
# ---------------------------------------------------------------------------

LIGHT_CSS = """
<style>
""" + SHARED_CSS + """

.stApp, [data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
}
.stApp > header {
    background-color: #FFFFFF !important;
}

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

[data-testid="stMetricLabel"] { color: #64748b !important; opacity: 1; }
[data-testid="stMetricValue"] { color: #1e293b !important; }

[data-testid="stExpander"] { background-color: #FFFFFF !important; }
[data-testid="stExpander"] summary { color: #1E293B !important; }

/* Light sidebar with subtle Lunar gradient */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(195deg, #fdf4ff 0%, #faf5ff 30%, #f5f3ff 60%, #eef2ff 100%) !important;
}
[data-testid="stSidebar"]::before {
    content: "";
    display: block;
    height: 3px;
    background: linear-gradient(90deg, #EC4899, #A855F7, #6366F1);
    margin: 0 0 0.5rem 0;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #1E293B !important;
}

[data-testid="stTabs"] button { color: #64748b !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #1E293B !important; }

hr { border-color: #e2e8f0 !important; }

[data-testid="stButton"] button {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
    border-color: #e2e8f0 !important;
}
[data-testid="stButton"] button:hover {
    background-color: #f8fafc !important;
    border-color: #A855F7 !important;
}

[data-testid="stChatMessage"] {
    background-color: #f8fafc !important;
    color: #1E293B !important;
}

[data-testid="stChatInput"] textarea,
.stChatInput textarea {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
    border-color: #e2e8f0 !important;
}

[data-testid="stAlert"] {
    background-color: #f8fafc !important;
    color: #1E293B !important;
    border-color: #e2e8f0 !important;
}

.stCaption, [data-testid="stCaption"] { color: #64748b !important; }
</style>
"""


def _is_dark() -> bool:
    return st.session_state.get("_theme_dark_persist", True)


def _on_toggle_change():
    st.session_state._theme_dark_persist = st.session_state._theme_toggle_widget


def apply():
    """Inject CSS + render theme toggle + branding. Call once per page."""
    # Theme toggle
    if "_theme_dark_persist" not in st.session_state:
        st.session_state._theme_dark_persist = True

    with st.sidebar:
        st.toggle(
            "Dark mode",
            value=st.session_state._theme_dark_persist,
            key="_theme_toggle_widget",
            on_change=_on_toggle_change,
        )

    # CSS
    if _is_dark():
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    else:
        st.markdown(LIGHT_CSS, unsafe_allow_html=True)

    # Logo + navigation
    _sidebar_logo()
    with st.sidebar:
        st.page_link("app.py", label="Home", icon="🏠")
        st.page_link("pages/4_Ask_Data.py", label="Ask Data", icon="🤖")
        st.page_link("pages/1_Ingestion.py", label="Ingestion", icon="📊")
        st.page_link("pages/2_Cost_Tracking.py", label="Cost Tracking", icon="💰")
        st.page_link("pages/3_Clusters.py", label="Clusters", icon="🔬")
        st.divider()


def _sidebar_logo():
    """Place Lunar Ventures logo above the navigation."""
    logo_path = Path(__file__).resolve().parent.parent / "static" / "logo.png"
    try:
        if logo_path.exists():
            st.logo(str(logo_path), size="large")
        else:
            # Fallback to text SVG
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 64">'
                '<text x="4" y="46" font-family="system-ui,sans-serif" font-size="40" '
                'font-weight="700" fill="#A855F7">Lunar Ventures</text>'
                '</svg>'
            )
            svg_b64 = base64.b64encode(svg.encode()).decode()
            st.logo(f"data:image/svg+xml;base64,{svg_b64}", size="large")
    except TypeError:
        # Older Streamlit without size param
        try:
            st.logo(str(logo_path))
        except Exception:
            pass
    except Exception:
        pass
