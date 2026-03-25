"""For You v2 — clean, readable feed of recent items and domain clusters."""

import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib import linear_client as lc
from lib import style
from lib.charts import COLORS

style.apply()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

profile = st.session_state.get("user_profile", {})
user_domains = profile.get("domains", [])
is_all = user_domains == ["all"]


def _get_openrouter_key():
    """Resolve OpenRouter API key from Streamlit secrets or env."""
    try:
        key = st.secrets.get("OPENROUTER_KEY_STREAMLIT", "")
    except FileNotFoundError:
        key = ""
    if not key:
        key = os.environ.get("OPENROUTER_KEY_STREAMLIT", "")
    return key


def _generate_embedding(text):
    """Generate embedding via OpenRouter text-embedding-3-small (1536 dims)."""
    key = _get_openrouter_key()
    if not key:
        return None
    body = json.dumps({
        "model": "openai/text-embedding-3-small",
        "input": text,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/embeddings",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["data"][0]["embedding"]
    except Exception:
        return None


def _get_domain_embedding():
    """Get or generate the domain embedding for the current user profile.

    Cached in session_state per user (keyed by profile name) so switching
    personas regenerates the embedding.
    """
    if is_all or not user_domains:
        return None

    profile_name = profile.get("name", "unknown")
    cache_key = f"_domain_embedding_{profile_name}"

    if cache_key in st.session_state:
        return st.session_state[cache_key]

    # Build a rich text from domains + profile description for embedding
    domain_text = ", ".join(user_domains)
    description = profile.get("description", "")
    embed_input = f"Investment domains: {domain_text}. {description}"

    embedding = _generate_embedding(embed_input)
    if embedding:
        st.session_state[cache_key] = embedding
    return embedding

# Bright, readable source colors for dark backgrounds
SOURCE_COLORS = {
    "linear": "#818CF8",       # Bright indigo
    "hackernews": "#FB923C",   # Bright orange
    "arxiv": "#FACC15",        # Yellow
    "conference": "#F472B6",   # Pink
    "tigerclaw": "#A78BFA",    # Violet
    "other": "#94A3B8",        # Slate
}

SOURCE_ICONS = {
    "linear": "🔷",
    "hackernews": "🟠",
    "arxiv": "📄",
    "conference": "🎤",
}

TYPE_COLORS = {
    "theme": "#A855F7",
    "deal": "#F59E0B",
}


def _source_badge(source):
    color = SOURCE_COLORS.get(source, SOURCE_COLORS["other"])
    icon = SOURCE_ICONS.get(source, "")
    return (
        f'<span style="display:inline-block; background:{color}18; color:{color}; '
        f'border:1px solid {color}33; border-radius:4px; padding:1px 8px; '
        f'font-size:0.7rem; font-weight:600;">{icon} {source}</span>'
    )


def _type_badge(item_type):
    color = TYPE_COLORS.get(item_type, "#94A3B8")
    return (
        f'<span style="display:inline-block; background:{color}18; color:{color}; '
        f'border:1px solid {color}33; border-radius:4px; padding:1px 8px; '
        f'font-size:0.7rem; font-weight:600; text-transform:uppercase;">{item_type}</span>'
    )


def _linear_badge(identifier):
    if not identifier:
        return ""
    return (
        f'<span style="display:inline-block; background:rgba(99,102,241,0.12); color:#818CF8; '
        f'border:1px solid rgba(99,102,241,0.25); border-radius:4px; padding:1px 8px; '
        f'font-size:0.7rem; font-weight:600;">{identifier}</span>'
    )


def _date_label(ts_str):
    if not ts_str:
        return ""
    return str(ts_str)[:10]


def _patch_item_linear(item_id, identifier, issue_id):
    """Update a Supabase item with its Linear identifier and issue ID."""
    try:
        url_base, _ = sb._get_credentials()
        hdrs = sb._headers()
        hdrs["Prefer"] = "return=minimal"
        body = json.dumps({
            "linear_identifier": identifier,
            "linear_issue_id": issue_id,
        }).encode()
        req = urllib.request.Request(
            f"{url_base}/rest/v1/items?id=eq.{item_id}",
            data=body, headers=hdrs, method="PATCH",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _send_to_linear(item):
    """Create a Linear issue from an item and update Supabase.

    For arxiv themes: also creates deals for associated authors (same source_url)
    and relates them to the theme issue in Linear.
    """
    team = "THE" if item.get("type") == "theme" else "DEAL"
    title = item.get("title", "")
    is_arxiv = item.get("source") == "arxiv"
    if is_arxiv:
        title = f"\U0001f4dc {title}"
    desc = item.get("description") or item.get("summary") or ""
    labels = item.get("source_labels") or []

    result = lc.create_issue(
        team=team,
        title=title,
        description=desc,
        assignee_id=profile.get("linear_id"),
        label_names=labels,
    )
    if "error" in result:
        st.error(f"Failed: {result['error']}")
        return

    theme_identifier = result.get("identifier", "")
    theme_issue_id = result.get("id", "")

    # Update Supabase for the theme
    _patch_item_linear(item["id"], theme_identifier, theme_issue_id)

    st.success(f"Created {theme_identifier} in Linear")

    # For arxiv themes: find related deals (authors) and create + relate them
    if is_arxiv and item.get("type") == "theme" and item.get("source_url"):
        related_deals = sb.query_fresh("items", {
            "select": "id,title,description,summary,source_labels",
            "source": "eq.arxiv",
            "type": "eq.deal",
            "source_url": f"eq.{item['source_url']}",
            "linear_identifier": "is.null",
            "limit": "10",
        }) or []

        if related_deals:
            deal_count = 0
            for deal in related_deals:
                deal_title = f"\U0001f4dc {deal['title']}"
                deal_desc = deal.get("description") or deal.get("summary") or ""
                deal_labels = deal.get("source_labels") or []

                deal_result = lc.create_issue(
                    team="DEAL",
                    title=deal_title,
                    description=deal_desc,
                    assignee_id=profile.get("linear_id"),
                    label_names=deal_labels,
                )
                if "error" in deal_result:
                    continue

                deal_identifier = deal_result.get("identifier", "")
                deal_issue_id = deal_result.get("id", "")

                # Update Supabase for the deal
                _patch_item_linear(deal["id"], deal_identifier, deal_issue_id)

                # Relate theme ↔ deal in Linear
                lc.relate_issues(theme_issue_id, deal_issue_id)

                deal_count += 1

            if deal_count:
                st.success(f"Created {deal_count} related deal{'s' if deal_count != 1 else ''} (authors) and linked to {theme_identifier}")


def _downgrade_headings(text):
    """Downgrade markdown headings so descriptions don't compete with the title.

    # → ###, ## → ####, ### → #####, etc.
    """
    import re
    def _shift(m):
        hashes = m.group(1)
        rest = m.group(2)
        new_level = min(len(hashes) + 2, 6)
        return "#" * new_level + rest
    return re.sub(r'^(#{1,4})([ \t])', _shift, text, flags=re.MULTILINE)


def _linear_issue_url(identifier):
    """Build the Linear issue URL from an identifier like THE-123."""
    if not identifier:
        return ""
    return f"https://linear.app/tigerslug/issue/{identifier}"


def _render_item_row(item, key_suffix):
    """Render a single item as an expander row with description and Send to Linear."""
    title = item.get("title", "Untitled")
    source = item.get("source", "")
    item_type = item.get("type", "")
    date = _date_label(item.get("created_at") or item.get("source_date"))
    linear_id = item.get("linear_identifier")
    source_url = item.get("source_url", "")

    # Expander label: title + source with icon for quick scanning
    source_label = "Hacker News" if source == "hackernews" else source.title() if source else ""
    source_icon = SOURCE_ICONS.get(source, "")
    header = f"{title}  ·  {source_icon} {source_label}" if source_label else title

    # Build the header line with badges
    badges = f"{_source_badge(source)} {_type_badge(item_type)} {_linear_badge(linear_id)}"

    with st.expander(header, expanded=False):
        # Badges row
        badge_row = (
            f'<div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">'
            f'{badges}'
            f'<span style="font-size:0.75rem; opacity:0.45; margin-left:4px;">{date}</span>'
            f'</div>'
        )
        st.markdown(badge_row, unsafe_allow_html=True)

        # Spacer between badges and button
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

        # Action buttons — both rendered as styled HTML for consistency
        _btn_base = (
            'display:inline-flex; align-items:center; gap:6px; '
            'border:none; border-radius:8px; padding:8px 18px; '
            'font-size:0.8rem; font-weight:600; text-decoration:none; '
            'cursor:pointer; white-space:nowrap; color:white; '
            'transition:transform 0.15s ease, box-shadow 0.15s ease;'
        )

        if linear_id:
            linear_url = _linear_issue_url(linear_id)
            st.markdown(
                f'<a href="{linear_url}" target="_blank" style="'
                f'{_btn_base}'
                f'background:linear-gradient(135deg,#6366F1,#818CF8); '
                f'box-shadow:0 2px 6px rgba(99,102,241,0.4),0 1px 2px rgba(0,0,0,0.2);'
                f'" onmouseover="this.style.transform=\'translateY(-1px)\';'
                f"this.style.boxShadow='0 4px 12px rgba(99,102,241,0.6),0 2px 4px rgba(0,0,0,0.3)';\""
                f' onmouseout="this.style.transform=\'none\';'
                f"this.style.boxShadow='0 2px 6px rgba(99,102,241,0.4),0 1px 2px rgba(0,0,0,0.2)';\""
                f'>\U0001f50d Open in Linear</a>',
                unsafe_allow_html=True,
            )
        else:
            # Styled container + CSS override for the Streamlit button
            st.markdown(
                f'<style>'
                f'div[data-testid="stButton"]:has(button[key="send_{key_suffix}"]) button,'
                f'div[data-testid="stButton"] button[kind="primary"] {{'
                f'  background:linear-gradient(135deg,#9333EA,#A855F7) !important;'
                f'  border:none !important;'
                f'  border-radius:8px !important;'
                f'  padding:8px 18px !important;'
                f'  font-size:0.8rem !important;'
                f'  font-weight:600 !important;'
                f'  box-shadow:0 2px 6px rgba(147,51,234,0.4),0 1px 2px rgba(0,0,0,0.2) !important;'
                f'  transition:transform 0.15s ease, box-shadow 0.15s ease !important;'
                f'}}'
                f'div[data-testid="stButton"] button[kind="primary"]:hover {{'
                f'  transform:translateY(-1px) !important;'
                f'  box-shadow:0 4px 12px rgba(147,51,234,0.6),0 2px 4px rgba(0,0,0,0.3) !important;'
                f'}}'
                f'</style>',
                unsafe_allow_html=True,
            )
            if st.button(
                "\U0001f680 Send to Linear",
                key=f"send_{key_suffix}",
                type="primary",
            ):
                _send_to_linear(item)
                st.rerun()

        # Title as heading inside the expanded view
        st.markdown(f"## {title}")

        # Description (with downgraded headings)
        desc = item.get("description") or item.get("summary") or ""
        if desc:
            st.markdown(_downgrade_headings(desc))
        else:
            st.caption("No description available.")

        # Source link
        if source_url:
            st.markdown(f"[Open source ↗]({source_url})")


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("For You")

if not user_domains:
    st.info("Add domains in [My Profile](/My_Profile) or via Ask AI: *'Add robotics to my interests'*")
    st.stop()

if is_all:
    st.caption("Showing all domains (Engineering view)")
else:
    pills = " ".join(
        f'`{d}`' for d in user_domains
    )
    st.caption(f"Your domains: {pills} · [Edit](/My_Profile)")

# Sidebar
with st.sidebar:
    st.caption("Data refreshes every 5 minutes")
    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        # Clear cached embedding so it regenerates on next load
        for k in list(st.session_state.keys()):
            if k.startswith("_domain_embedding"):
                del st.session_state[k]
        st.session_state.pop("user_profile", None)
        st.rerun()

# ---------------------------------------------------------------------------
# Data loading — semantic matching via embeddings
# ---------------------------------------------------------------------------

domain_embedding = _get_domain_embedding()
_use_semantic = domain_embedding is not None and not is_all

with st.spinner("Loading your feed..."):
    iso_7d = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")

    if _use_semantic:
        # Semantic matching via Supabase vector RPCs
        try:
            # 1. Find semantically matching clusters
            matched_clusters = sb.rpc_fresh("search_clusters_by_embedding", {
                "query_emb": domain_embedding,
                "lim": 300,
            }) or []

            # Filter by similarity threshold and non-empty
            matched_clusters = [
                c for c in matched_clusters
                if float(c.get("similarity", 0)) >= 0.40
                and c.get("item_count", 0) > 0
            ]

            # Sort by hotness (already semantically filtered)
            matched_clusters.sort(
                key=lambda c: float(c.get("hotness_score") or 0), reverse=True
            )

            # 2. Get recent items that belong to matched clusters
            matched_cluster_ids = {c["id"] for c in matched_clusters}

            recent_items = sb.query_fresh("items", {
                "select": "id,title,source,type,source_date,created_at,source_url,source_labels,sector_labels,linear_identifier,description,summary,cluster_id",
                "created_at": f"gte.{iso_7d}",
                "order": "created_at.desc",
                "limit": "1000",
            }) or []

            # Items match if:
            # 1. They belong to a semantically matched cluster, OR
            # 2. They're unclustered but match user domains by keyword
            #    (77% of recent items are unclustered, so this catches them)
            domain_lower = [d.lower() for d in user_domains]

            domain_items = []
            for i in recent_items:
                if i.get("source") == "arxiv" and i.get("type") == "deal":
                    continue
                cid = i.get("cluster_id")
                if cid and cid in matched_cluster_ids:
                    domain_items.append(i)
                elif not cid:
                    # Unclustered: keyword match on title + summary
                    text = ((i.get("title") or "") + " " + (i.get("summary") or "")).lower()
                    if any(d in text for d in domain_lower):
                        domain_items.append(i)

        except Exception as e:
            # Fallback to non-semantic if RPCs fail
            st.warning(f"Semantic matching unavailable, using keyword fallback. ({e})")
            _use_semantic = False

    if not _use_semantic:
        # Fallback: keyword matching (for "all" domains or if semantic fails)
        recent_items = sb.query_fresh("items", {
            "select": "id,title,source,type,source_date,created_at,source_url,source_labels,sector_labels,linear_identifier,description,summary,cluster_id",
            "created_at": f"gte.{iso_7d}",
            "order": "created_at.desc",
            "limit": "1000",
        }) or []

        all_clusters = sb.query_fresh("clusters", {
            "select": "id,label,summary,item_count,source_diversity,hotness_score,first_seen_at,last_surfaced_at",
            "order": "hotness_score.desc.nullslast",
            "limit": "500",
        }) or []
        all_clusters = [c for c in all_clusters if c.get("item_count", 0) > 0]

        if is_all:
            matched_clusters = all_clusters
            domain_items = [
                i for i in recent_items
                if not (i.get("source") == "arxiv" and i.get("type") == "deal")
            ]
        else:
            domain_lower = [d.lower() for d in user_domains]

            def _cluster_matches(c):
                text = ((c.get("label") or "") + " " + (c.get("summary") or "")).lower()
                return any(d in text for d in domain_lower)

            matched_clusters = [c for c in all_clusters if _cluster_matches(c)]
            matched_cluster_ids = {c["id"] for c in matched_clusters}
            domain_items = [
                i for i in recent_items
                if not (i.get("source") == "arxiv" and i.get("type") == "deal")
                and (
                    i.get("cluster_id") in matched_cluster_ids
                    or any(d in (i.get("title") or "").lower() for d in domain_lower)
                )
            ]

if _use_semantic:
    st.caption(f"Matched semantically via embeddings ({len(matched_clusters)} clusters, similarity >= 0.40)")

# ---------------------------------------------------------------------------
# Main content — two tabs: Recent Items / Your Clusters
# ---------------------------------------------------------------------------

st.markdown("---")

# Custom CSS for tab accent color
st.markdown(
    '<style>'
    '[data-testid="stTabs"] [data-baseweb="tab-list"] {'
    '  gap: 0; border-bottom: 2px solid rgba(168,85,247,0.15);'
    '}'
    '[data-testid="stTabs"] [data-baseweb="tab"] {'
    '  padding: 12px 24px; font-weight: 600;'
    '  border-bottom: 3px solid transparent; transition: all 0.15s ease;'
    '}'
    '[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {'
    '  border-bottom: 3px solid #A855F7 !important;'
    '  color: #A855F7 !important;'
    '}'
    '[data-testid="stTabs"] [data-baseweb="tab"]:hover {'
    '  color: #C084FC;'
    '}'
    '[data-testid="stTabs"]:not([data-testid="stTabs"] [data-testid="stTabs"]) > [data-baseweb="tab-list"] > [data-baseweb="tab"] p {'
    '  font-size: 1.5rem !important; font-weight: 700 !important;'
    '}'
    '</style>',
    unsafe_allow_html=True,
)

tab_recent, tab_clusters = st.tabs([
    f"📋 Recent Items ({len(domain_items)})",
    f"🔬 Your Clusters ({len(matched_clusters)})",
])

# --- Tab 1: Recent Items ---
with tab_recent:
    if not domain_items:
        st.info("No recent items match your domains.")
    else:
        st.caption(f"{len(domain_items)} items in the last 7 days")

        # Source filter tabs
        sources_present = sorted(set(i.get("source", "") for i in domain_items))
        tab_labels = ["All"] + [s.title() if s != "hackernews" else "Hacker News" for s in sources_present]
        source_tabs = st.tabs(tab_labels)

        for tab_idx, tab in enumerate(source_tabs):
            with tab:
                if tab_idx == 0:
                    filtered = domain_items
                else:
                    src_key = sources_present[tab_idx - 1]
                    filtered = [i for i in domain_items if i.get("source") == src_key]

                if not filtered:
                    st.caption("No items from this source.")
                    continue

                for idx, item in enumerate(filtered[:50]):
                    _render_item_row(item, key_suffix=f"recent_{tab_idx}_{idx}")

                if len(filtered) > 50:
                    st.caption(f"Showing 50 of {len(filtered)} items")

# --- Tab 2: Your Clusters ---
with tab_clusters:
    if not matched_clusters:
        st.info("No clusters match your domains yet.")
    else:
        st.caption(f"{len(matched_clusters)} clusters ranked by hotness")

        for c_idx, cluster in enumerate(matched_clusters[:20]):
            score = float(cluster.get("hotness_score") or 0)
            label = cluster.get("label") or "Unlabeled"
            item_count = cluster.get("item_count", 0)
            diversity = cluster.get("source_diversity", 0)
            summary = cluster.get("summary") or ""

            # Score color
            if score >= 0.6:
                score_color = "#EF4444"
                heat = "🔴"
            elif score >= 0.4:
                score_color = "#F59E0B"
                heat = "🟠"
            elif score >= 0.3:
                score_color = "#EAB308"
                heat = "🟡"
            else:
                score_color = "#94A3B8"
                heat = "⚪"

            # Cluster header card
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:12px; padding:14px 18px; '
                f'margin-top:12px; border-radius:10px; '
                f'background:linear-gradient(145deg,#2A3154,#252B45); '
                f'border:1px solid rgba(168,85,247,0.12);">'
                f'<span style="font-size:1.3rem;">{heat}</span>'
                f'<div style="flex:1; min-width:0;">'
                f'<div style="font-weight:700; font-size:1rem; margin-bottom:2px;">{label}</div>'
                f'<div style="font-size:0.78rem; opacity:0.55;">'
                f'{item_count} items · {diversity} source{"s" if diversity != 1 else ""} · '
                f'score <span style="color:{score_color}; font-weight:700;">{score:.2f}</span>'
                f'</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if summary:
                st.caption(summary[:200])

            # Expand to see items
            with st.expander(f"Browse {item_count} items", expanded=False):
                cluster_items = sb.query_fresh("items", {
                    "select": "id,title,source,type,source_date,source_url,source_labels,sector_labels,linear_identifier,description,summary",
                    "cluster_id": f"eq.{cluster['id']}",
                    "order": "created_at.desc",
                    "limit": "100",
                }) or []

                # Exclude arxiv deals (only themes from arxiv)
                cluster_items = [
                    i for i in cluster_items
                    if not (i.get("source") == "arxiv" and i.get("type") == "deal")
                ]

                if not cluster_items:
                    st.caption("No items found.")
                else:
                    for i_idx, item in enumerate(cluster_items):
                        _render_item_row(item, key_suffix=f"cl_{c_idx}_{i_idx}")
