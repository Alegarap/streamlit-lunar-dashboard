"""Ask Data — AI-powered natural language querying.

Uses Claude via OpenRouter to translate natural language questions into
SQL queries against Supabase, then renders results as tables/charts.
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
from lib.charts import format_cost

st.title("Ask Data")

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
        "or relaunch locally via `claude-ops`."
    )
    st.stop()

SCHEMA_CONTEXT = """You are a data analyst for Lunar Ventures. You help answer questions about the ambient sourcing pipeline by generating Supabase REST API queries.

## Database Schema

### items — All investment themes and deals
- id (UUID PK), type (TEXT: 'theme'/'deal'), title (TEXT), description (TEXT), summary (TEXT)
- source (TEXT: 'linear','hackernews','arxiv','conference','tigerclaw')
- source_url (TEXT), linear_issue_id (TEXT), linear_identifier (TEXT: 'THE-2398')
- stage (TEXT: 'raw','triage','curated','scored','setup','live','disqualified')
- signal_strength (TEXT: 'strong','medium','weak'), priority (INT 0-4)
- source_labels (TEXT[]), sector_labels (TEXT[]), metadata (JSONB), scores (JSONB)
- cluster_id (UUID FK -> clusters), embedding (vector 1536)
- created_at (TIMESTAMPTZ), updated_at, source_date, synced_at

### clusters — Groups of similar items
- id (UUID PK), label (TEXT), summary (TEXT), item_count (INT)
- source_diversity (INT), hotness_score (FLOAT 0-1)
- first_seen_at (TIMESTAMPTZ), last_surfaced_at (TIMESTAMPTZ)

### eval_samples — Evaluation feedback
- id (UUID PK), item_id (UUID FK), batch_id (TEXT: '2026-W11')
- source (TEXT), reviewer (TEXT), linear_issue_id (TEXT)
- sample_pool (TEXT: 'hot'/'random'), classification (TEXT: 'signal'/'weak_signal'/'shareable'/'noise')
- comment (TEXT), collected_at (TIMESTAMPTZ), created_at (TIMESTAMPTZ)

### cost_log — API cost tracking (may not exist yet)
- id (UUID PK), workflow_key (TEXT), api_type (TEXT), model (TEXT)
- input_tokens (BIGINT), output_tokens (BIGINT), total_cost (DECIMAL)
- execution_id (TEXT), api_key_name (TEXT), created_at (TIMESTAMPTZ)

## Available RPCs
- get_ingestion_stats(p_days INT) -> day, source, type, item_count
- get_hot_clusters(min_score FLOAT, lim INT) -> cluster rows
- get_cost_stats(p_days INT) -> day, workflow_key, model, request_count, tokens, cost

## Response Format
Return a JSON object with:
- "query_type": "rest" (Supabase REST API) or "rpc" (Supabase RPC call)
- For "rest": "table" (string), "params" (object with PostgREST query params)
- For "rpc": "function" (string), "params" (object)
- "explanation": Brief explanation of what the query does
- "display": "table", "bar_chart", "line_chart", "pie_chart", "metric", or "text"
- "chart_config": optional object with "x", "y", "color" keys for chart rendering

Only return the JSON object, no other text.
"""

# --- Quick queries ---
st.markdown("**Quick queries:**")
quick_cols = st.columns(4)
quick_queries = [
    "What's hot right now?",
    "Ingestion stats this week",
    "Top sources today",
    "Clusters with multi-source convergence",
]
for col, q in zip(quick_cols, quick_queries):
    if col.button(q, use_container_width=True, key=f"quick_{q}"):
        st.session_state["ask_input"] = q
        st.rerun()

# --- Chat interface ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("content"):
            st.markdown(msg["content"])
        if msg.get("dataframe") is not None:
            st.dataframe(pd.DataFrame(msg["dataframe"]), use_container_width=True, hide_index=True)

prompt = st.chat_input("Ask a question about your data...") or st.session_state.pop("ask_input", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Call OpenRouter
            body = json.dumps({
                "model": "anthropic/claude-sonnet-4",
                "messages": [
                    {"role": "system", "content": SCHEMA_CONTEXT},
                    {"role": "user", "content": prompt},
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
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                query_spec = json.loads(content.strip())
            except Exception as e:
                st.error(f"AI query failed: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})

        if query_spec is None:
            st.stop()

        # Execute the query
        explanation = query_spec.get("explanation", "")
        st.caption(explanation)

        data = None
        try:
            if query_spec["query_type"] == "rpc":
                data = sb.rpc_call(query_spec["function"], query_spec.get("params", {}))
            else:
                data = sb.query_table(query_spec["table"], query_spec.get("params", {}))
        except Exception as e:
            st.error(f"Query failed: {e}")
            st.session_state.messages.append({"role": "assistant", "content": f"Query error: {e}"})

        if not data:
            if data is None:
                # Query itself errored — already handled above
                pass
            else:
                st.info("No results found.")
                st.session_state.messages.append({"role": "assistant", "content": "No results found."})
            st.stop()

        df = pd.DataFrame(data)
        display = query_spec.get("display", "table")
        chart_config = query_spec.get("chart_config", {})
        msg_data = {"role": "assistant", "content": explanation, "dataframe": df.to_dict(orient="records")}

        if display == "table" or display == "text":
            st.dataframe(df, use_container_width=True, hide_index=True)

        elif display == "metric" and len(df) == 1:
            cols = st.columns(len(df.columns))
            for col, c in zip(cols, df.columns):
                col.metric(c, df[c].iloc[0])

        elif display in ("bar_chart", "line_chart", "pie_chart"):
            x = chart_config.get("x", df.columns[0] if len(df.columns) > 0 else None)
            y = chart_config.get("y", df.columns[1] if len(df.columns) > 1 else (df.columns[0] if len(df.columns) > 0 else None))
            color = chart_config.get("color")

            # Validate columns exist in the DataFrame
            if x and x not in df.columns:
                x = df.columns[0] if len(df.columns) > 0 else None
            if y and y not in df.columns:
                y = df.columns[1] if len(df.columns) > 1 else (df.columns[0] if len(df.columns) > 0 else None)
            if color and color not in df.columns:
                color = None

            if x and y:
                try:
                    if display == "bar_chart":
                        fig = px.bar(df, x=x, y=y, color=color)
                    elif display == "line_chart":
                        fig = px.line(df, x=x, y=y, color=color)
                    else:
                        fig = px.pie(df, names=x, values=y)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass  # Fall through to table display below

            st.dataframe(df, use_container_width=True, hide_index=True)

        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.session_state.messages.append(msg_data)
