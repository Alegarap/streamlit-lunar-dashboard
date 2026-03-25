"""Clusters & What's Hot — cluster health, top themes, and source diversity."""

import sys
import urllib.error
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib import linear_client as lc
from lib import style
from lib.charts import COLORS, metric_row, style_fig, item_detail_viewer

style.apply()

# --- User profile for Linear creation ---
_profile = st.session_state.get("user_profile", {})


def _bulk_create_issues(selected_keys, options_map, profile):
    """Create multiple Linear issues from selected items."""
    import json
    import urllib.request

    created_count = 0
    errors = []
    progress = st.progress(0)
    status = st.empty()

    for idx, key in enumerate(selected_keys):
        item = options_map[key]
        team = "THE" if item["type"] == "theme" else "DEAL"
        title = item["title"]
        if item.get("source") == "arxiv":
            title = f"📜 {title}"
        desc = item.get("description") or item.get("summary") or ""
        labels = item.get("source_labels") or []

        status.text(f"Creating {idx + 1}/{len(selected_keys)}: {title[:50]}...")
        result = lc.create_issue(
            team=team, title=title, description=desc,
            assignee_id=profile.get("linear_id"),
            label_names=labels,
        )
        if "error" in result:
            errors.append(f"{title[:40]}: {result['error']}")
        else:
            created_count += 1
            try:
                url_base, _ = sb._get_credentials()
                hdrs = sb._headers()
                hdrs["Prefer"] = "return=minimal"
                body = json.dumps({
                    "linear_identifier": result.get("identifier", ""),
                    "linear_issue_id": result.get("id", ""),
                }).encode()
                req = urllib.request.Request(
                    f"{url_base}/rest/v1/items?id=eq.{item['id']}",
                    data=body, headers=hdrs, method="PATCH",
                )
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                pass

        progress.progress((idx + 1) / len(selected_keys))

    status.empty()
    progress.empty()
    if created_count:
        st.success(f"Created {created_count} issue{'s' if created_count != 1 else ''} in Linear!")
    for err in errors:
        st.error(err)
st.title("Clusters & What's Hot")

# --- User profile for domain filtering ---
profile = st.session_state.get("user_profile", {})
user_domains = profile.get("domains", [])
has_domains = user_domains and user_domains != ["all"]

with st.sidebar:
    st.caption("Data refreshes every 5 minutes")
    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Domain filter toggle ---
show_all = True
if has_domains:
    filter_col1, filter_col2 = st.columns([3, 1])
    with filter_col1:
        show_all = not st.toggle(
            "Relevant to me",
            value=True,
            help=f"Filter clusters to your domains: {', '.join(user_domains[:5])}{'...' if len(user_domains) > 5 else ''}",
        )

# --- Overview metrics ---
with st.spinner("Loading clusters..."):
    clusters = sb.query_fresh("clusters", {
        "select": "id,label,summary,item_count,source_diversity,hotness_score,first_seen_at,last_surfaced_at",
        "order": "hotness_score.desc.nullslast",
        "limit": "500",
    })

clusters = [c for c in clusters if c.get("item_count", 0) > 0]
all_clusters = clusters  # keep unfiltered for metrics

# Filter clusters by user domains if toggle is on
if has_domains and not show_all and clusters:
    domain_lower = [d.lower() for d in user_domains]

    def _cluster_matches(c):
        text = ((c.get("label") or "") + " " + (c.get("summary") or "")).lower()
        return any(d in text for d in domain_lower)

    clusters = [c for c in clusters if _cluster_matches(c)]

total_items = sb.count_rows("items")
clustered_items = sb.count_rows("items", {"cluster_id": "not.is.null"})
unclustered = total_items - clustered_items
clustering_rate = (clustered_items / total_items * 100) if total_items > 0 else 0

total_clusters = len(all_clusters)
hot_clusters = sum(1 for c in all_clusters if (c.get("hotness_score") or 0) > 0.3)
labeled_clusters = sum(1 for c in all_clusters if c.get("label"))
filtered_count = len(clusters) if (has_domains and not show_all) else None

