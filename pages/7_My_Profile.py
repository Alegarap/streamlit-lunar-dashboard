"""My Profile — view and manage your profile, domains, and interests."""

import json
import os
import sys
import urllib.request
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib import style
from lib.user_profiles import get_profile

style.apply()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

profile = st.session_state.get("user_profile", {})
user_domains = profile.get("domains", [])
is_simulated = profile.get("_simulated", False)


def _get_target_email():
    """Get the email to read/write preferences for.

    For persona simulation: use the simulated persona's email (so Engineering
    users can manage interests on behalf of team members).
    Otherwise: use the logged-in user's email.
    """
    persona_key = profile.get("_persona_key")
    if persona_key:
        return f"{persona_key}@lunarventures.eu"
    try:
        if st.user.is_logged_in:
            return st.user.email.lower()
    except AttributeError:
        pass
    return None


def _upsert_preferences(email, extra_domains, notes=""):
    """Upsert user preferences into Supabase."""
    url_base, _ = sb._get_credentials()
    endpoint = f"{url_base}/rest/v1/user_preferences"
    hdrs = sb._headers()
    hdrs["Prefer"] = "resolution=merge-duplicates,return=minimal"
    body = json.dumps({
        "email": email,
        "extra_domains": extra_domains,
        "notes": notes,
    }).encode()
    req = urllib.request.Request(endpoint, data=body, headers=hdrs, method="POST")
    urllib.request.urlopen(req, timeout=10)


def _get_openrouter_key():
    """Resolve OpenRouter API key, with fallback."""
    for key_name in ("OPENROUTER_KEY_STREAMLIT", "OPENROUTER_KEY_FALLBACK"):
        key = ""
        try:
            key = st.secrets.get(key_name, "")
        except FileNotFoundError:
            pass
        if not key:
            key = os.environ.get(key_name, "")
        if key:
            return key
    return ""


