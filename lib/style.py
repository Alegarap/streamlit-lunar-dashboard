"""Custom CSS polish + dark/light theme toggle.

Native config.toml is set to dark. Toggle switches to light via CSS override.
Dark mode has zero flash. Light mode may briefly show dark on page switch.
"""

import base64

import streamlit as st

# ---------------------------------------------------------------------------
# Shared CSS (both themes)
# ---------------------------------------------------------------------------

SHARED_CSS = """
/* Sidebar: hide the raw "app" entry — we add a proper Home link instead */
[data-testid="stSidebarNav"] li:first-child {
    display: none;
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
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 10px;
    padding: 4px 8px;
    transition: all 0.15s ease;
}
[data-testid="stPageLink"]:hover {
    border-color: #6366F1;
}
"""

# ---------------------------------------------------------------------------
# Dark theme — minimal polish, native config handles backgrounds
# ---------------------------------------------------------------------------

DARK_CSS = "<style>" + SHARED_CSS + "</style>"

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
[data-testid="stSidebarNav"] a { color: #334155 !important; }
[data-testid="stSidebarNav"] a:hover { background-color: #e2e8f0 !important; }

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
    border-color: #6366F1 !important;
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

    # Logo + Home link
    _sidebar_logo()
    with st.sidebar:
        st.page_link("app.py", label="Home", icon="🏠")


def _sidebar_logo():
    """Place Lunar Ventures branding above the navigation."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 64">'
        '<text x="4" y="46" font-family="system-ui,sans-serif" font-size="40" '
        'font-weight="700" fill="#6366F1">&#127769; Lunar Ventures</text>'
        '</svg>'
    )
    svg_b64 = base64.b64encode(svg.encode()).decode()
    data_uri = f"data:image/svg+xml;base64,{svg_b64}"
    try:
        st.logo(data_uri, size="large")
    except TypeError:
        try:
            st.logo(data_uri)
        except Exception:
            pass
    except Exception:
        pass
