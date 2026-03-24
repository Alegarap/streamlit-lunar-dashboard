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
from lib import style
from lib.charts import COLORS, metric_row, style_fig

style.apply()

# --- Title + toggle on the same row ---
profile = st.session_state.get("user_profile", {})
user_domains = profile.get("domains", [])
has_domains = user_domains and user_domains != ["all"]

title_col, toggle_col = st.columns([3, 1])
with title_col:
    st.title("Clusters & What's Hot")
with toggle_col:
    show_all = True
    if has_domains:
        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        show_all = not st.toggle(
            "Relevant to me",
            value=True,
            help=f"Filter clusters to your domains: {', '.join(user_domains[:5])}{'...' if len(user_domains) > 5 else ''}",
        )

with st.sidebar:
    st.caption("Data refreshes every 5 minutes")
    if st.button("Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Fetch data ---
with st.spinner("Loading clusters..."):
    clusters = sb.query_fresh("clusters", {
        "select": "id,label,summary,item_count,source_diversity,hotness_score,first_seen_at,last_surfaced_at",
        "order": "hotness_score.desc.nullslast",
        "limit": "500",
    })

all_clusters = clusters  # keep unfiltered for metrics

# Filter clusters by user domains if toggle is on
if has_domains and not show_all and clusters:
    domain_lower = [d.lower() for d in user_domains]

    def _cluster_matches(c):
        text = ((c.get("label") or "") + " " + (c.get("summary") or "")).lower()
        return any(d in text for d in domain_lower)

    clusters = [c for c in clusters if _cluster_matches(c)]

# --- 3 key metrics ---
total_items = sb.count_rows("items")
clustered_items = sb.count_rows("items", {"cluster_id": "not.is.null"})
clustering_rate = (clustered_items / total_items * 100) if total_items > 0 else 0

total_clusters = len(all_clusters)
hot_clusters = sum(1 for c in all_clusters if (c.get("hotness_score") or 0) > 0.3)
filtered_count = len(clusters) if (has_domains and not show_all) else None

metric_row([
    ("Total Clusters", total_clusters, None),
    ("Hot (>0.3)", hot_clusters, None),
    ("Clustering Rate", f"{clustering_rate:.0f}%", f"{clustered_items:,} of {total_items:,}"),
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

    st.subheader("Top Clusters")
    st.caption("Showing top 15 labeled clusters by hotness score")

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
        textfont=dict(size=12, family="Fira Sans"),
    ))
    fig.update_layout(
        height=450,
        xaxis_title="Hotness Score",
        yaxis_title="",
        xaxis=dict(range=[0, 1.05]),
        margin=dict(l=10, r=40, t=10, b=40),
        showlegend=False,
        font=dict(family="Fira Sans", size=13),
        legend=dict(font=dict(size=13, family="Fira Sans")),
    )
    style_fig(fig)
    st.plotly_chart(fig, use_container_width=True)

    # --- Cluster Details — two-column layout ---
    st.subheader("Cluster Details")
    col_left, col_right = st.columns(2)
    for idx, (_, cluster) in enumerate(top.iterrows()):
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

        target_col = col_left if idx % 2 == 0 else col_right

        with target_col:
            with st.expander(
                f"{score_color} **{label}** — {score:.2f} · {items_count} items · {diversity} source{'s' if diversity != 1 else ''}"
            ):
                detail_cols = st.columns([2, 1])
                with detail_cols[0]:
                    if cluster.get("summary"):
                        st.markdown(f"*{cluster['summary']}*")
                with detail_cols[1]:
                    if cluster.get("first_seen_at"):
                        first = str(cluster["first_seen_at"])[:10]
                        st.caption(f"First seen: {first}")
                    if cluster.get("last_surfaced_at"):
                        last = str(cluster["last_surfaced_at"])[:10]
                        st.caption(f"Last active: {last}")

                # Fetch items for this cluster
                items = sb.query_fresh("items", {
                    "select": "title,source,type,source_date,linear_identifier,source_url",
                    "cluster_id": f"eq.{cluster['id']}",
                    "order": "source_date.desc.nullslast",
                    "limit": "20",
                })
                if items:
                    df_items = pd.DataFrame(items)
                    if "source_date" in df_items.columns:
                        df_items["source_date"] = pd.to_datetime(
                            df_items["source_date"], errors="coerce"
                        ).dt.strftime("%Y-%m-%d")
                    st.dataframe(
                        df_items.rename(columns={
                            "title": "Title",
                            "source": "Source",
                            "type": "Type",
                            "source_date": "Date",
                            "linear_identifier": "Linear",
                            "source_url": "URL",
                        }),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "URL": st.column_config.LinkColumn("URL", display_text="Link"),
                        },
                    )

# --- Distributions (collapsed) ---
with st.expander("Distributions"):
    dist_col1, dist_col2 = st.columns(2)

    with dist_col1:
        st.markdown("**Hotness Distribution**")
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
                font=dict(family="Fira Sans", size=13),
            )
            style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)

    with dist_col2:
        st.markdown("**Source Diversity**")
        if clusters:
            diversities = [c.get("source_diversity") or 0 for c in clusters]
            max_div = max(diversities) if diversities else 5
            fig = px.histogram(
                x=diversities, nbins=max(max_div, 1),
                labels={"x": "Distinct Sources", "y": "Clusters"},
                color_discrete_sequence=["#14B8A6"],
            )
            fig.update_layout(
                margin=dict(t=10),
                showlegend=False,
                font=dict(family="Fira Sans", size=13),
            )
            style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)

# --- Eval metrics (collapsed) ---
with st.expander("Evaluation Metrics"):
    try:
        eval_data = sb.query_fresh("eval_samples", {
            "select": "batch_id,classification,source,sample_pool",
            "classification": "not.is.null",
            "limit": "1000",
        })
        if eval_data:
            df_eval = pd.DataFrame(eval_data)

            eval_col1, eval_col2 = st.columns(2)
            with eval_col1:
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
                fig.update_layout(font=dict(family="Fira Sans", size=13))
                style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)

            with eval_col2:
                batch_class = df_eval.groupby(["batch_id", "classification"]).size().reset_index(name="count")
                fig = px.bar(
                    batch_class, x="batch_id", y="count", color="classification",
                    title="Classification by Batch",
                    barmode="stack",
                    color_discrete_map=colors,
                )
                fig.update_layout(font=dict(family="Fira Sans", size=13))
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