def _expand_domain_with_ai(domain):
    """Use AI to suggest adjacent domains related to a given interest."""
    key = _get_openrouter_key()
    if not key:
        return [domain]

    prompt = (
        f"I'm adding '{domain}' as a topic of interest for sourcing deep-tech startups. "
        f"What are 4-6 specific sub-topics, adjacent fields, or related technology areas "
        f"that fall under or closely relate to '{domain}'? "
        f"Focus narrowly on what '{domain}' actually means — don't drift into unrelated areas. "
        f"Return ONLY a JSON array of short lowercase strings. No explanation, no markdown. "
        f"Example for 'robotics': [\"autonomous navigation\", \"manipulation\", \"swarm intelligence\", \"sensor fusion\", \"embodied AI\"]"
    )

    body = json.dumps({
        "model": "google/gemini-2.0-flash-001",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        content = data["choices"][0]["message"]["content"].strip()
        # Parse JSON array from response (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        suggestions = json.loads(content)
        if isinstance(suggestions, list):
            return [s.strip().lower() for s in suggestions if isinstance(s, str)]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("My Profile")

target_email = _get_target_email()

if not target_email:
    st.info("Sign in to view your profile.")
    st.stop()

if is_simulated:
    st.caption(f"Editing profile for **{profile.get('name')}** ({target_email})")
else:
    st.caption(target_email)

# Sidebar
with st.sidebar:
    if st.button("Refresh profile", use_container_width=True):
        st.session_state.pop("user_profile", None)
        for k in list(st.session_state.keys()):
            if k.startswith("_domain_embedding"):
                del st.session_state[k]
        st.rerun()

# ---------------------------------------------------------------------------
# Profile info
# ---------------------------------------------------------------------------

st.markdown("---")

col_info, col_role = st.columns([2, 1])
with col_info:
    st.markdown(f"### {profile.get('name', 'Unknown')}")
    desc = profile.get("description", "")
    if desc:
        st.caption(desc)
with col_role:
    role = profile.get("role", "")
    role_color = "#A855F7" if role == "Engineering" else "#F59E0B"
    st.markdown(
        f'<div style="display:inline-block; background:{role_color}18; color:{role_color}; '
        f'border:1px solid {role_color}33; border-radius:6px; padding:6px 16px; '
        f'font-size:0.85rem; font-weight:600; margin-top:8px;">{role}</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("My Domains")

# Load current preferences from Supabase
current_prefs = sb.query_fresh("user_preferences", {
    "email": f"eq.{target_email}",
    "limit": "1",
}) or []
extra_domains = current_prefs[0].get("extra_domains", []) if current_prefs else []
current_notes = current_prefs[0].get("notes", "") if current_prefs else ""

# Base domains from profile
base_profile = get_profile(target_email)
base_domains = base_profile.get("domains", [])
is_all_base = base_domains == ["all"]

# Show base domains
if is_all_base:
    st.caption("Base domains: **All** (Engineering — sees everything)")
elif base_domains:
    st.markdown("**Base domains** (from role profile)")
    pills_html = " ".join(
        f'<span style="display:inline-block; background:rgba(168,85,247,0.12); '
        f'border:1px solid rgba(168,85,247,0.25); border-radius:20px; '
        f'padding:4px 14px; font-size:0.8rem; margin:3px 2px;">{d}</span>'
        for d in base_domains
    )
    st.markdown(pills_html, unsafe_allow_html=True)
    st.caption("These come from your role profile and can't be changed here.")

# Show extra domains with remove buttons
st.markdown("")
col_title, col_clear = st.columns([3, 1])
with col_title:
    st.markdown("**Added interests**")
with col_clear:
    if extra_domains:
        st.markdown(
            '<style>div[data-testid="stButton"]:has(button[key="rm_all"]) button {'
            'background:linear-gradient(135deg,#DC2626,#EF4444) !important;'
            'border:none !important;'
            'box-shadow:0 2px 6px rgba(220,38,38,0.4) !important;'
            '} div[data-testid="stButton"]:has(button[key="rm_all"]) button:hover {'
            'box-shadow:0 4px 12px rgba(220,38,38,0.6) !important;'
            'transform:translateY(-1px) !important;'
            '}</style>',
            unsafe_allow_html=True,
        )
        if st.button("Remove all", key="rm_all", type="primary"):
            _upsert_preferences(target_email, [], current_notes)
            st.session_state.pop("user_profile", None)
            for k in list(st.session_state.keys()):
                if k.startswith("_domain_embedding"):
                    del st.session_state[k]
            st.rerun()

if extra_domains:
    cols_per_row = 3
    for row_start in range(0, len(extra_domains), cols_per_row):
        row = extra_domains[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col_idx, domain in enumerate(row):
            with cols[col_idx]:
                st.markdown(
                    f'<div style="display:flex; align-items:center; justify-content:space-between; '
                    f'background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.25); '
                    f'border-radius:8px; padding:8px 12px; margin-bottom:4px;">'
                    f'<span style="font-size:0.85rem;">{domain}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Remove", key=f"rm_{domain}", use_container_width=True):
                    new_extra = [d for d in extra_domains if d != domain]
                    _upsert_preferences(target_email, new_extra, current_notes)
                    st.session_state.pop("user_profile", None)
                    for k in list(st.session_state.keys()):
                        if k.startswith("_domain_embedding"):
                            del st.session_state[k]
                    st.rerun()
else:
    st.caption("No extra interests added yet.")

# ---------------------------------------------------------------------------
# Add new interest
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Add Interest")

use_ai = st.toggle(
    "Let AI suggest related domains",
    value=True,
    help="When enabled, AI will suggest 3-6 adjacent fields related to your input. "
         "You can review and select which ones to add.",
)

new_domain = st.text_input(
    "New interest",
    placeholder="e.g. quantum computing, bio, defense",
    key="add_domain_input",
    label_visibility="collapsed",
)

if st.button("Add", type="primary", key="add_domain_btn"):
    if new_domain and new_domain.strip():
        clean = new_domain.strip().lower()
        all_current = (base_domains if not is_all_base else []) + extra_domains

        if use_ai:
            with st.spinner(f"Finding domains related to '{clean}'..."):
                suggestions = _expand_domain_with_ai(clean)

            # Always include the original term
            if clean not in suggestions:
                suggestions = [clean] + suggestions

            # Filter out already-present domains
            new_suggestions = [s for s in suggestions if s not in all_current]

            if new_suggestions:
                st.session_state["_pending_suggestions"] = new_suggestions
            else:
                st.info(f"All suggested domains are already in your interests.")
        else:
            if clean not in all_current:
                new_extra = extra_domains + [clean]
                _upsert_preferences(target_email, new_extra, current_notes)
                st.session_state.pop("user_profile", None)
                for k in list(st.session_state.keys()):
                    if k.startswith("_domain_embedding"):
                        del st.session_state[k]
                st.success(f"Added '{clean}' to your interests.")
                st.rerun()
            else:
                st.warning(f"'{clean}' is already in your domains.")

# Show pending AI suggestions for review
if "_pending_suggestions" in st.session_state:
    suggestions = st.session_state["_pending_suggestions"]
    st.markdown("**AI suggestions** — select which to add:")

    selected = []
    cols_per_row = 3
    for row_start in range(0, len(suggestions), cols_per_row):
        row = suggestions[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col_idx, s in enumerate(row):
            with cols[col_idx]:
                if st.checkbox(s, value=True, key=f"sug_{s}"):
                    selected.append(s)

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Add selected", type="primary", key="confirm_suggestions"):
            if selected:
                new_extra = extra_domains + [s for s in selected if s not in extra_domains]
                _upsert_preferences(target_email, new_extra, current_notes)
                st.session_state.pop("user_profile", None)
                st.session_state.pop("_pending_suggestions", None)
                for k in list(st.session_state.keys()):
                    if k.startswith("_domain_embedding"):
                        del st.session_state[k]
                st.success(f"Added {len(selected)} domain{'s' if len(selected) != 1 else ''}.")
                st.rerun()
    with col_cancel:
        if st.button("Cancel", key="cancel_suggestions"):
            st.session_state.pop("_pending_suggestions", None)
            st.rerun()

# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Notes")
st.caption("Free-form notes about your preferences (visible to AI when answering questions).")

updated_notes = st.text_area(
    "Notes",
    value=current_notes,
    key="profile_notes",
    label_visibility="collapsed",
    height=100,
)
if updated_notes != current_notes:
    if st.button("Save notes", key="save_notes"):
        _upsert_preferences(target_email, extra_domains, updated_notes)
        st.session_state.pop("user_profile", None)
        st.success("Notes saved.")
        st.rerun()
