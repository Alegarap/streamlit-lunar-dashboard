"""Clusters & What's Hot — cluster health, top themes, and source diversity."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib.charts import COLORS, metric_row

st.set_page_config(page_title="Clusters | Lunar BI", layout="wide", page_icon="🔬")
st.title("🔬 Clusters & What's Hot")

# --- Overview metrics ---
clusters = sb.query("clusters", {
    "select": "id,label,summary,item_count,source_diversity,hotness_score,first_seen_at,last_surfaced_at",
    "order": "hotness_score.desc.nullslast",
    "limit": "500",
})

total_items_data = sb.query("items", {
    "select": "id",
    "limit": "1",
})
# Get total counts via separate queries
all_items = sb.query("items", {"select": "id,cluster_id", "limit": "3000"})
total_items = len(all_items)
clustered = sum(1 for i in all_items if i.get("cluster_id"))
unclustered = total_items - clustered
clustering_rate = (clustered / total_items * 100) if total_items > 0 else 0

total_clusters = len(clusters)
hot_clusters = sum(1 for c in clusters if (c.get("hotness_score") or 0) > 0.3)
labeled_clusters = sum(1 for c in clusters if c.get("label"))

metric_row([
    ("Total Items", f"{total_items:,}", None),
    ("Clustered", f"{clustered:,}", f"{clustering_rate:.0f}%"),
    ("Unclustered", f"{unclustered:,}", None),
    ("Total Clusters", total_clusters, f"{labeled_clusters} labeled"),
    ("Hot Clusters (>0.3)", hot_clusters, None),
])

st.divider()

# --- Top 10 Hot Clusters ---
st.subheader("🔥 Top Hot Clusters")
if clusters:
    df_clusters = pd.DataFrame(clusters)
    df_clusters["hotness_score"] = pd.to_numeric(df_clusters["hotness_score"], errors="coerce").fillna(0)
    top = df_clusters.nlargest(15, "hotness_score")

    fig = px.bar(
        top, x="hotness_score", y="label",
        orientation="h",
        title="Hotness Score — Top 15 Clusters",
        labels={"hotness_score": "Hotness Score", "label": "Cluster"},
        color="hotness_score",
        color_continuous_scale="YlOrRd",
    )
    fig.update_layout(yaxis={"autorange": "reversed"})
    st.plotly_chart(fig, use_container_width=True)

    # Expandable drill-down
    st.subheader("Cluster Details")
    for _, cluster in top.iterrows():
        score = cluster["hotness_score"]
        label = cluster["label"] or "Unlabeled"
        with st.expander(f"**{label}** — score: {score:.2f} | {cluster['item_count']} items | {cluster['source_diversity']} sources"):
            if cluster.get("summary"):
                st.write(cluster["summary"])
            # Fetch items for this cluster
            items = sb.query("items", {
                "select": "title,source,type,source_date,linear_identifier",
                "cluster_id": f"eq.{cluster['id']}",
                "order": "source_date.desc.nullslast",
                "limit": "20",
            })
            if items:
                st.dataframe(
                    pd.DataFrame(items).rename(columns={
                        "title": "Title",
                        "source": "Source",
                        "type": "Type",
                        "source_date": "Date",
                        "linear_identifier": "Linear",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

# --- Hotness distribution ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("Hotness Score Distribution")
    if clusters:
        scores = [c.get("hotness_score") or 0 for c in clusters]
        fig = px.histogram(
            x=scores, nbins=20,
            title="Cluster Hotness Distribution",
            labels={"x": "Hotness Score", "y": "Count"},
        )
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Source Diversity Distribution")
    if clusters:
        diversities = [c.get("source_diversity") or 0 for c in clusters]
        fig = px.histogram(
            x=diversities, nbins=max(diversities) if diversities else 5,
            title="Source Diversity per Cluster",
            labels={"x": "Number of Distinct Sources", "y": "Clusters"},
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Eval metrics (if eval_samples table has data) ---
st.divider()
st.subheader("📋 Evaluation Metrics")
try:
    eval_data = sb.query("eval_samples", {
        "select": "batch_id,classification,source,sample_pool",
        "classification": "not.is.null",
        "limit": "1000",
    })
    if eval_data:
        df_eval = pd.DataFrame(eval_data)

        # Classification breakdown
        class_counts = df_eval["classification"].value_counts()
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(
                names=class_counts.index,
                values=class_counts.values,
                title="Overall Classification Distribution",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # By batch
            batch_class = df_eval.groupby(["batch_id", "classification"]).size().reset_index(name="count")
            fig = px.bar(
                batch_class, x="batch_id", y="count", color="classification",
                title="Classification by Batch",
                barmode="stack",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Signal rate by source
        st.markdown("**Signal Rate by Source**")
        signal_by_src = df_eval.groupby("source").apply(
            lambda g: (g["classification"].isin(["signal", "weak_signal"])).mean() * 100
        ).reset_index(name="signal_rate")
        st.dataframe(
            signal_by_src.rename(columns={"source": "Source", "signal_rate": "Signal Rate (%)"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No evaluation feedback collected yet. Run the evaluation loop skill to start.")
except Exception:
    st.info("Evaluation data not available. The `eval_samples` table may not have data yet.")
