"""Ask AI — AI-powered natural language data assistant.

Two-pass agent: (1) LLM plans a Supabase query from natural language,
(2) data is fetched, (3) LLM analyzes results and responds.
"""

import json
import os
import re
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
from lib.charts import style_fig

style.apply()
st.title("Ask AI")

with st.sidebar:
    st.caption("Powered by Claude Opus via OpenRouter")
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

MODEL = "anthropic/claude-opus-4-6"

# Dynamic date context
today = datetime.now().date()
yesterday = today - timedelta(days=1)
week_start = today - timedelta(days=today.weekday())
month_start = today.replace(day=1)

# --------------------------------------------------------------------------
# Pass 1 prompt: NLQ → Supabase query
# --------------------------------------------------------------------------

QUERY_PROMPT = f"""You are a query planner that converts natural language questions into Supabase PostgREST API calls. You work for Lunar Ventures, a VC fund that tracks themes (technology trends) and deals (startup companies) from multiple sources.

## Date Context
- Today: {today.isoformat()} ({today.strftime('%A')})
- Yesterday: {yesterday.isoformat()}
- Week start (Monday): {week_start.isoformat()}
- Month start: {month_start.isoformat()}

## Database Schema

### Table: `items` (themes and deals from various sources)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | Primary key |
| type | text | "theme" or "deal" |
| title | text | Item title |
| description | text | Full description (markdown) |
| summary | text | AI-generated summary |
| source | text | One of: "linear", "hackernews", "arxiv", "conference", "tigerclaw" |
| source_url | text | Link to original source |
| stage | text | "raw" by default |
| priority | integer | 0 by default |
| source_labels | jsonb | Array of labels |
| cluster_id | uuid | FK to clusters table (null if unclustered) |
| created_at | timestamptz | When ingested |
| source_date | timestamptz | Original publication date |

### Table: `clusters` (groups of related items)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | Primary key |
| label | text | Human-readable cluster name |
| summary | text | AI-generated cluster summary |
| item_count | integer | Number of items in cluster |
| source_diversity | integer | Number of distinct sources |
| hotness_score | numeric | 0.0 to 1.0 (NOT 0-100) |
| first_seen_at | timestamptz | When cluster first appeared |
| last_surfaced_at | timestamptz | When last item was added |

### Table: `cost_log` (LLM API costs)
| Column | Type | Notes |
|--------|------|-------|
| workflow_key | text | Which pipeline/workflow |
| model | text | e.g. "anthropic/claude-sonnet-4.6" |
| input_tokens | integer | Input token count |
| output_tokens | integer | Output token count |
| total_cost | numeric | Cost in USD |
| created_at | timestamptz | When the call happened |

### Table: `eval_samples` (team evaluation feedback)
| Column | Type | Notes |
|--------|------|-------|
| batch_id | text | e.g. "2026-W11" |
| source | text | Same as items.source |
| classification | text | "signal", "weak_signal", "shareable", "noise", or null |
| sample_pool | text | "hot" or "random" |
| created_at | timestamptz | |

## RPC Functions (pre-built aggregation queries)

### `get_ingestion_stats(p_days integer)`
Returns daily item counts grouped by source and type.
- p_days=0 → today only, p_days=6 → last 7 days, p_days=29 → last 30 days
- Returns: day, source, type, item_count

### `get_cost_stats(p_days integer)`
Returns daily cost aggregates grouped by workflow_key and model.
- Same p_days logic as above
- Returns: day, workflow_key, model, request_count, total_input_tokens, total_output_tokens, total_cost

### `get_hot_clusters(min_score numeric, lim integer)`
Returns top clusters above a hotness threshold.
- min_score: 0.0-1.0 (use 0.3 for "hot", 0.5 for "very hot", 0.0 for all)
- lim: max results (use 5-20)
- Returns: id, label, summary, item_count, source_diversity, hotness_score, first_seen_at, last_surfaced_at

## p_days Reference
| User says | p_days value |
|-----------|-------------|
| today | 0 |
| yesterday | 1 |
| last 3 days | 2 |
| this week (Mon-today) | {(today - week_start).days} |
| last 7 days | 6 |
| last 2 weeks | 13 |
| this month | {(today - month_start).days} |
| last 30 days | 29 |
| last 90 days | 89 |

## Query Types

### Type 1: RPC call (PREFERRED for time-based aggregation)
Use RPCs when the user asks about counts, totals, trends over time, or cost breakdowns.
```json
{{"query": {{"type": "rpc", "function": "get_ingestion_stats", "params": {{"p_days": 6}}}}}}
```

### Type 2: REST call (for search, filtering, listing individual items)
Use REST when the user wants to see specific items, search by keyword, or filter by column values.
```json
{{"query": {{"type": "rest", "table": "items", "params": {{"select": "title,source,type,created_at", "source": "eq.arxiv", "type": "eq.theme", "order": "created_at.desc", "limit": "20"}}}}}}
```

## PostgREST Filter Syntax (CRITICAL — follow exactly)
Filters are key-value pairs where the value starts with an operator:
- `"column": "eq.value"` → equals (exact match)
- `"column": "neq.value"` → not equals
- `"column": "gt.value"` → greater than
- `"column": "gte.value"` → greater than or equal
- `"column": "lt.value"` → less than
- `"column": "lte.value"` → less than or equal
- `"column": "like.*keyword*"` → SQL LIKE (% = wildcard, use * in PostgREST)
- `"column": "ilike.*keyword*"` → case-insensitive LIKE
- `"column": "in.(val1,val2,val3)"` → one of several values
- `"column": "is.null"` → is null
- `"column": "not.is.null"` → is not null

IMPORTANT: Every filter value MUST start with an operator. Never write `"source": "arxiv"`. Always write `"source": "eq.arxiv"`.

## Few-Shot Examples

User: "How many items today?"
```json
{{"query": {{"type": "rpc", "function": "get_ingestion_stats", "params": {{"p_days": 0}}}}}}
```

User: "Show me arxiv themes from this week"
```json
{{"query": {{"type": "rest", "table": "items", "params": {{"select": "title,source,type,source_date,source_url", "source": "eq.arxiv", "type": "eq.theme", "created_at": "gte.{week_start.isoformat()}", "order": "created_at.desc", "limit": "50"}}}}}}
```

User: "What are the hottest clusters?"
```json
{{"query": {{"type": "rpc", "function": "get_hot_clusters", "params": {{"min_score": 0.3, "lim": 10}}}}}}
```

User: "How much did we spend this week?"
```json
{{"query": {{"type": "rpc", "function": "get_cost_stats", "params": {{"p_days": {(today - week_start).days}}}}}}}
```

User: "Show deals from hackernews"
```json
{{"query": {{"type": "rest", "table": "items", "params": {{"select": "title,source,type,source_date,source_url", "source": "eq.hackernews", "type": "eq.deal", "order": "created_at.desc", "limit": "30"}}}}}}
```

User: "Search for items about quantum computing"
```json
{{"query": {{"type": "rest", "table": "items", "params": {{"select": "title,source,type,source_date", "title": "ilike.*quantum*", "order": "created_at.desc", "limit": "30"}}}}}}
```

User: "Daily ingestion for the last 2 weeks"
```json
{{"query": {{"type": "rpc", "function": "get_ingestion_stats", "params": {{"p_days": 13}}}}}}
```

User: "Cost by model this month"
```json
{{"query": {{"type": "rpc", "function": "get_cost_stats", "params": {{"p_days": {(today - month_start).days}}}}}}}
```

User: "I'm seeing multiple sources, I just want arxiv"
(Follow-up: user wants to refine the previous query to only show arxiv)
```json
{{"query": {{"type": "rpc", "function": "get_ingestion_stats", "params": {{"p_days": 0}}}}}}
```
Note: RPCs don't support source filtering — fetch all data and the analysis pass will filter.

User: "Thanks!" / "Hello" / "What can you do?"
```json
{{"no_query": true, "reply": "I can help you explore your sourcing data — ingestion volumes, costs, hot clusters, and specific items. Try asking about today's items, this week's costs, or what topics are trending."}}
```

## Rules
1. Return ONLY valid JSON. No markdown, no explanation, no code blocks.
2. Prefer RPC calls over REST for aggregated data (counts, sums, trends).
3. Every REST filter MUST use operator syntax: `"column": "op.value"`.
4. Use `ilike.*keyword*` for search — never bare keyword values.
5. Always include `select`, `order`, and `limit` in REST queries.
6. For follow-up questions, look at conversation history to understand context.
7. If the user's intent is ambiguous, make your best guess — do NOT return an error.
"""

