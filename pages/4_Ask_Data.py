"""Ask Data — AI-powered natural language querying.

Uses Claude via OpenRouter to translate natural language questions into
Supabase REST API queries, then renders results as tables/charts.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import supabase_client as sb
from lib import style

style.apply()
st.title("Ask Data")

with st.sidebar:
    st.caption("Powered by Claude Sonnet via OpenRouter")
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Resolve API key from st.secrets or os.environ
OPENROUTER_KEY = ""
try:
    OPENROUTER_KEY = st.secrets.get("OPENROUTER_KEY_STREAMLIT", "")
except FileNotFoundError:
    pass
if not OPENROUTER_KEY:
    OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY_STREAMLIT", "")
if not OPENROUTER_KEY:
    st.error(
        "Missing OPENROUTER_KEY_STREAMLIT. Add it to Streamlit Cloud secrets "
        "or set it as an environment variable."
    )
    st.stop()

SCHEMA_CONTEXT = """You are a data analyst for Lunar Ventures, a VC fund. You answer questions about their ambient sourcing pipeline by generating Supabase PostgREST queries.

## Database Schema

### items — All investment themes and deals
Columns: id (UUID PK), type ('theme'/'deal'), title (TEXT), description (TEXT), summary (TEXT), source ('linear'/'hackernews'/'arxiv'/'conference'/'tigerclaw'), source_url (TEXT), linear_identifier (TEXT, e.g. 'THE-2398'), stage ('raw'/'triage'/'curated'/'scored'/'setup'/'live'/'disqualified'), signal_strength ('strong'/'medium'/'weak'), priority (INT 0-4), source_labels (TEXT[]), sector_labels (TEXT[]), cluster_id (UUID FK), created_at (TIMESTAMPTZ), source_date (TIMESTAMPTZ)

### clusters — Groups of similar items
Columns: id (UUID PK), label (TEXT), summary (TEXT), item_count (INT), source_diversity (INT), hotness_score (FLOAT 0-1), first_seen_at (TIMESTAMPTZ), last_surfaced_at (TIMESTAMPTZ)

### eval_samples — Evaluation feedback
Columns: id (UUID PK), item_id (UUID FK), batch_id (TEXT, e.g. '2026-W11'), source (TEXT), reviewer (TEXT), sample_pool ('hot'/'random'), classification ('signal'/'weak_signal'/'shareable'/'noise'), comment (TEXT), created_at (TIMESTAMPTZ)

### cost_log — API cost tracking
Columns: id (UUID PK), workflow_key (TEXT), model (TEXT), input_tokens (BIGINT), output_tokens (BIGINT), total_cost (DECIMAL), created_at (TIMESTAMPTZ)

## Available RPCs
- get_ingestion_stats(p_days INT) → rows with: day, source, type, item_count
- get_hot_clusters(min_score FLOAT, lim INT) → cluster rows
- get_cost_stats(p_days INT) → rows with: day, workflow_key, model, request_count, total_input_tokens, total_output_tokens, total_cost

## PostgREST Query Syntax (use these in params)
- Filtering: "column": "eq.value", "column": "gt.5", "column": "ilike.*keyword*", "column": "in.(a,b,c)"
- Selecting: "select": "col1,col2,col3"
- Ordering: "order": "column.desc"
- Limiting: "limit": "10"
- Date filtering: "created_at": "gte.2026-03-10T00:00:00"
- Not null: "column": "not.is.null"
- Count: include "select": "id" with limit for approximate count

## Response Format
Return ONLY a JSON object (no markdown, no explanation outside JSON):
{
  "query_type": "rest" or "rpc",
  "table": "table_name",  // for rest
  "function": "fn_name",  // for rpc
  "params": {},            // PostgREST params or RPC params
  "explanation": "What this query does",
  "display": "table" | "bar_chart" | "line_chart" | "pie_chart" | "metric",
  "chart_config": {"x": "col", "y": "col", "color": "col"}  // optional
}

## Examples

Q: "What's hot right now?"
{"query_type": "rpc", "function": "get_hot_clusters", "params": {"min_score": 0.3, "lim": 10}, "explanation": "Top 10 clusters with hotness score above 0.3", "display": "table"}

Q: "How many items from arxiv this month?"
{"query_type": "rest", "table": "items", "params": {"select": "id", "source": "eq.arxiv", "created_at": "gte.2026-03-01T00:00:00", "limit": "1000"}, "explanation": "Count of arxiv items created this month", "display": "metric"}

Q: "Cost this week"
{"query_type": "rpc", "function": "get_cost_stats", "params": {"p_days": 7}, "explanation": "Cost breakdown for the last 7 days", "display": "bar_chart", "chart_config": {"x": "workflow_key", "y": "total_cost"}}

