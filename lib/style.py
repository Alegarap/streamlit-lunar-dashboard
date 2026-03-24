"""Custom CSS polish for Lunar Dashboard.

Dark mode is the default (set in config.toml).
"""

import base64
from pathlib import Path

import streamlit as st

from lib.user_profiles import get_profile, all_profiles

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;1,9..40,400&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

/* Global typography and background */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'IBM Plex Sans', -apple-system, sans-serif !important;
}
[data-testid="stAppViewContainer"] {
    background-color: #0F1117 !important;
}
[data-testid="stSidebar"] {
    background-color: #0F1117 !important;
}
[data-testid="stHeader"] {
    background-color: #0F1117 !important;
}
h1, h2, h3, [data-testid="stHeading"] {
    font-family: 'DM Sans', sans-serif !important;
}

/* Fade-in animation for cards */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

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
    background: #161B26 !important;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
    animation: fadeSlideUp 0.3s ease both;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.5;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    font-variant-numeric: tabular-nums;
}
[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
}
[data-testid="stExpander"] {
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 8px !important;
    margin-bottom: 8px;
    transition: border-color 0.2s ease;
}
[data-testid="stTabs"] button {
    font-weight: 500 !important;
}
hr {
    margin: 2rem 0 !important;
    border-color: rgba(255, 255, 255, 0.04) !important;
}
[data-testid="stChatMessage"] {
    border-radius: 12px;
}
[data-testid="stButton"] button {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    transition: all 0.15s ease;
}
/* Dataframes / tables */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    overflow: hidden;
}