# --------------------------------------------------------------------------
# Pass 2 prompt: analyze data and respond
# --------------------------------------------------------------------------

ANALYSIS_PROMPT = f"""You are a data analyst for Lunar Ventures, a VC fund. You queried the database and got results. Write a clear, helpful response.

Today: {today.isoformat()}.

## Data Sources
- **Items**: Themes (technology trends) and Deals (startups) from: Linear (internal), Hacker News, arXiv, Conferences, Tigerclaw
- **Clusters**: Groups of related items with hotness scores (0.0-1.0)
- **Cost log**: LLM API costs by workflow and model

## Response Rules
1. Lead with the key number or finding in **bold**.
2. Be concise — write like you're talking to a colleague.
3. Use markdown: **bold** for numbers, bullet points for lists.
4. Do NOT say "based on the data" or "the query returned" — just state facts.
5. If the user asked to filter by source and the data contains multiple sources, filter the data in your response and only mention the relevant source.
6. When showing breakdowns, sort by the most interesting dimension.
7. For cost data, always show dollar amounts.

## Display Options
- **Text only** (default): just write the answer.
- **With table**: if user said "table", "list", "show", "breakdown", or the data has many rows worth browsing → add `"display": "table"`.
- **With chart**: if user said "chart", "graph", "plot", "visualize" → add `"display": "bar_chart"` (or "line_chart", "pie_chart") and `"chart_config"` with column names from the data.

## Response Format (JSON only, no markdown blocks)
Text only:
{{"message": "Your answer with **bold numbers**"}}

With table:
{{"message": "Brief caption", "display": "table"}}

With chart:
{{"message": "Brief caption", "display": "bar_chart", "chart_config": {{"x": "column_name", "y": "column_name", "color": "optional_column_or_null"}}}}

chart_config x/y/color MUST be actual column names from the query results.

Return ONLY valid JSON. No markdown code blocks, no explanation outside JSON.
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def _parse_json(text):
    """Extract JSON from LLM response (handles markdown code blocks)."""
    text = text.strip()
    # Strip markdown code fences
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    # Try parsing directly
    return json.loads(text)


def _build_data_context(df, query):
    """Build a pre-aggregated summary so the LLM sees accurate totals."""
    fn = query.get("function", "")
    lines = [f"Query returned {len(df)} rows. Columns: {list(df.columns)}"]

    if fn == "get_cost_stats" and "total_cost" in df.columns:
        df["total_cost"] = pd.to_numeric(df["total_cost"], errors="coerce").fillna(0)
        total = df["total_cost"].sum()
        lines.append(f"\n**PRE-COMPUTED TOTALS (use these, do NOT re-sum):**")
        lines.append(f"- Grand total cost: ${total:.4f}")
        lines.append(f"- Total requests: {int(df['request_count'].sum()) if 'request_count' in df.columns else len(df)}")
        if "workflow_key" in df.columns:
            by_wf = df.groupby("workflow_key")["total_cost"].sum().sort_values(ascending=False)
            lines.append(f"\nCost by workflow:")
            for wf, cost in by_wf.items():
                lines.append(f"  - {wf}: ${cost:.4f}")
        if "model" in df.columns:
            by_model = df.groupby("model")["total_cost"].sum().sort_values(ascending=False)
            lines.append(f"\nCost by model:")
            for m, cost in by_model.items():
                lines.append(f"  - {m}: ${cost:.4f}")
        if "day" in df.columns:
            by_day = df.groupby("day")["total_cost"].sum().sort_values(ascending=False)
            lines.append(f"\nCost by day:")
            for d, cost in by_day.items():
                lines.append(f"  - {d}: ${cost:.4f}")

    elif fn == "get_ingestion_stats" and "item_count" in df.columns:
        df["item_count"] = pd.to_numeric(df["item_count"], errors="coerce").fillna(0)
        total = int(df["item_count"].sum())
        lines.append(f"\n**PRE-COMPUTED TOTALS (use these, do NOT re-sum):**")
        lines.append(f"- Total items: {total}")
        if "source" in df.columns:
            by_src = df.groupby("source")["item_count"].sum().sort_values(ascending=False)
            lines.append(f"\nBy source:")
            for s, c in by_src.items():
                lines.append(f"  - {s}: {int(c)}")
        if "type" in df.columns:
            by_type = df.groupby("type")["item_count"].sum().sort_values(ascending=False)
            lines.append(f"\nBy type:")
            for t, c in by_type.items():
                lines.append(f"  - {t}: {int(c)}")
        if "day" in df.columns:
            by_day = df.groupby("day")["item_count"].sum().sort_values(ascending=False)
            lines.append(f"\nBy day (top 10):")
            for d, c in list(by_day.items())[:10]:
                lines.append(f"  - {d}: {int(c)}")

    elif fn == "get_hot_clusters":
        lines.append(f"\nTop clusters:")
        for _, row in df.iterrows():
            r = row.to_dict()
            lines.append(
                f"  - {r.get('label', 'Unlabeled')} (score: {r.get('hotness_score', 0)}, "
                f"{r.get('item_count', 0)} items, {r.get('source_diversity', 0)} sources)"
                f"{': ' + r['summary'] if r.get('summary') else ''}"
            )

    else:
        # Generic: send rows capped at 50
        if len(df) > 50:
            lines.append(f"\nFirst 50 rows (of {len(df)}):")
            lines.append(json.dumps(df.head(50).to_dict(orient="records"), default=str))
        else:
            lines.append(f"\nAll {len(df)} rows:")
            lines.append(json.dumps(df.to_dict(orient="records"), default=str))

    return "\n".join(lines)


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
        "Ask me anything about your sourcing data — ingestion volumes, costs, "
        "hot clusters, or specific items. I'll answer in plain language "
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
                    style_fig(fig)
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
        # --- Build conversation history ---
        history = []
        for msg in st.session_state.messages[-10:]:
            if msg["role"] == "user":
                history.append({"role": "user", "content": msg["content"]})
            elif msg.get("content") and msg["role"] == "assistant":
                history.append({"role": "assistant", "content": msg["content"]})

        # --- Pass 1: plan the query ---
        with st.spinner("Thinking..."):
            try:
                raw = _llm_call([
                    {"role": "system", "content": QUERY_PROMPT},
                    *history,
                ], max_tokens=512)
                query_spec = _parse_json(raw)
            except Exception as e:
                st.markdown(f"Sorry, I had trouble understanding that. Please try rephrasing.")
                st.session_state.messages.append({
                    "role": "assistant", "content": f"Error planning query: {e}",
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
        query = query_spec.get("query", {})
        data = None
        error_msg = None

        with st.spinner("Querying data..."):
            try:
                if query.get("type") == "rpc":
                    data = sb.rpc_fresh(query["function"], query.get("params", {}))
                else:
                    data = sb.query_fresh(query["table"], query.get("params", {}))
            except Exception as e:
                error_msg = str(e)

        # --- Retry on failure: tell LLM what went wrong ---
        if error_msg:
            with st.spinner("Query failed, retrying..."):
                try:
                    retry_msg = (
                        f"The query you planned failed with error: {error_msg}\n"
                        f"The failed query was: {json.dumps(query)}\n"
                        f"Please fix the query. Common issues:\n"
                        f"- Missing operator prefix (use 'eq.value' not 'value')\n"
                        f"- Wrong column name\n"
                        f"- Invalid filter syntax\n"
                        f"Return corrected JSON."
                    )
                    history.append({"role": "assistant", "content": f"Query error: {error_msg}"})
                    history.append({"role": "user", "content": retry_msg})
                    raw_retry = _llm_call([
                        {"role": "system", "content": QUERY_PROMPT},
                        *history[-6:],
                    ], max_tokens=512)
                    query_spec = _parse_json(raw_retry)
                    query = query_spec.get("query", {})
                    if query.get("type") == "rpc":
                        data = sb.rpc_fresh(query["function"], query.get("params", {}))
                    else:
                        data = sb.query_fresh(query["table"], query.get("params", {}))
                    error_msg = None
                except Exception as e2:
                    st.markdown(f"Sorry, I couldn't get that data. Error: {e2}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Query failed after retry: {e2}",
                    })
                    st.stop()

        if not data:
            st.markdown("No results found for that query. Try broadening your search.")
            st.session_state.messages.append({
                "role": "assistant", "content": "No results found.",
            })
            st.stop()

        df = pd.DataFrame(data)

        # --- Pass 2: analyze data and respond ---
        with st.spinner("Analyzing..."):
            data_context = _build_data_context(df, query)

            # Include conversation history in analysis for follow-up awareness
            analysis_history = []
            for msg in st.session_state.messages[-6:]:
                if msg["role"] == "user":
                    analysis_history.append({"role": "user", "content": msg["content"]})
                elif msg.get("content") and msg["role"] == "assistant" and "Error" not in msg["content"]:
                    analysis_history.append({"role": "assistant", "content": msg["content"]})

            try:
                raw2 = _llm_call([
                    {"role": "system", "content": ANALYSIS_PROMPT},
                    *analysis_history[:-1],  # prior conversation
                    {"role": "user", "content": (
                        f"User's question: {prompt}\n\n"
                        f"Query executed: {json.dumps(query)}\n\n"
                        f"{data_context}\n\n"
                        f"Write your response. Use the TOTALS provided — do NOT re-sum from rows."
                    )},
                ], max_tokens=1500)
                response = _parse_json(raw2)
            except json.JSONDecodeError:
                # LLM returned plain text — use directly
                clean = raw2.strip()
                if clean.startswith("{") or clean.startswith("```"):
                    clean = "I found the data but had trouble formatting. Please try rephrasing."
                response = {"message": clean}
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
                    style_fig(fig)
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
