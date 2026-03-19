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

/* Force wide layout on all pages */
[data-testid="stAppViewBlockContainer"] {
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}
.block-container {
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
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

/* Lunar neon gradient on sidebar */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(160deg, #2d0a3e 0%, #1a0832 35%, #250d42 65%, #3b1055 100%) !important;
}

/* Bold gradient accent line at top of sidebar */
[data-testid="stSidebar"]::before {
    content: "";
    display: block;
    height: 4px;
    background: linear-gradient(90deg, #F472B6, #D946EF, #A855F7, #7C3AED);
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

/* Light sidebar with Lunar gradient */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(160deg, #fdf2f8 0%, #faf5ff 35%, #f3e8ff 65%, #ede9fe 100%) !important;
}
[data-testid="stSidebar"]::before {
    content: "";
    display: block;
    height: 4px;
    background: linear-gradient(90deg, #F472B6, #D946EF, #A855F7, #7C3AED);
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


def require_auth():
    """Gate all pages behind Google OIDC login. Call before any content."""
    try:
        if not st.user.is_logged_in:
            st.markdown(
                '<div style="text-align:center; margin-top:4rem;">'
                '<h2>🌙 Lunar Dashboard</h2>'
                '<p style="opacity:0.6;">Sign in to access the dashboard</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("Sign in with Google", use_container_width=True):
                    st.login("google")
            st.stop()
    except AttributeError:
        # st.user not available (older Streamlit or auth not configured)
        pass


def apply():
    """Auth gate + CSS + branding. Call once per page."""
    require_auth()

    # Dark mode is the default. To switch themes, change `base` in
    # .streamlit/config.toml ("dark" or "light") and redeploy.
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    # Logo + navigation
    _sidebar_logo()
    with st.sidebar:
        st.page_link("app.py", label="Home", icon="🏠")
        st.page_link("pages/4_Ask_Data.py", label="Ask Data", icon="🤖")
        st.page_link("pages/1_Ingestion.py", label="Ingestion", icon="📊")
        st.page_link("pages/2_Cost_Tracking.py", label="Cost Tracking", icon="💰")
        st.page_link("pages/3_Clusters.py", label="Clusters", icon="🔬")
        st.divider()
        # User info + logout
        try:
            if st.user.is_logged_in:
                st.caption(f"Signed in as {st.user.name}")
                if st.button("Sign out", use_container_width=True):
                    st.logout()
        except AttributeError:
            pass


def _sidebar_logo():
    """Place Lunar Ventures logo + 'Lunar Dashboard' text above the navigation."""
    logo_path = Path(__file__).resolve().parent.parent / "static" / "logo.png"

    # Build a composite SVG with the logo image embedded + text
    try:
        if logo_path.exists():
            logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink" '
                'viewBox="0 0 320 48">'
                f'<image href="data:image/png;base64,{logo_b64}" '
                'x="0" y="0" width="48" height="48" />'
                '<text x="56" y="22" font-family="system-ui,sans-serif" '
                'font-size="21" font-weight="700" fill="#D946EF">'
                'Lunar</text>'
                '<text x="56" y="42" font-family="system-ui,sans-serif" '
                'font-size="21" font-weight="700" fill="#A855F7">'
                'Dashboard</text>'
                '</svg>'
            )
        else:
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 48">'
                '<text x="4" y="22" font-family="system-ui,sans-serif" '
                'font-size="21" font-weight="700" fill="#D946EF">'
                'Lunar</text>'
                '<text x="4" y="42" font-family="system-ui,sans-serif" '
                'font-size="21" font-weight="700" fill="#A855F7">'
                'Dashboard</text>'
                '</svg>'
            )

        svg_b64 = base64.b64encode(svg.encode()).decode()
        data_uri = f"data:image/svg+xml;base64,{svg_b64}"
        try:
            st.logo(data_uri, size="large")
        except TypeError:
            st.logo(data_uri)
    except Exception:
        pass
