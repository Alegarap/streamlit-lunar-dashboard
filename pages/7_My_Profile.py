"""My Profile — view and manage your profile, domains, and interests."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib import style

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


def _upsert_profile_domains(email, domains, name=None, role=None):
    """Write the canonical domain list to user_profiles (the single source of truth
    shared with the ambient-sourcing plugin). name/role are sent so a brand-new
    teammate row can be created; for an existing row only domains change in practice."""
    url_base, _ = sb._get_credentials()
    endpoint = f"{url_base}/rest/v1/user_profiles?on_conflict=email"
    hdrs = sb._headers()
    hdrs["Prefer"] = "resolution=merge-duplicates,return=minimal"
    row = {"email": email, "domains": domains}
    if name:
        row["name"] = name
    if role:
        row["role"] = role
    body = json.dumps(row).encode()
    req = urllib.request.Request(endpoint, data=body, headers=hdrs, method="POST")
    urllib.request.urlopen(req, timeout=10)


def _upsert_notes(email, notes):
    """Persist free-form notes to user_preferences (domains live in user_profiles)."""
    url_base, _ = sb._get_credentials()
    endpoint = f"{url_base}/rest/v1/user_preferences"
    hdrs = sb._headers()
    hdrs["Prefer"] = "resolution=merge-duplicates,return=minimal"
    body = json.dumps({"email": email, "notes": notes}).encode()
    req = urllib.request.Request(endpoint, data=body, headers=hdrs, method="POST")
    urllib.request.urlopen(req, timeout=10)


def _clear_profile_cache():
    """Drop cached profile + domain embeddings so edits take effect immediately."""
    st.session_state.pop("user_profile", None)
    st.cache_data.clear()
    for k in list(st.session_state.keys()):
        if k.startswith("_domain_embedding"):
            del st.session_state[k]


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
    keys = []
    for key_name in ("OPENROUTER_KEY_STREAMLIT", "OPENROUTER_KEY_FALLBACK"):
        key = ""
        try:
            key = st.secrets.get(key_name, "")
        except FileNotFoundError:
            pass
        if not key:
            key = os.environ.get(key_name, "")
        if key:
            keys.append(key)

    if not keys:
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

    for api_key in keys:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"].strip()
            # Parse JSON array from response (handle markdown code blocks)
            if "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    inner = parts[1]
                    if inner.startswith("json"):
                        inner = inner[4:]
                    content = inner.strip()
            suggestions = json.loads(content)
            if isinstance(suggestions, list):
                return [s.strip().lower() for s in suggestions if isinstance(s, str)]
        except urllib.error.HTTPError as e:
            if e.code in (402, 429) and api_key != keys[-1]:
                continue
            return [domain]
        except Exception:
            return [domain]
    return [domain]


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

# Notes still live in user_preferences; domains are now canonical in user_profiles.
current_prefs = sb.query_fresh("user_preferences", {
    "email": f"eq.{target_email}",
    "limit": "1",
}) or []
current_notes = current_prefs[0].get("notes", "") if current_prefs else ""

# Canonical domains come straight from the resolved profile (user_profiles table).
domains = list(profile.get("domains") or [])
is_all = domains == ["all"]
profile_name = profile.get("name")
profile_role = profile.get("role")

if is_all:
    st.caption("Domains: **All** (Engineering — sees everything, never filtered).")
else:
    st.caption(
        "These domains drive your Discovery feed and the ambient-sourcing plugin. "
        "Edits here update the shared database and take effect everywhere."
    )

    col_title, col_clear = st.columns([3, 1])
    with col_title:
        st.markdown(f"**{len(domains)} domain{'s' if len(domains) != 1 else ''}**")
    with col_clear:
        if domains:
            if st.button("Remove all", key="rm_all", type="secondary"):
                _upsert_profile_domains(target_email, [], profile_name, profile_role)
                _clear_profile_cache()
                st.rerun()

    if domains:
        cols_per_row = 3
        for row_start in range(0, len(domains), cols_per_row):
            row = domains[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col_idx, domain in enumerate(row):
                with cols[col_idx]:
                    st.markdown(
                        f'<div style="display:flex; align-items:center; justify-content:space-between; '
                        f'background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.25); '
                        f'border-radius:8px; padding:8px 12px; margin-bottom:4px;">'
                        f'<span style="font-size:0.85rem;">{domain}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("Remove", key=f"rm_{domain}", use_container_width=True):
                        new_domains = [d for d in domains if d != domain]
                        _upsert_profile_domains(target_email, new_domains, profile_name, profile_role)
                        _clear_profile_cache()
                        st.rerun()
    else:
        st.caption("No domains yet — add some below.")

# ---------------------------------------------------------------------------
# Add a domain
# ---------------------------------------------------------------------------

if not is_all:
    st.markdown("---")
    st.subheader("Add Domain")

    use_ai = st.toggle(
        "Let AI suggest related domains",
        value=True,
        help="When enabled, AI will suggest 3-6 adjacent fields related to your input. "
             "You can review and select which ones to add.",
    )

    new_domain = st.text_input(
        "New domain",
        placeholder="e.g. quantum computing, bio, defense",
        key="add_domain_input",
        label_visibility="collapsed",
    )

    if st.button("Add", type="primary", key="add_domain_btn"):
        if new_domain and new_domain.strip():
            clean = new_domain.strip().lower()
            if use_ai:
                with st.spinner(f"Finding domains related to '{clean}'..."):
                    suggestions = _expand_domain_with_ai(clean)
                if clean not in suggestions:
                    suggestions = [clean] + suggestions
                new_suggestions = [s for s in suggestions if s not in domains]
                if new_suggestions:
                    st.session_state["_pending_suggestions"] = new_suggestions
                else:
                    st.info("All suggested domains are already in your list.")
            else:
                if clean not in domains:
                    _upsert_profile_domains(target_email, domains + [clean], profile_name, profile_role)
                    _clear_profile_cache()
                    st.success(f"Added '{clean}'.")
                    st.rerun()
                else:
                    st.warning(f"'{clean}' is already in your domains.")

    # Pending AI suggestions for review
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
                    new_domains = domains + [s for s in selected if s not in domains]
                    _upsert_profile_domains(target_email, new_domains, profile_name, profile_role)
                    _clear_profile_cache()
                    st.session_state.pop("_pending_suggestions", None)
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
        _upsert_notes(target_email, updated_notes)
        _clear_profile_cache()
        st.success("Notes saved.")
        st.rerun()
