"""For You — personalized view of clusters and items matching user domains."""

import sys
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib import style
from lib.charts import COLORS, style_fig

style.apply()

# --- Sidebar ---
with st.sidebar:
    st.caption("Data refreshes every 5 minutes")
    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# 1. Header — Title + Domain Pills
# ---------------------------------------------------------------------------

st.title("For You")

profile = st.session_state.get("user_profile", {})
user_domains = profile.get("domains", [])

if not user_domains:
    st.info("Add domains to your profile via Ask AI: 'Add robotics to my interests'")
    st.stop()

is_all = user_domains == ["all"]

if is_all:
    st.caption("Showing all domains (Engineering view)")
else:
    pills_html = "".join(
        f'<span style="display:inline-block; background:rgba(168,85,247,0.15); '
        f'border:1px solid rgba(168,85,247,0.25); border-radius:20px; '
        f'padding:4px 12px; font-size:0.75rem; margin:2px 4px;">{d}</span>'
        for d in user_domains
    )
    st.markdown(pills_html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 2. Data Fetching
# ---------------------------------------------------------------------------

all_clusters = sb.query_fresh("clusters", {
    "select": "id,label,summary,item_count,source_diversity,hotness_score,first_seen_at,last_surfaced_at",
    "order": "hotness_score.desc.nullslast",
    "limit": "500",
})

domain_lower = [d.lower() for d in user_domains] if not is_all else []


def cluster_matches(c):
    if is_all:
        return True
    text = ((c.get("label") or "") + " " + (c.get("summary") or "")).lower()
    return any(d in text for d in domain_lower)


matched = [c for c in (all_clusters or []) if cluster_matches(c)]
matched_ids = {c["id"] for c in matched}
unmatched = [c for c in (all_clusters or []) if not cluster_matches(c)]

iso_14d = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")
iso_48h = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")
iso_7d = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")

recent_items = sb.query_fresh("items", {
    "select": "title,source,type,created_at,source_url,cluster_id,linear_identifier",
    "created_at": f"gte.{iso_14d}",
    "order": "created_at.desc",
    "limit": "500",
})

# ---------------------------------------------------------------------------
# 3. KPI Row
# ---------------------------------------------------------------------------


def colored_metric(label, value, color):
    st.markdown(
        f'<div style="border:1px solid rgba(168,85,247,0.15); border-radius:12px; '
        f'padding:16px 20px; margin-bottom:16px; background:linear-gradient(145deg,#2A3154,#252B45); '
        f'box-shadow:0 2px 8px rgba(0,0,0,0.3),0 1px 2px rgba(0,0,0,0.2),'
        f'inset 0 1px 0 rgba(255,255,255,0.04);">'
        f'<p style="font-size:0.8rem; font-weight:500; text-transform:uppercase; '
        f'letter-spacing:0.06em; opacity:0.7; margin:0 0 4px 0;">{label}</p>'
        f'<p style="font-size:1.8rem; font-weight:700; margin:0; color:{color};">{value}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


hot_count = sum(1 for c in matched if float(c.get("hotness_score") or 0) > 0.4)

new_48h_count = sum(
    1 for item in (recent_items or [])
    if item.get("cluster_id") in matched_ids and item.get("created_at", "") >= iso_48h
)

# Trending: clusters with 3+ items in last 7 days
recent_per_cluster = defaultdict(int)
for item in (recent_items or []):
    cid = item.get("cluster_id")
    if cid in matched_ids and item.get("created_at", "") >= iso_7d:
        recent_per_cluster[cid] += 1
trending_count = sum(1 for v in recent_per_cluster.values() if v >= 3)

k1, k2, k3, k4 = st.columns(4)
with k1:
    colored_metric("Matching Clusters", len(matched), "#A855F7")
with k2:
    colored_metric("Hot Signals", hot_count, "#EF4444")
with k3:
    colored_metric("New Items (48h)", new_48h_count, "#F4A7C8")
with k4:
    colored_metric("Trending", trending_count, "#F59E0B")

# ---------------------------------------------------------------------------
# 4. Hot in Your Domains
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Hot in Your Domains")


def parse_ts(ts):
    if not ts:
        return None
    try:
        clean = re.sub(r'[+-]\d{2}:\d{2}$|Z$', '', ts)
        return datetime.fromisoformat(clean)
    except Exception:
        return None


if not matched:
    st.caption("No clusters match your domains yet.")
else:
    for rank, cluster in enumerate(matched[:10], 1):
        score = float(cluster.get("hotness_score") or 0)
        label = cluster.get("label") or "Unlabeled"
        items_count = cluster.get("item_count", 0)
        diversity = cluster.get("source_diversity", 0)

        # Age
        first_dt = parse_ts(cluster.get("first_seen_at", ""))
        age_days = (datetime.now() - first_dt).days if first_dt else 0
        if age_days <= 1:
            age_str = "new today"
        elif age_days < 7:
            age_str = f"{age_days}d old"
        elif age_days < 30:
            age_str = f"{age_days // 7}w old"
        else:
            age_str = f"{age_days // 30}mo old"

        # Momentum
        last_dt = parse_ts(cluster.get("last_surfaced_at", ""))
        days_since = (datetime.now() - last_dt).days if last_dt else 999
        if days_since == 0:
            momentum = "active today"
        elif days_since <= 2:
            momentum = "active this week"
        elif days_since <= 7:
            momentum = "last week"
        else:
            momentum = "cooling off"

        # Score color
        score_color = "#EF4444" if score >= 0.6 else "#F59E0B" if score >= 0.4 else "#94A3B8"
        bar_width = int(score * 100)

        # Render row
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:16px; padding:12px 16px; '
            f'margin-bottom:8px; border-radius:10px; '
            f'background:linear-gradient(145deg,#2A3154,#252B45); '
            f'border:1px solid rgba(168,85,247,0.1);">'
            f'<span style="font-size:1.4rem; font-weight:800; opacity:0.3; min-width:28px;">#{rank}</span>'
            f'<div style="flex:1; min-width:0;">'
            f'<div style="display:flex; align-items:baseline; gap:10px; margin-bottom:4px;">'
            f'<span style="font-weight:700; font-size:1rem;">{label}</span>'
            f'<span style="font-size:0.75rem; color:{score_color}; font-weight:700;">{score:.2f}</span>'
            f'</div>'
            f'<div style="background:rgba(255,255,255,0.06); border-radius:4px; height:6px; width:100%; margin-bottom:6px;">'
            f'<div style="background:{score_color}; border-radius:4px; height:6px; width:{bar_width}%;"></div>'
            f'</div>'
            f'<div style="display:flex; gap:16px; font-size:0.75rem; opacity:0.6;">'
            f'<span>{items_count} items</span>'
            f'<span>{diversity} source{"s" if diversity != 1 else ""}</span>'
            f'<span>{age_str}</span>'
            f'<span>{momentum}</span>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Expandable drill-down
        with st.expander(f"View items in {label}", expanded=False):
            cluster_items = sb.query_fresh("items", {
                "select": "title,source,type,source_date,source_url,linear_identifier",
                "cluster_id": f"eq.{cluster['id']}",
                "order": "source_date.desc.nullslast",
                "limit": "20",
            })
            if cluster_items:
                df = pd.DataFrame(cluster_items)
                if "source_date" in df.columns:
                    df["source_date"] = pd.to_datetime(df["source_date"], errors="coerce").dt.strftime("%Y-%m-%d")
                st.dataframe(
                    df.rename(columns={
                        "title": "Title",
                        "source": "Source",
                        "type": "Type",
                        "source_date": "Date",
                        "linear_identifier": "Linear",
                        "source_url": "URL",
                    }),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"URL": st.column_config.LinkColumn("URL", display_text="Link")},
                )
            else:
                st.caption("No items found.")

# ---------------------------------------------------------------------------
# 5. Trending in Your Domains
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Trending in Your Domains")

recent_count = defaultdict(int)
previous_count = defaultdict(int)
for item in (recent_items or []):
    cid = item.get("cluster_id")
    if not cid or cid not in matched_ids:
        continue
    created = item.get("created_at", "")
    if created >= iso_7d:
        recent_count[cid] += 1
    else:
        previous_count[cid] += 1

# Build momentum data
cluster_labels = {c["id"]: c.get("label") or "Unlabeled" for c in matched}
momentum_data = []
for cid in recent_count:
    ratio = recent_count[cid] / (previous_count.get(cid, 0) + 1)
    momentum_data.append({
        "label": cluster_labels.get(cid, "Unknown"),
        "recent": recent_count[cid],
        "previous": previous_count.get(cid, 0),
        "momentum": ratio,
    })
momentum_data.sort(key=lambda x: x["momentum"], reverse=True)

if not momentum_data:
    st.caption("No trending clusters this week.")
else:
    col_chart, col_cards = st.columns([3, 2])

    with col_chart:
        top_8 = momentum_data[:8]
        fig = go.Figure(go.Bar(
            x=[d["momentum"] for d in top_8],
            y=[d["label"] for d in top_8],
            orientation="h",
            marker=dict(
                color=[d["momentum"] for d in top_8],
                colorscale="YlOrRd",
            ),
        ))
        fig.update_layout(
            title="Momentum (recent / previous ratio)",
            yaxis=dict(autorange="reversed"),
            height=350,
        )
        style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)

    with col_cards:
        for d in momentum_data[:3]:
            st.markdown(
                f'<div style="padding:12px 16px; margin-bottom:8px; border-radius:10px; '
                f'background:linear-gradient(145deg,#2A3154,#252B45); '
                f'border:1px solid rgba(168,85,247,0.1);">'
                f'<div style="font-weight:700; margin-bottom:4px;">{d["label"]}</div>'
                f'<div style="color:#22C55E; font-size:0.85rem; font-weight:600;">'
                f'+{d["recent"]} items this week</div>'
                f'<div style="font-size:0.75rem; opacity:0.5; margin-top:2px;">'
                f'momentum: {d["momentum"]:.1f}x</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# 6. New Discoveries
# ---------------------------------------------------------------------------

st.divider()
st.subheader("New Discoveries")
st.caption("Items added in the last 48 hours matching your domains")

# Filter to 48h items matching user domains
all_filtered = []
for item in (recent_items or []):
    if item.get("created_at", "") < iso_48h:
        continue
    cid = item.get("cluster_id")
    if cid and cid in matched_ids:
        all_filtered.append(item)
    elif not is_all:
        title_lower = (item.get("title") or "").lower()
        if any(d in title_lower for d in domain_lower):
            all_filtered.append(item)
    elif is_all:
        all_filtered.append(item)

SOURCE_TAB_MAP = {
    "All": None,
    "Linear": "linear",
    "Hacker News": "hackernews",
    "arXiv": "arxiv",
    "Conferences": "conference",
}

if not all_filtered:
    st.caption("No new items in the last 48 hours.")
else:
    tabs = st.tabs(list(SOURCE_TAB_MAP.keys()))
    for tab, (tab_label, source_key) in zip(tabs, SOURCE_TAB_MAP.items()):
        with tab:
            if source_key:
                filtered_items = [i for i in all_filtered if i.get("source") == source_key]
            else:
                filtered_items = all_filtered

            if not filtered_items:
                st.caption(f"No {tab_label.lower()} items in the last 48 hours.")
                continue

            for item in filtered_items[:20]:
                created = item.get("created_at", "").replace("T", " ").split(".")[0][:16]
                source = item.get("source", "")
                title = item.get("title", "Untitled")
                url = item.get("source_url", "")
                source_color = COLORS.get(source, COLORS["other"])

                title_html = (
                    f'<a href="{url}" target="_blank" style="color:inherit; text-decoration:none; '
                    f'border-bottom:1px solid rgba(255,255,255,0.2);">{title}</a>'
                    if url else title
                )

                st.markdown(
                    f'<div style="padding:6px 0; border-bottom:1px solid rgba(128,128,128,0.1);">'
                    f'<small><code>{created}</code> &nbsp; '
                    f'<span style="color:{source_color}; font-weight:600;">{source}</span> &nbsp; '
                    f'{title_html}</small></div>',
                    unsafe_allow_html=True,
                )

            if len(filtered_items) > 20:
                st.caption(f"Showing 20 of {len(filtered_items)} items")

# ---------------------------------------------------------------------------
# 7. You Might Also Like
# ---------------------------------------------------------------------------

st.divider()

if not is_all:
    with st.expander("You might also like", expanded=False):
        st.caption("Hot clusters outside your usual domains")
        if not unmatched:
            st.caption("No additional clusters to suggest.")
        else:
            for cluster in unmatched[:5]:
                score = float(cluster.get("hotness_score") or 0)
                label = cluster.get("label") or "Unlabeled"
                items_count = cluster.get("item_count", 0)
                summary = (cluster.get("summary") or "")[:120]
                score_color = "#EF4444" if score >= 0.6 else "#F59E0B" if score >= 0.4 else "#94A3B8"

                st.markdown(
                    f'<div style="padding:10px 16px; margin-bottom:6px; border-radius:8px; '
                    f'background:rgba(255,255,255,0.03); border:1px solid rgba(128,128,128,0.1);">'
                    f'<div style="display:flex; align-items:baseline; gap:10px; margin-bottom:4px;">'
                    f'<span style="font-weight:600;">{label}</span>'
                    f'<span style="font-size:0.75rem; color:{score_color}; font-weight:700;">{score:.2f}</span>'
                    f'<span style="font-size:0.75rem; opacity:0.5;">{items_count} items</span>'
                    f'</div>'
                    f'<div style="font-size:0.8rem; opacity:0.6;">{summary}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
