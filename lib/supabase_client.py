"""Supabase client for the Streamlit dashboard.

Reuses the same REST API patterns from sourcing_dashboard.py.
Credentials come from Streamlit secrets (st.secrets) with os.environ fallback.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import streamlit as st


def _get_credentials():
    """Resolve Supabase credentials from st.secrets (Streamlit Cloud) or os.environ (local)."""
    url = ""
    key = ""
    # Streamlit Cloud stores secrets in st.secrets; local dev uses os.environ
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    except FileNotFoundError:
        pass  # No secrets.toml — fall through to os.environ
    if not url:
        url = os.environ.get("SUPABASE_URL", "")
    if not key:
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        st.error(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY. "
            "Add them to Streamlit Cloud secrets or relaunch locally via `claude-ops`."
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
def rpc(fn_name: str, _params_json: str = "{}") -> list | dict | None:
    """Call a Supabase RPC function.

    Note: params are passed as a JSON string for Streamlit cache hashability.
    Use rpc_call() for the dict-based interface.
    """
    url, _ = _get_credentials()
    endpoint = f"{url}/rest/v1/rpc/{fn_name}"
    data = _params_json.encode()
    req = urllib.request.Request(endpoint, data=data, headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read()
        return json.loads(body) if body else None


def rpc_call(fn_name: str, params: dict | None = None) -> list | dict | None:
    """Convenience wrapper: accepts a dict, serialises for caching."""
    return rpc(fn_name, json.dumps(params or {}, sort_keys=True))


@st.cache_data(ttl=300)
def query(table: str, _params_json: str = "{}") -> list:
    """Query a Supabase table via REST API.

    Note: params are passed as a JSON string for Streamlit cache hashability.
    Use query_table() for the dict-based interface.
    """
    url, _ = _get_credentials()
    params = json.loads(_params_json)
    endpoint = f"{url}/rest/v1/{table}"
    if params:
        endpoint += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(endpoint, headers=_headers())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def query_table(table: str, params: dict | None = None) -> list:
    """Convenience wrapper: accepts a dict, serialises for caching."""
    return query(table, json.dumps(params or {}, sort_keys=True))


def count_rows(table: str, filters: dict | None = None) -> int:
    """Get exact row count using Prefer: count=exact header."""
    url, _ = _get_credentials()
    endpoint = f"{url}/rest/v1/{table}?select=id"
    if filters:
        endpoint += "&" + urllib.parse.urlencode(filters)
    hdrs = _headers()
    hdrs["Prefer"] = "count=exact"
    hdrs["Range"] = "0-0"  # Fetch minimal data
    req = urllib.request.Request(endpoint, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_range = resp.headers.get("Content-Range", "")
            # Format: "0-0/1234" or "*/1234"
            if "/" in content_range:
                return int(content_range.split("/")[1])
            return 0
    except urllib.error.HTTPError:
        return 0


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
