"""Ask Data — AI-powered natural language querying.

Uses Claude via OpenRouter to translate natural language questions into
Supabase REST API queries, then renders results as tables/charts.
Supports conversational follow-ups and natural language responses.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
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
    st.caption("Powered by Claude via OpenRouter")
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

# Dynamic date context
today = datetime.now().date()
yesterday = today - timedelta(days=1)
week_start = today - timedelta(days=today.weekday())
month_start = today.replace(day=1)

SYSTEM_PROMPT = f"""You are a helpful data analyst assistant for Lunar Ventures, a VC fund. You have access to their ambient sourcing database and can query it to answer questions.

## Important Context
- **Today's date**: {today.isoformat()} ({today.strftime('%A')})
- **Yesterday**: {yesterday.isoformat()}
- **This week started**: {week_start.isoformat()} (Monday)
- **This month started**: {month_start.isoformat()}
- All timestamps are in UTC.

## Your Behavior — READ THIS CAREFULLY
You are a smart analyst, not a chart-generating machine. Think about WHAT the user actually wants:

1. **"Show me X" / "Graph of X" / "Chart X"** → They want a visualization. Use display: "bar_chart"/"line_chart"/"pie_chart".
2. **"How many X?" / "What's the total?" / "Count of X"** → They want a number or short answer. Write the answer in your message with the actual number. Use display: "table" only if the breakdown is useful.
3. **"What's hot?" / "Any interesting trends?" / "Summarize X"** → They want your analysis and interpretation as text. Query the data, then write an insightful summary in your message. Include the data as a table for reference, not a chart.
4. **"Why is X?" / "Compare X vs Y" / "What should we do about X?"** → They want your reasoning. Write a thoughtful text response. Query if needed, but the value is in your analysis, not the raw data.
5. **Casual conversation / "thanks" / "ok"** → Just respond naturally, no query needed.

KEY PRINCIPLE: Your "message" field is the primary response. Charts/tables are supporting evidence. Always write a meaningful message that directly answers the question — don't just say "Here's the data:" and dump a chart. Include actual numbers, comparisons, and insights in your message text.

## Database Schema

### items — All investment themes and deals
Key columns: id, type ('theme'/'deal'), title, summary, source ('linear'/'hackernews'/'arxiv'/'conference'/'tigerclaw'), source_url, linear_identifier (e.g. 'THE-2398'), stage, signal_strength, cluster_id, created_at, source_date

### clusters — Groups of similar items
Key columns: id, label, summary, item_count, source_diversity, hotness_score (0-1), first_seen_at, last_surfaced_at

### eval_samples — Evaluation feedback
Key columns: batch_id (e.g. '2026-W11'), source, reviewer, sample_pool ('hot'/'random'), classification ('signal'/'weak_signal'/'shareable'/'noise'), comment, created_at

### cost_log — API cost tracking
Key columns: workflow_key, model, input_tokens, output_tokens, total_cost (decimal), created_at

## Available RPCs — ALWAYS USE THESE for time-based questions
The RPCs use `WHERE created_at >= (CURRENT_DATE - p_days)`. This means:
- p_days=0 → today only
- p_days=1 → yesterday + today (2 days)
- p_days=2 → 3 days of data
- p_days=6 → 7 days (this week if today is Sunday)

**RPCs:**
- `get_ingestion_stats(p_days)` → day, source, type, item_count — for ingestion/items questions
- `get_hot_clusters(min_score, lim)` → cluster rows sorted by hotness
- `get_cost_stats(p_days)` → day, workflow_key, model, request_count, total_input_tokens, total_output_tokens, total_cost — for cost questions

## PostgREST REST queries — only for non-time-based questions
Use REST queries ONLY when you need to search by keyword, filter by source, or list specific items. NEVER use REST for "today/this week/last N days" — use the RPCs above instead.
- Filtering: "column": "eq.value", "gt.5", "gte.2026-03-15T00:00:00", "ilike.*keyword*", "in.(a,b,c)"
- Select/order/limit: "select": "col1,col2", "order": "col.desc", "limit": "20"
- Not null: "column": "not.is.null"

## Response Format
You MUST respond with a JSON object. The JSON can include a natural language message AND optionally a query:

For questions that need data:
```json
{{
  "message": "Your conversational response explaining what you're looking up and what you found",
  "query": {{
    "type": "rest" or "rpc",
    "table": "items",
    "function": "get_ingestion_stats",
    "params": {{}},
  }},
  "display": "table" | "bar_chart" | "line_chart" | "pie_chart" | "metric",
  "chart_config": {{"x": "col", "y": "col", "color": "col"}}
}}
```

For conversational responses (no data needed):
```json
{{
  "message": "Your response text here"
}}
```

## Critical Rules for Date Queries — READ CAREFULLY
The p_days parameter means "go back N days from today". p_days=0 means today only.

| User says | Correct p_days | Dates returned |
|-----------|---------------|----------------|
| "today" | p_days=0 | {today.isoformat()} only |
| "yesterday" | DO NOT USE RPC. Use REST with created_at gte/lt | {yesterday.isoformat()} only |
| "last 3 days" | p_days=2 | {(today - timedelta(days=2)).isoformat()} to {today.isoformat()} (3 days) |
| "last 7 days" / "this week" | p_days=6 | 7 days of data |
| "this week (Mon-today)" | p_days={(today - week_start).days} | {week_start.isoformat()} to {today.isoformat()} |
| "this month" | p_days={(today - month_start).days} | {month_start.isoformat()} to {today.isoformat()} |

NEVER guess p_days. Calculate it from the table above. ALWAYS use RPCs for time-based aggregation questions — never REST queries with date filters.

## Examples — notice how the response style matches the question type

User: "Show me a chart of ingestion for the last 3 days" (WANTS A CHART)
```json
{{"message": "Here's the ingestion breakdown for the last 3 days by source:", "query": {{"type": "rpc", "function": "get_ingestion_stats", "params": {{"p_days": 2}}}}, "display": "bar_chart", "chart_config": {{"x": "day", "y": "item_count", "color": "source"}}}}
```

User: "How many items came in today?" (WANTS A NUMBER)
```json
{{"message": "Today ({today.isoformat()}) we've ingested **118 items** so far — 38 themes and 80 deals. The main sources are arxiv (103 items), hackernews (9), and conferences (6).", "query": {{"type": "rpc", "function": "get_ingestion_stats", "params": {{"p_days": 0}}}}, "display": "table"}}
```

User: "What's hot right now?" (WANTS ANALYSIS)
```json
{{"message": "The hottest cluster right now is **AI Agent Security and Governance** with a score of 0.76 — it has 61 items from multiple sources, showing strong convergence. Other notable hot themes include **Photonic AI Inference Accelerators** (0.64) and **LLM Tooling & Observability** (0.62). The pattern suggests strong interest in AI infrastructure security and novel hardware acceleration.", "query": {{"type": "rpc", "function": "get_hot_clusters", "params": {{"min_score": 0.5, "lim": 10}}}}, "display": "table"}}
```

User: "How much did we spend this week?" (WANTS A NUMBER + CONTEXT)
```json
{{"message": "This week's total spend is **$18.78** across all workflows. The biggest cost driver is Academic Sourcing at $6.74, followed by factory (default key) at $0.50. Compared to last week this is normal operational cost.", "query": {{"type": "rpc", "function": "get_cost_stats", "params": {{"p_days": {(today - week_start).days}}}}}, "display": "table"}}
```

