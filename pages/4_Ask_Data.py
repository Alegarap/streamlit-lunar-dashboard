"""Ask Data — AI-powered natural language data assistant.

Two-pass agent: (1) LLM decides what to query, (2) data is fetched,
(3) LLM analyzes the results and writes a human response.
"""

import json
import os
import sys
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

# Resolve API key
OPENROUTER_KEY = ""
try:
    OPENROUTER_KEY = st.secrets.get("OPENROUTER_KEY_STREAMLIT", "")
except FileNotFoundError:
    pass
if not OPENROUTER_KEY:
    OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY_STREAMLIT", "")
if not OPENROUTER_KEY:
    st.error("Missing OPENROUTER_KEY_STREAMLIT.")
    st.stop()

MODEL = "anthropic/claude-sonnet-4-6"

# Dynamic date context
today = datetime.now().date()
yesterday = today - timedelta(days=1)
week_start = today - timedelta(days=today.weekday())
month_start = today.replace(day=1)

# --------------------------------------------------------------------------
# Pass 1 prompt: decide what query to run (or none)
# --------------------------------------------------------------------------

QUERY_PROMPT = f"""You are a data query planner for Lunar Ventures' BI dashboard. Given a user question, decide what database query to run.

Today: {today.isoformat()} ({today.strftime('%A')}). Week started: {week_start.isoformat()}. Month started: {month_start.isoformat()}.

## Available queries

### RPCs (for time-based aggregation)
The p_days param: p_days=0 → today only, p_days=2 → last 3 days, p_days=6 → last 7 days.
- get_ingestion_stats(p_days) → day, source, type, item_count
- get_hot_clusters(min_score, lim) → label, summary, item_count, source_diversity, hotness_score. NOTE: hotness_score is 0.0 to 1.0 (not 0-100). Use min_score=0.3 for hot clusters, 0.5 for very hot.
- get_cost_stats(p_days) → day, workflow_key, model, request_count, total_input_tokens, total_output_tokens, total_cost

### REST (for keyword search, filtering, listing)
- items: select, order, limit, filters (source=eq.arxiv, type=eq.theme, title=ilike.*keyword*, etc.)
- clusters: select, order, limit, filters (hotness_score=gt.0.3, label=ilike.*keyword*, etc.)

## p_days reference
| User says | p_days |
|-----------|--------|
| today | 0 |
| last 3 days | 2 |
| this week (Mon-today) | {(today - week_start).days} |
| last 7 days | 6 |
| this month | {(today - month_start).days} |

## Response
Return JSON only:
- Need data: {{"query": {{"type": "rpc", "function": "...", "params": {{...}}}}}} or {{"query": {{"type": "rest", "table": "...", "params": {{...}}}}}}
- No data needed (greeting, thanks, etc.): {{"no_query": true, "reply": "Your response"}}
"""

# --------------------------------------------------------------------------
# Pass 2 prompt: analyze data and respond naturally
# --------------------------------------------------------------------------

ANALYSIS_PROMPT = f"""You are a helpful data analyst for Lunar Ventures, a VC fund. You just queried the database and got results. Now write a clear, natural language response.

Today: {today.isoformat()}.

## Rules
- Write like you're talking to a colleague. Be concise but insightful.
- Lead with the key number or finding in **bold**.
- Add brief context or breakdown where useful.
- Use markdown: **bold** for key numbers, bullet points for lists.
- Do NOT say "based on the data" or "the query returned" — just state the facts.
- If the user asked for a chart or table, set the display field. Otherwise, text only.

## Response format
Return JSON:
- Text response: {{"message": "Your natural language answer with **bold numbers**"}}
- With chart (only if user said "chart"/"graph"/"show"): {{"message": "Caption", "display": "bar_chart", "chart_config": {{"x": "column_name_from_data", "y": "column_name_from_data", "color": "column_name_from_data_or_null"}}}}
  chart_config x/y/color MUST be actual column names from the query results. display can be "bar_chart", "line_chart", or "pie_chart".
- With table (only if user said "table"/"list"/"show"/"breakdown"): {{"message": "Caption", "display": "table"}}
"""

# --------------------------------------------------------------------------
# LLM call helper
# --------------------------------------------------------------------------

def _llm_call(messages, max_tokens=1024):
    """Call OpenRouter and return the response content string."""
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def _parse_json(text):
    """Extract JSON from LLM response (handles markdown code blocks)."""
    if "```" in text:
        parts = text.split("```")
        code = parts[1] if len(parts) > 1 else text
        if code.startswith("json"):
            code = code[4:]
        text = code
    return json.loads(text.strip())


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

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

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown(
        '<p style="color: #94a3b8; text-align: center; margin: 3rem 0;">'
        "Ask me anything about your sourcing data. I'll answer in plain language "
        "with key numbers and insights. Say \"show chart\" or \"show table\" "
        "when you want visuals."
        "</p>",
        unsafe_allow_html=True,
    )

