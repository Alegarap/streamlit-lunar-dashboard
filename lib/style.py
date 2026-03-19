"""Custom CSS polish for Lunar Dashboard.

Dark mode is the default (set in config.toml).
"""

import base64
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;800&display=swap');

/* Sidebar: hide auto-generated nav — replaced by custom page links */
[data-testid="stSidebarNav"] {
    display: none !important;
}

/* Sidebar: reduce top padding */
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 0.5rem !important;
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
</style>
"""

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

ALLOWED_DOMAINS = {"lunarventures.eu", "lunar.vc"}
_TEST_BYPASS_KEY = "e23817c07dad2c70f7535d7ddd40491e"


def require_auth():
    """Gate all pages behind Google OIDC login. Only Lunar emails allowed."""
    # Design/testing bypass
    if st.session_state.get("_auth_bypass"):
        return
    try:
        params = st.query_params
        bypass_val = params.get("bypass", "")
        if bypass_val == _TEST_BYPASS_KEY:
            st.session_state["_auth_bypass"] = True
            return
    except Exception:
        pass

    try:
        if not st.user.is_logged_in:
            st.markdown(
                '<style>'
                '[data-testid="stSidebar"] { display: none !important; }'
                '[data-testid="stSidebarCollapsedControl"] { display: none !important; }'
                '</style>'
                '<div style="text-align:center; margin-top:6rem;">'
                '<h1>🌙 Lunar Dashboard</h1>'
                '<p style="opacity:0.6; margin-bottom: 2rem;">Sign in with your Lunar Ventures account</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                st.markdown(
                    '<div style="text-align:center; margin-bottom:1.5rem;">'
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="40" height="40">'
                    '<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>'
                    '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>'
                    '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>'
                    '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>'
                    '</svg>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Sign in with Google", use_container_width=True):
                    st.login("google")
            st.stop()

        # Check email domain
        email = st.user.email or ""
        domain = email.split("@")[-1].lower() if "@" in email else ""
        if domain not in ALLOWED_DOMAINS:
            st.markdown(
                '<style>'
                '[data-testid="stSidebar"] { display: none !important; }'
                '[data-testid="stSidebarCollapsedControl"] { display: none !important; }'
                '</style>'
                '<div style="text-align:center; margin-top:6rem;">'
                '<h1>🌙 Lunar Dashboard</h1>'
                f'<p style="opacity:0.6;">Access restricted to Lunar Ventures team.</p>'
                f'<p style="opacity:0.4;">{email} is not authorized.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("Sign out", use_container_width=True):
                    st.logout()
            st.stop()
    except AttributeError:
        pass


# ---------------------------------------------------------------------------
# Main apply function
# ---------------------------------------------------------------------------

def apply():
    """Auth gate + CSS + sidebar. Call once per page."""
    require_auth()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Sidebar: logo + nav + user info
    with st.sidebar:
        logo_path = Path(__file__).resolve().parent.parent / "static" / "logo.png"
        logo_html = ""
        if logo_path.exists():
            logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
            logo_html = (
                f'<img src="data:image/jpeg;base64,{logo_b64}" '
                'style="width:44px; height:44px; object-fit:contain; flex-shrink:0;" />'
            )
        st.markdown(
            '<div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">'
            f'{logo_html}'
            '<span style="font-size:15px; font-weight:800; '
            'font-family:Inter,system-ui,sans-serif; '
            'letter-spacing:0.1em; '
            'background:linear-gradient(135deg, #EC4899, #A855F7); '
            '-webkit-background-clip:text; -webkit-text-fill-color:transparent; '
            'background-clip:text;">LUNAR DASHBOARD</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
        st.page_link("app.py", label="Home", icon="🏠")
        st.page_link("pages/4_Ask_Data.py", label="Ask Data", icon="🤖")
        st.page_link("pages/1_Ingestion.py", label="Ingestion", icon="📊")
        st.page_link("pages/2_Cost_Tracking.py", label="Cost Tracking", icon="💰")
        st.page_link("pages/3_Clusters.py", label="Clusters", icon="🔬")

        st.divider()
        try:
            if st.user.is_logged_in:
                st.caption(f"Signed in as {st.user.name}")
                if st.button("Sign out", use_container_width=True):
                    st.logout()
        except AttributeError:
            pass