metric_row([
    ("Items", f"{total_items:,}", None),
    ("Clustered", f"{clustered_items:,}", f"{clustering_rate:.0f}%"),
    ("Free", f"{unclustered:,}", None),
    ("Clusters", total_clusters, f"{labeled_clusters} labeled"),
    ("Hot (>0.3)", hot_clusters, None),
])

if filtered_count is not None:
    st.caption(f"Showing {filtered_count} clusters matching your domains (of {total_clusters} total)")

st.divider()

# --- Top Hot Clusters ---
if clusters:
    df_clusters = pd.DataFrame(clusters)
    df_clusters["hotness_score"] = pd.to_numeric(df_clusters["hotness_score"], errors="coerce").fillna(0).clip(0, 1)
    df_clusters["label"] = df_clusters["label"].fillna("Unlabeled")
    # Filter to labeled clusters for the top chart
    labeled = df_clusters[df_clusters["label"] != "Unlabeled"]
    top = labeled.nlargest(15, "hotness_score") if len(labeled) >= 15 else df_clusters.nlargest(15, "hotness_score")

    st.subheader("Top 15 Hot Clusters")

    # Horizontal bar chart with gradient colors
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top["hotness_score"].values[::-1],
        y=top["label"].values[::-1],
        orientation="h",
        marker=dict(
            color=top["hotness_score"].values[::-1],
            colorscale="YlOrRd",
            cmin=0, cmax=1,
        ),
        text=[f"{s:.2f}" for s in top["hotness_score"].values[::-1]],
        textposition="outside",
        textfont=dict(size=12),
    ))
    fig.update_layout(
        height=500,
        xaxis_title="Hotness Score",
        yaxis_title="",
        xaxis=dict(range=[0, 1.05]),
        margin=dict(l=10, r=40, t=10, b=40),
        showlegend=False,
    )
    style_fig(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Drill-down cards
    st.subheader("Cluster Details")
    for _, cluster in top.iterrows():
        score = cluster["hotness_score"]
        label = cluster["label"]
        items_count = cluster["item_count"]
        diversity = cluster["source_diversity"]

        # Color-code the score
        if score >= 0.6:
            score_color = "🔴"
        elif score >= 0.4:
            score_color = "🟠"
        elif score >= 0.3:
            score_color = "🟡"
        else:
            score_color = "⚪"

        with st.expander(
            f"{score_color} **{label}** — {score:.2f} · {items_count} items · {diversity} source{'s' if diversity != 1 else ''}"
        ):
            cols = st.columns([2, 1])
            with cols[0]:
                if cluster.get("summary"):
                    st.markdown(f"*{cluster['summary']}*")
            with cols[1]:
                if cluster.get("first_seen_at"):
                    first = str(cluster["first_seen_at"])[:10]
                    st.caption(f"First seen: {first}")
                if cluster.get("last_surfaced_at"):
                    last = str(cluster["last_surfaced_at"])[:10]
                    st.caption(f"Last active: {last}")

            # Fetch items for this cluster (with full data for Linear creation)
            items = sb.query_fresh("items", {
                "select": "id,title,source,type,source_date,linear_identifier,source_url,source_labels,sector_labels,description,summary",
                "cluster_id": f"eq.{cluster['id']}",
                "order": "source_date.desc.nullslast",
                "limit": "200",
            })
            if items:
                df_items = pd.DataFrame(items)
                display_cols = ["title", "source", "type", "source_date", "linear_identifier", "source_url"]
                df_display = df_items[[c for c in display_cols if c in df_items.columns]].copy()
                if "source_date" in df_display.columns:
                    df_display["source_date"] = pd.to_datetime(
                        df_display["source_date"], errors="coerce"
                    ).dt.strftime("%Y-%m-%d")
                st.dataframe(
                    df_display.rename(columns={
                        "title": "Title", "source": "Source", "type": "Type",
                        "source_date": "Date", "linear_identifier": "Linear",
                        "source_url": "URL",
                    }),
                    use_container_width=True, hide_index=True,
                    column_config={"URL": st.column_config.LinkColumn("URL", display_text="Link")},
                )

                # Item detail viewer
                item_detail_viewer(items, key_prefix=f"cl_{cluster['id']}")

                # Bulk add to Linear
                not_in_linear = [i for i in items if not i.get("linear_identifier")]
                if not_in_linear:
                    st.markdown(f"**{len(not_in_linear)} item{'s' if len(not_in_linear) != 1 else ''} not yet in Linear:**")
                    options = {f"{i['title'][:80]} ({i['type']}, {i['source']})": i for i in not_in_linear}
                    selected = st.multiselect(
                        "Select items to create in Linear",
                        options=list(options.keys()),
                        default=[],
                        key=f"cl_bulk_{cluster['id']}",
                    )
                    if selected:
                        col_btn, col_info = st.columns([1, 3])
                        with col_btn:
                            create_clicked = st.button(
                                f"Create {len(selected)} in Linear",
                                key=f"cl_create_{cluster['id']}",
                                type="primary",
                            )
                        with col_info:
                            st.caption("Themes → THE, Deals → DEAL. Labels + assignee added automatically.")
                        if create_clicked:
                            _bulk_create_issues(selected, options, _profile)

# --- Distributions ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("Hotness Distribution")
    if clusters:
        scores = [float(c.get("hotness_score") or 0) for c in clusters]
        fig = px.histogram(
            x=scores, nbins=20,
            labels={"x": "Hotness Score", "y": "Clusters"},
            color_discrete_sequence=["#6366F1"],
        )
        fig.update_layout(
            xaxis=dict(range=[0, 1]),
            margin=dict(t=10),
            showlegend=False,
        )
        style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Source Diversity")
    if clusters:
        diversities = [c.get("source_diversity") or 0 for c in clusters]
        max_div = max(diversities) if diversities else 5
        fig = px.histogram(
            x=diversities, nbins=max(max_div, 1),
            labels={"x": "Distinct Sources", "y": "Clusters"},
            color_discrete_sequence=["#14B8A6"],
        )
        fig.update_layout(margin=dict(t=10), showlegend=False)
        style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)