# Render chat history
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

# --------------------------------------------------------------------------
# Handle new input
# --------------------------------------------------------------------------

prompt = st.chat_input("Ask a question about your data...") or st.session_state.pop("ask_input", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # --- Pass 1: decide what query to run ---
        with st.spinner("Thinking..."):
            # Build conversation context (last 6 messages)
            history = []
            for msg in st.session_state.messages[-6:]:
                if msg["role"] == "user":
                    history.append({"role": "user", "content": msg["content"]})
                elif msg.get("content") and msg["role"] == "assistant":
                    history.append({"role": "assistant", "content": msg["content"]})

            try:
                raw = _llm_call([
                    {"role": "system", "content": QUERY_PROMPT},
                    *history,
                ], max_tokens=512)
                query_spec = _parse_json(raw)
            except Exception as e:
                st.markdown(f"Sorry, I had trouble understanding that. Error: {e}")
                st.session_state.messages.append({
                    "role": "assistant", "content": f"Error: {e}",
                })
                st.stop()

        # No query needed — direct reply
        if query_spec.get("no_query"):
            reply = query_spec.get("reply", "How can I help?")
            st.markdown(reply)
            st.session_state.messages.append({
                "role": "assistant", "content": reply,
            })
            st.stop()

        # --- Execute the query ---
        with st.spinner("Querying data..."):
            query = query_spec.get("query", {})
            try:
                if query.get("type") == "rpc":
                    data = sb.rpc_fresh(query["function"], query.get("params", {}))
                else:
                    data = sb.query_fresh(query["table"], query.get("params", {}))
            except Exception as e:
                st.markdown(f"Query failed: {e}")
                st.session_state.messages.append({
                    "role": "assistant", "content": f"Query error: {e}",
                })
                st.stop()

        if not data:
            st.markdown("No results found for that query.")
            st.session_state.messages.append({
                "role": "assistant", "content": "No results found.",
            })
            st.stop()

        df = pd.DataFrame(data)

        # --- Pass 2: analyze the data and write response ---
        with st.spinner("Analyzing..."):
            # Summarize data for the LLM (limit to avoid token overflow)
            if len(df) > 50:
                data_summary = json.dumps(df.head(50).to_dict(orient="records"), default=str)
                data_note = f"Showing first 50 of {len(df)} rows."
            else:
                data_summary = json.dumps(df.to_dict(orient="records"), default=str)
                data_note = f"{len(df)} rows total."

            try:
                raw2 = _llm_call([
                    {"role": "system", "content": ANALYSIS_PROMPT},
                    {"role": "user", "content": (
                        f"User's question: {prompt}\n\n"
                        f"Query results ({data_note}):\n{data_summary}\n\n"
                        f"Columns: {list(df.columns)}\n"
                        f"Write your response."
                    )},
                ], max_tokens=1500)
                response = _parse_json(raw2)
            except json.JSONDecodeError:
                # LLM returned plain text instead of JSON — use it directly
                response = {"message": raw2}
            except Exception as e:
                response = {"message": f"I got the data but couldn't analyze it: {e}"}

        # --- Render the response ---
        message = response.get("message", "")
        display = response.get("display")
        chart_config = response.get("chart_config", {})

        if message:
            st.markdown(message)

        msg_data = {"role": "assistant", "content": message}

        if display in ("bar_chart", "line_chart", "pie_chart"):
            x = chart_config.get("x", df.columns[0] if len(df.columns) > 0 else None)
            y = chart_config.get("y", df.columns[1] if len(df.columns) > 1 else None)
            color = chart_config.get("color")
            if x and x not in df.columns:
                x = df.columns[0]
            if y and y not in df.columns:
                y = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            if color and color not in df.columns:
                color = None
            if x and y:
                try:
                    ct = {"bar_chart": "bar", "line_chart": "line", "pie_chart": "pie"}.get(display, "bar")
                    if ct == "bar":
                        fig = px.bar(df, x=x, y=y, color=color)
                    elif ct == "line":
                        fig = px.line(df, x=x, y=y, color=color)
                    else:
                        fig = px.pie(df, names=x, values=y)
                    fig.update_layout(margin=dict(t=10))
                    st.plotly_chart(fig, use_container_width=True)
                    msg_data["chart_fig_data"] = {
                        "type": ct, "data": df.to_dict(orient="records"),
                        "x": x, "y": y, "color": color,
                    }
                except Exception:
                    pass

        elif display == "table":
            st.dataframe(df, use_container_width=True, hide_index=True)
            msg_data["dataframe"] = df.to_dict(orient="records")

        st.session_state.messages.append(msg_data)