User: "Thanks!"
```json
{{"message": "You're welcome! Let me know if you have any other questions about the data."}}
```
"""

# --- Quick queries ---
st.markdown("**Quick queries:**")
quick_cols = st.columns(4)
quick_queries = [
    "What's hot right now?",
    "How many items came in today?",
    "How much did we spend this week?",
    "Show ingestion chart for last 7 days",
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
        "Ask me anything about your sourcing data. I can show charts, "
        "give you numbers, or analyze trends.<br>"
        '"What\'s hot right now?" · '
        '"How much did we spend this week?" · '
        '"Show a chart of ingestion by source for the last 7 days"'
        "</p>",
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
        if msg.get("chart_fig_data") is not None:
            # Re-render chart from stored spec
            try:
                spec = msg["chart_fig_data"]
                cdf = pd.DataFrame(spec["data"])
                if spec["type"] == "bar":
                    fig = px.bar(cdf, x=spec["x"], y=spec["y"], color=spec.get("color"))
                elif spec["type"] == "line":
                    fig = px.line(cdf, x=spec["x"], y=spec["y"], color=spec.get("color"))
                elif spec["type"] == "pie":
                    fig = px.pie(cdf, names=spec["x"], values=spec["y"])
                else:
                    fig = None
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

prompt = st.chat_input("Ask a question about your data...") or st.session_state.pop("ask_input", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Build conversation history (last 8 messages for context)
            history = []
            for msg in st.session_state.messages[-8:]:
                if msg["role"] == "user":
                    history.append({"role": "user", "content": msg["content"]})
                elif msg.get("content") and msg["role"] == "assistant":
                    # Include data summary in history for follow-ups
                    assistant_text = msg["content"]
                    if msg.get("dataframe"):
                        df_summary = pd.DataFrame(msg["dataframe"])
                        assistant_text += f"\n[Data: {len(df_summary)} rows, columns: {list(df_summary.columns)}]"
                    history.append({"role": "assistant", "content": assistant_text})

            body = json.dumps({
                "model": "anthropic/claude-sonnet-4-6",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *history,
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                },
            )
            response_spec = None
            raw_content = ""
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    ai_response = json.loads(resp.read())
                raw_content = ai_response["choices"][0]["message"]["content"]

                # Parse JSON from response (handle markdown code blocks)
                json_str = raw_content
                if "```" in json_str:
                    parts = json_str.split("```")
                    code_block = parts[1] if len(parts) > 1 else json_str
                    if code_block.startswith("json"):
                        code_block = code_block[4:]
                    json_str = code_block
                response_spec = json.loads(json_str.strip())
            except json.JSONDecodeError:
                # AI returned non-JSON — show as conversational text
                st.markdown(raw_content)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": raw_content,
                })
            except Exception as e:
                st.error(f"AI query failed: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {e}",
                })

        if response_spec is None:
            st.stop()

        # Show the conversational message
        message = response_spec.get("message", "")
        if message:
            st.markdown(message)

        # Execute query if present
        query = response_spec.get("query")
        if not query:
            # Pure conversational response, no data
            st.session_state.messages.append({
                "role": "assistant",
                "content": message,
            })
            st.stop()

        data = None
        try:
            # Use uncached queries so Ask Data always shows fresh data
            if query.get("type") == "rpc":
                data = sb.rpc_fresh(
                    query["function"],
                    query.get("params", {}),
                )
            else:
                data = sb.query_fresh(
                    query["table"],
                    query.get("params", {}),
                )
        except Exception as e:
            st.error(f"Query failed: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"{message}\n\nQuery error: {e}",
            })
            st.stop()

        if not data:
            st.info("No results found for this query.")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"{message}\n\nNo results found.",
            })
            st.stop()

        df = pd.DataFrame(data)
        display = response_spec.get("display", "table")
        chart_config = response_spec.get("chart_config", {})
        msg_data = {
            "role": "assistant",
            "content": message,
            "dataframe": df.to_dict(orient="records"),
        }

        # Render charts
        if display in ("bar_chart", "line_chart", "pie_chart"):
            x = chart_config.get("x", df.columns[0] if len(df.columns) > 0 else None)
            y = chart_config.get("y", df.columns[1] if len(df.columns) > 1 else df.columns[0] if len(df.columns) > 0 else None)
            color = chart_config.get("color")

            # Validate columns
            if x and x not in df.columns:
                x = df.columns[0] if len(df.columns) > 0 else None
            if y and y not in df.columns:
                y = df.columns[1] if len(df.columns) > 1 else df.columns[0] if len(df.columns) > 0 else None
            if color and color not in df.columns:
                color = None

            if x and y:
                try:
                    chart_type_map = {"bar_chart": "bar", "line_chart": "line", "pie_chart": "pie"}
                    ct = chart_type_map.get(display, "bar")
                    if ct == "bar":
                        fig = px.bar(df, x=x, y=y, color=color)
                    elif ct == "line":
                        fig = px.line(df, x=x, y=y, color=color)
                    else:
                        fig = px.pie(df, names=x, values=y)
                    fig.update_layout(margin=dict(t=10))
                    st.plotly_chart(fig, use_container_width=True)
                    # Store chart spec for re-rendering in history
                    msg_data["chart_fig_data"] = {
                        "type": ct,
                        "data": df.to_dict(orient="records"),
                        "x": x, "y": y, "color": color,
                    }
                except Exception:
                    pass

        if display == "metric" and len(df) == 1 and len(df.columns) <= 4:
            cols = st.columns(len(df.columns))
            for col, c in zip(cols, df.columns):
                col.metric(c, df[c].iloc[0])
        else:
            # Always show data table
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.session_state.messages.append(msg_data)