# --- Eval metrics ---
st.divider()
st.subheader("Evaluation Metrics")
try:
    eval_data = sb.query_fresh("eval_samples", {
        "select": "batch_id,classification,source,sample_pool",
        "classification": "not.is.null",
        "limit": "1000",
    })
    if eval_data:
        df_eval = pd.DataFrame(eval_data)

        col1, col2 = st.columns(2)
        with col1:
            class_counts = df_eval["classification"].value_counts()
            colors = {
                "signal": "#22C55E",
                "weak_signal": "#EAB308",
                "shareable": "#3B82F6",
                "noise": "#EF4444",
            }
            fig = px.pie(
                names=class_counts.index,
                values=class_counts.values,
                title="Classification Distribution",
                color=class_counts.index,
                color_discrete_map=colors,
            )
            style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            batch_class = df_eval.groupby(["batch_id", "classification"]).size().reset_index(name="count")
            fig = px.bar(
                batch_class, x="batch_id", y="count", color="classification",
                title="Classification by Batch",
                barmode="stack",
                color_discrete_map=colors,
            )
            style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)

        # Signal rate by source
        st.markdown("**Signal Rate by Source**")
        is_signal = df_eval["classification"].isin(["signal", "weak_signal"])
        df_eval_copy = df_eval.assign(_is_signal=is_signal)
        signal_by_src = (
            df_eval_copy.groupby("source")["_is_signal"]
            .mean()
            .mul(100)
            .reset_index(name="signal_rate")
        )
        st.dataframe(
            signal_by_src.rename(columns={
                "source": "Source",
                "signal_rate": "Signal Rate (%)",
            }),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Signal Rate (%)": st.column_config.ProgressColumn(
                    min_value=0, max_value=100, format="%.0f%%",
                ),
            },
        )
    else:
        st.info("No evaluation feedback collected yet.")
except urllib.error.HTTPError as e:
    if e.code == 404:
        st.info("Evaluation data not available.")
    else:
        st.warning(f"Failed to fetch eval data (HTTP {e.code}).")
except Exception:
    st.info("Evaluation data not available.")