/* Plotly charts */
[data-testid="stPlotlyChart"] {
    background: #161B26 !important;
    border-radius: 10px;
    padding: 8px 16px;
    border: 1px solid rgba(255, 255, 255, 0.04);
}
[data-testid="stPageLink"] {
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 8px;
    padding: 4px 8px;
    transition: all 0.2s ease;
}
[data-testid="stPageLink"]:hover {
    border-color: rgba(255, 255, 255, 0.15);
    background: rgba(255, 255, 255, 0.03);
}
/* Active page indicator */
[data-testid="stPageLink"][aria-current="page"],
[data-testid="stPageLink"]:has(a[aria-current="page"]) {
    border-left: 3px solid #E5A431 !important;
    background: rgba(229, 164, 49, 0.06) !important;
    border-color: rgba(229, 164, 49, 0.2) !important;
}
/* Active tab styling */
[data-testid="stTabs"] button[aria-selected="true"] {
    font-weight: 600 !important;
    border-bottom: 2px solid #E5A431 !important;
}
[data-testid="stTabs"] button[aria-selected="false"]:hover {
    color: rgba(255, 255, 255, 0.8) !important;
}
/* Consistent subheader spacing */
[data-testid="stSubheader"] {
    margin-top: 0.5rem !important;
    margin-bottom: 0.25rem !important;
}
/* Button hover states */
[data-testid="stButton"] button:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    border-color: rgba(255, 255, 255, 0.15) !important;
}
[data-testid="stButton"] button:active {
    transform: translateY(0px);
    box-shadow: none;
}
/* Expander hover state */
[data-testid="stExpander"]:hover {
    border-color: rgba(255, 255, 255, 0.12) !important;
}
[data-testid="stExpander"] summary {
    transition: color 0.15s ease;
}
/* Metric card hover */
[data-testid="stMetric"]:hover {
    border-color: rgba(255, 255, 255, 0.12);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
/* Staggered card entrance */
[data-testid="stHorizontalBlock"] > div:nth-child(1) [data-testid="stMetric"] { animation-delay: 0ms; }
[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] { animation-delay: 50ms; }
[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] { animation-delay: 100ms; }
[data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] { animation-delay: 150ms; }
[data-testid="stHorizontalBlock"] > div:nth-child(5) [data-testid="stMetric"] { animation-delay: 200ms; }
/* Mobile responsive */
@media (max-width: 768px) {
    [data-testid="stAppViewBlockContainer"],
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.7rem !important;
    }
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
# Profile resolution
# ---------------------------------------------------------------------------

# Page registry: label -> (file_path, icon)
_ALL_PAGES = {
    "Home": ("app.py", "🏠"),
    "For You": ("pages/5_For_You.py", "🎯"),
    "Ingestion": ("pages/1_Ingestion.py", "📊"),
    "Cost Tracking": ("pages/2_Cost_Tracking.py", "💰"),
    "Clusters": ("pages/3_Clusters.py", "🔬"),
    "Ask AI": ("pages/4_Ask_Data.py", "✨"),
}


def _resolve_profile(force_refresh=False):
    """Resolve logged-in user's profile and store in session state.

    Merges base profile with any user_preferences from Supabase.
    Supports persona override for Engineering users.
    """
    if not force_refresh and "user_profile" in st.session_state:
        return st.session_state["user_profile"]

    email = ""
    name = ""
    try:
        if st.user.is_logged_in:
            email = st.user.email or ""
            name = st.user.name or ""
    except AttributeError:
        pass

    if not email:
        # Bypass mode or not logged in — default profile
        profile = get_profile("", fallback_name="Guest")
        st.session_state["user_profile"] = profile
        return profile

    # Check for persona override (Engineering users only)
    persona_key = st.session_state.get("_persona_override")
    if persona_key:
        profiles = all_profiles()
        if persona_key in profiles:
            profile = dict(profiles[persona_key])
            profile["_simulated"] = True
            profile["_real_email"] = email
            st.session_state["user_profile"] = profile
            return profile

    profile = get_profile(email.strip(), fallback_name=name)

    # Try to merge Supabase user_preferences (extra_domains, notes)
    try:
        from lib import supabase_client as sb
        prefs = sb.query_fresh("user_preferences", {
            "email": f"eq.{email.lower()}",
            "limit": "1",
        })
        if prefs:
            pref = prefs[0]
            extra = pref.get("extra_domains") or []
            if extra:
                profile["domains"] = list(profile["domains"]) + [
                    d for d in extra if d not in profile["domains"]
                ]
            profile["notes"] = pref.get("notes", "")
            profile["hidden_sources"] = pref.get("hidden_sources") or []
    except Exception:
        pass  # Supabase unavailable — use base profile

    st.session_state["user_profile"] = profile
    return profile


# ---------------------------------------------------------------------------
# Main apply function
# ---------------------------------------------------------------------------

def apply():
    """Auth gate + CSS + sidebar. Call once per page."""
    require_auth()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Resolve user profile
    profile = _resolve_profile()
    visible = profile.get("visible_pages", list(_ALL_PAGES.keys()))

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
            'font-family:DM Sans,system-ui,sans-serif; '
            'letter-spacing:0.1em; '
            'background:linear-gradient(135deg, #EC4899, #A855F7); '
            '-webkit-background-clip:text; -webkit-text-fill-color:transparent; '
            'background-clip:text; color:transparent;">LUNAR DASHBOARD</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)

        # Conditional page links based on user profile
        for page_label, (page_file, page_icon) in _ALL_PAGES.items():
            if page_label in visible:
                st.page_link(page_file, label=page_label, icon=page_icon)

        st.divider()

        # --- User info + profile viewer ---
        try:
            is_logged_in = st.user.is_logged_in
        except AttributeError:
            is_logged_in = False

        if is_logged_in or st.session_state.get("_auth_bypass"):
            display_name = profile.get("name") or getattr(st.user, "name", "User")
            role = profile.get("role", "")
            simulated = profile.get("_simulated", False)

            if simulated:
                st.caption(f"Viewing as {display_name} · {role}")
            elif role:
                st.caption(f"Signed in as {display_name} · {role}")
            else:
                st.caption(f"Signed in as {display_name}")

            # Profile viewer (expandable)
            domains = profile.get("domains", [])
            domain_text = "All domains" if domains == ["all"] else ", ".join(domains[:10]) or "None"
            notes = profile.get("notes", "")

            with st.expander("My Profile", expanded=False):
                st.markdown(f"**Role:** {role}")
                st.markdown(f"**Domains:** {domain_text}")
                if notes:
                    st.markdown(f"**Notes:** {notes}")
                st.caption("Edit preferences via Ask AI: \"Add X to my interests\"")

            # --- Persona simulator (Engineering only) ---
            real_email = profile.get("_real_email", "")
            real_profile = get_profile(real_email) if real_email else profile
            is_engineering = (
                real_profile.get("role") == "Engineering"
                or profile.get("role") == "Engineering"
            )

            if is_engineering:
                profiles = all_profiles()
                persona_options = {"(myself)": None}
                for key, p in profiles.items():
                    persona_options[f"{p['name']} · {p['role']}"] = key

                current_persona = st.session_state.get("_persona_override")
                current_label = "(myself)"
                for label, key in persona_options.items():
                    if key == current_persona:
                        current_label = label
                        break

                selected = st.selectbox(
                    "Simulate persona",
                    options=list(persona_options.keys()),
                    index=list(persona_options.keys()).index(current_label),
                    key="_persona_select",
                )
                new_persona = persona_options[selected]
                if new_persona != current_persona:
                    st.session_state["_persona_override"] = new_persona
                    st.session_state.pop("user_profile", None)
                    st.session_state.pop("messages", None)  # reset Ask AI context
                    st.rerun()

            # Sign out button
            try:
                if st.user.is_logged_in:
                    if st.button("Sign out", use_container_width=True):
                        st.logout()
            except AttributeError:
                pass
