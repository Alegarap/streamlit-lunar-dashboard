"""Supabase client for the Streamlit dashboard.

Reuses the same REST API patterns from sourcing_dashboard.py.
Credentials come from environment variables (resolved via 1Password/claude-ops).
"""

import json
import os
import urllib.parse
import urllib.request
from functools import lru_cache

import streamlit as st


def _get_credentials():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        st.error(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY. "
            "Relaunch via `claude-ops` so 1Password resolves all secrets."
        )
        st.stop()
    return url, key


def _headers():
    _, key = _get_credentials()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


@st.cache_data(ttl=300)
def rpc(fn_name: str, params: dict | None = None) -> list | dict | None:
    """Call a Supabase RPC function."""
    url, _ = _get_credentials()
    endpoint = f"{url}/rest/v1/rpc/{fn_name}"
    data = json.dumps(params or {}).encode()
    req = urllib.request.Request(endpoint, data=data, headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read()
        return json.loads(body) if body else None


@st.cache_data(ttl=300)
def query(table: str, params: dict | None = None) -> list:
    """Query a Supabase table via REST API."""
    url, _ = _get_credentials()
    endpoint = f"{url}/rest/v1/{table}"
    if params:
        endpoint += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(endpoint, headers=_headers())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def insert(table: str, rows: list[dict]) -> list:
    """Insert rows into a Supabase table."""
    url, _ = _get_credentials()
    endpoint = f"{url}/rest/v1/{table}"
    hdrs = _headers()
    hdrs["Prefer"] = "return=minimal"
    data = json.dumps(rows).encode()
    req = urllib.request.Request(endpoint, data=data, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
        return json.loads(body) if body else []