Q: "Top sources today"
{"query_type": "rpc", "function": "get_ingestion_stats", "params": {"p_days": 1}, "explanation": "Today's ingestion by source", "display": "bar_chart", "chart_config": {"x": "source", "y": "item_count"}}
"""

# --- Quick queries ---
st.markdown("**Quick queries:**")
quick_cols = st.columns(4)
quick_queries = [
    "What's hot right now?",
    "Ingestion stats this week",
    "Top sources today",
    "Clusters with multiple sources",
]
for col, q in zip(quick_cols, quick_queries):
    if col.button(q, use_container_width=True, key=f"quick_{q}"):
        st.session_state["ask_input"] = q
        st.rerun()

st.divider()

# --- Chat interface ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown(
        '<p style="color: #94a3b8; text-align: center; margin: 3rem 0;">'
        'Ask questions in natural language. Examples:<br>'
        '"How many themes were added this week?" · '
        '"Show cost breakdown by model" · '
        '"Which clusters have items from multiple sources?"'
        '</p>',
        unsafe_allow_html=True,
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("content"):
            st.markdown(msg["content"])
        if msg.get("dataframe") is not None:
            st.dataframe(
                pd.DataFrame(msg["dataframe"]),
                use_container_width=True,
                hide_index=True,
            )

prompt = st.chat_input("Ask a question about your data...") or st.session_state.pop("ask_input", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Build conversation history (last 6 messages for context)
            history = []
            for msg in st.session_state.messages[-6:]:
                if msg["role"] == "user":
                    history.append({"role": "user", "content": msg["content"]})
                elif msg.get("content") and msg["role"] == "assistant":
                    history.append({"role": "assistant", "content": msg["content"]})

            body = json.dumps({
                "model": "anthropic/claude-sonnet-4",
                "messages": [
                    {"role": "system", "content": SCHEMA_CONTEXT},
                    *history,
                ],
                "temperature": 0,
                "max_tokens": 1024,
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                },
            )
            query_spec = None
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    ai_response = json.loads(resp.read())
                content = ai_response["choices"][0]["message"]["content"]

                # Parse JSON from response (handle markdown code blocks)
                if "```" in content:
                    # Extract first code block
                    parts = content.split("```")
                    code_block = parts[1] if len(parts) > 1 else content
                    if code_block.startswith("json"):
                        code_block = code_block[4:]
                    content = code_block
                query_spec = json.loads(content.strip())
            except json.JSONDecodeError:
                # AI returned non-JSON — show it as text
                st.markdown(content if content else "Could not parse response.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": content or "Could not parse response.",
                })
            except Exception as e:
                st.error(f"AI query failed: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {e}",
                })

        if query_spec is None:
            st.stop()

        # Execute the query
        explanation = query_spec.get("explanation", "")
        st.caption(explanation)

        data = None
        try:
            if query_spec["query_type"] == "rpc":
                data = sb.rpc_call(
                    query_spec["function"],
                    query_spec.get("params", {}),
                )
            else:
                data = sb.query_table(
                    query_spec["table"],
                    query_spec.get("params", {}),
                )
        except Exception as e:
            st.error(f"Query failed: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Query error: {e}",
            })

        if not data:
            if data is None:
                pass  # Query errored — already handled
            else:
                st.info("No results found.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "No results found.",
                })
            st.stop()

        df = pd.DataFrame(data)
        display = query_spec.get("display", "table")
        chart_config = query_spec.get("chart_config", {})
        msg_data = {
            "role": "assistant",
            "content": explanation,
            "dataframe": df.to_dict(orient="records"),
        }

        if display == "metric":
            if len(df) == 1 and len(df.columns) <= 4:
                cols = st.columns(len(df.columns))
                for col, c in zip(cols, df.columns):
                    col.metric(c, df[c].iloc[0])
            else:
                # Metric display for counts — show total rows
                st.metric("Results", f"{len(df):,} rows")
                st.dataframe(df, use_container_width=True, hide_index=True)

        elif display in ("bar_chart", "line_chart", "pie_chart"):
            x = chart_config.get("x", df.columns[0] if len(df.columns) > 0 else None)
            y = chart_config.get("y", df.columns[1] if len(df.columns) > 1 else df.columns[0] if df.columns.any() else None)
            color = chart_config.get("color")

            # Validate columns
            if x and x not in df.columns:
                x = df.columns[0] if len(df.columns) > 0 else None
            if y and y not in df.columns:
                y = df.columns[1] if len(df.columns) > 1 else df.columns[0] if len(df.columns) > 0 else None
            if color and color not in df.columns:
                color = None

            chart_rendered = False
            if x and y:
                try:
                    if display == "bar_chart":
                        fig = px.bar(df, x=x, y=y, color=color)
                    elif display == "line_chart":
                        fig = px.line(df, x=x, y=y, color=color)
                    else:
                        fig = px.pie(df, names=x, values=y)
                    fig.update_layout(margin=dict(t=10))
                    st.plotly_chart(fig, use_container_width=True)
                    chart_rendered = True
                except Exception:
                    pass

            # Always show data table below chart
            st.dataframe(df, use_container_width=True, hide_index=True)

        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.session_state.messages.append(msg_data)
