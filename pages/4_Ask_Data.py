"""Ask AI — Agentic assistant for the Lunar Ventures investment team.

Uses Claude's native tool use via OpenRouter to provide a multi-step agent
that can query Supabase, search/create Linear issues, display charts/tables,
and update user preferences — all personalized to the logged-in user.
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
from lib import linear_client as lc
from lib import style
from lib.charts import style_fig

style.apply()
st.title("Ask AI")

with st.sidebar:
    st.caption("Powered by Claude via OpenRouter")
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pop("pending_action", None)
        st.session_state.pop("visuals", None)
        st.rerun()

# ---------------------------------------------------------------------------
# API key & model
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Date context
# ---------------------------------------------------------------------------

today = datetime.now().date()
yesterday = today - timedelta(days=1)
week_start = today - timedelta(days=today.weekday())
month_start = today.replace(day=1)

# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------

profile = st.session_state.get("user_profile", {})
user_name = profile.get("name", "team member")
user_role = profile.get("role", "")
user_domains = profile.get("domains", [])
user_linear_id = profile.get("linear_id", "")
user_notes = profile.get("notes", "")
user_email = ""
try:
    if st.user.is_logged_in:
        user_email = st.user.email or ""
except AttributeError:
    pass

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "query_supabase",
        "description": (
            "Query the Supabase database. Supports RPC calls (for aggregated stats) "
            "and REST queries (for searching/filtering individual rows).\n\n"
            "## RPC functions available:\n"
            "- `get_ingestion_stats(p_days)` — daily item counts by source/type. p_days=0 for today, 6 for last 7 days, 29 for last 30 days.\n"
            "- `get_cost_stats(p_days)` — daily cost by workflow/model. Same p_days logic.\n"
            "- `get_hot_clusters(min_score, lim)` — top clusters above hotness threshold (0.0-1.0).\n\n"
            "## REST tables available:\n"
            "- `items` — themes and deals. Columns: id, type ('theme'/'deal'), title, description, summary, "
            "source ('linear','hackernews','arxiv','conference','tigerclaw'), source_url, source_date, "
            "sector_labels (text array), cluster_id, created_at, stage, priority, linear_identifier.\n"
            "- `clusters` — item groups. Columns: id, label, summary, item_count, source_diversity, "
            "hotness_score (0.0-1.0), first_seen_at, last_surfaced_at.\n"
            "- `cost_log` — LLM costs. Columns: workflow_key, model, total_cost, input_tokens, output_tokens, created_at.\n"
            "- `eval_samples` — team evaluation feedback. Columns: batch_id, reviewer, classification, sample_pool, source.\n\n"
            "## REST filter syntax (PostgREST — CRITICAL):\n"
            "Every filter value MUST start with an operator:\n"
            "- `eq.value`, `neq.value`, `gt.value`, `gte.value`, `lt.value`, `lte.value`\n"
            "- `ilike.*keyword*` (case-insensitive search), `like.*keyword*`\n"
            "- `in.(val1,val2)`, `is.null`, `not.is.null`\n"
            "- `ov.{val1,val2}` (array overlap — use for sector_labels matching)\n"
            "Always include `select`, `order`, and `limit` in REST params."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["rpc", "rest"],
                    "description": "rpc for aggregation functions, rest for table queries",
                },
                "function_or_table": {
                    "type": "string",
                    "description": "RPC function name (e.g. 'get_ingestion_stats') or table name (e.g. 'items')",
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters. For RPC: function args. For REST: PostgREST filters.",
                },
            },
            "required": ["method", "function_or_table", "params"],
        },
    },
    {
        "name": "search_linear_issues",
        "description": (
            "Search Linear issues by text query. Optionally filter by team.\n"
            "Teams: THE (Theme & Thesis), DEAL (Dealflow), IN (Investment), GEN (General), ENG (Engineering).\n"
            "Returns: identifier, title, state, assignee, labels, url, description snippet."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text"},
                "team": {
                    "type": "string",
                    "enum": ["THE", "DEAL", "IN", "GEN", "ENG"],
                    "description": "Optional team filter",
                },
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_linear_issue",
        "description": (
            "Get full details of a specific Linear issue by identifier (e.g. THE-1234, DEAL-567).\n"
            "Returns: title, description, state, assignee, labels, comments, url."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Issue identifier like THE-1234"},
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "create_linear_issue",
        "description": (
            "Create a new Linear issue. IMPORTANT: Always describe what you're about to create "
            "and ask the user to confirm BEFORE calling this tool. Never create without confirmation.\n"
            "Teams: THE for themes/technology trends, DEAL for startup deals."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "team": {
                    "type": "string",
                    "enum": ["THE", "DEAL"],
                    "description": "Target team",
                },
                "title": {"type": "string", "description": "Issue title"},
                "description": {"type": "string", "description": "Issue description (markdown)"},
                "assignee_id": {
                    "type": "string",
                    "description": "Linear user UUID to assign (optional)",
                },
            },
            "required": ["team", "title", "description"],
        },
    },
    {
        "name": "show_table",
        "description": "Display data as an interactive table in the dashboard. Use when presenting lists or detailed breakdowns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of row objects to display",
                },
                "caption": {"type": "string", "description": "Brief table caption"},
            },
            "required": ["data"],
        },
    },
    {
        "name": "show_chart",
        "description": "Display a chart (bar, line, or pie) in the dashboard. Use for visual trends and comparisons.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {"type": "string", "enum": ["bar", "line", "pie"]},
                "data": {"type": "array", "items": {"type": "object"}, "description": "Chart data rows"},
                "x": {"type": "string", "description": "Column name for x-axis"},
                "y": {"type": "string", "description": "Column name for y-axis"},
                "color": {"type": "string", "description": "Optional column for color grouping"},
                "caption": {"type": "string", "description": "Brief chart caption"},
            },
            "required": ["chart_type", "data", "x", "y"],
        },
    },
    {
        "name": "update_user_preferences",
        "description": (
            "Update the current user's persistent preferences. Use when the user says "
            "'I'm interested in X', 'add X to my interests', 'remember that I care about Y', "
            "or 'remove X from my interests'. Changes persist across sessions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "add_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domain interests to add",
                },
                "remove_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domain interests to remove",
                },
                "notes": {
                    "type": "string",
                    "description": "Free-form notes to remember about this user (replaces existing notes)",
                },
            },
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

if user_domains == ["all"]:
    domains_csv = "all domains (do not filter results for this user)"
elif user_domains:
    domains_csv = ", ".join(user_domains[:15])
else:
    domains_csv = "none specified"
notes_section = f"\n- Personal notes: {user_notes}" if user_notes else ""

SYSTEM_PROMPT = f"""You are Lunar AI, the intelligent assistant for Lunar Ventures' investment team. You help team members explore sourcing data, discover relevant themes and deals, search Linear issues, and take actions like creating new issues.

## User Context
- Name: {user_name}
- Role: {user_role}
- Domain expertise: {domains_csv}
- Linear user ID: {user_linear_id or 'not available'}{notes_section}

## About Lunar Ventures
Lunar Ventures is a deep tech VC fund investing across 9 domains: AI/ML Infrastructure, Privacy & Cryptography, Developer Infrastructure, Autonomous Systems, Science & Bio Computation, Frontier Computing, Gaming & Realtime Infrastructure, Vertical AI Applications, and Emerging Deep Tech.

The ambient sourcing pipeline collects themes (technology trends) and deals (startups) from multiple sources:
- **Linear** — internal team submissions (Theme & Thesis and Dealflow teams)
- **Hacker News** — automated scraping of relevant tech stories
- **arXiv** — academic paper monitoring
- **Conferences** — tech conference talk/topic harvesting
- **Tigerclaw** — deal flow platform

Items are clustered by embedding similarity. Clusters have hotness scores (0.0-1.0) based on recency, velocity, source diversity, and size.

## Date Context
- Today: {today.isoformat()} ({today.strftime('%A')})
- Yesterday: {yesterday.isoformat()}
- Week start (Monday): {week_start.isoformat()}
- Month start: {month_start.isoformat()}

## Team Members
- Alejandro García — Engineering (all domains)
- Morris Clay — General Partner (software, edge AI, compute hardware)
- Cindy Wei — General Partner (life sciences, genomics, medical devices)
- Eyal Baroz — General Partner (robotics, autonomous systems, semiconductors)
- Mick Halsband — General Partner (climate, defense software, geospatial)
- Alberto Cresto — General Partner (new materials, computational chemistry)
- Florent — General Partner (AI infrastructure, inference, GPU orchestration)
- Etel Friedmann — General Partner (developer tooling, DevOps, LLM routing)

## Behavioral Rules
1. **Personalize**: When the user asks "what should I look at", "what's relevant for me", or similar, filter results by their domain expertise. Highlight items matching their interests.
2. **Be concise**: Lead with the key finding or number. Write like you're talking to a colleague.
3. **Use tools**: Query data before answering factual questions. Don't guess numbers.
4. **Multi-step**: You can call multiple tools to answer complex questions. E.g., query Supabase for items, then search Linear for related issues.
5. **Confirmation for writes**: Before calling create_linear_issue, always tell the user what you plan to create and ask them to confirm. Only call the tool after they say yes.
6. **Cost formatting**: Use "USD" not "$" (Streamlit renders $ as LaTeX).
7. **Tables and charts**: Use show_table for lists of items/issues. Use show_chart for trends over time. Don't use them for single values.
8. **p_days reference**: today=0, yesterday=1, last 7 days=6, this week={max(0, (today - week_start).days)}, this month={max(0, (today - month_start).days)}, last 30 days=29.
9. **Preferences**: When the user expresses interest in new topics or asks you to remember something, use update_user_preferences to persist it.
10. **Pre-aggregate cost/ingestion data**: When presenting cost or ingestion totals, sum the data yourself from the query results. State the totals explicitly.
"""

# ---------------------------------------------------------------------------
# LLM call with tool use
# ---------------------------------------------------------------------------


def _safe_markdown(text):
    """Escape $ signs to prevent Streamlit LaTeX rendering."""
    return text.replace("$", "\\$") if text else text


def _llm_call(messages, tools=None, max_tokens=4096):
    """Call OpenRouter with optional tool use. Returns the full response."""
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if tools:
        body["tools"] = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
            for t in tools
        ]
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------


def _build_data_context(df, query_info):
    """Build a pre-aggregated summary so the agent sees accurate totals."""
    fn = query_info.get("function_or_table", "")
    lines = [f"Query returned {len(df)} rows. Columns: {list(df.columns)}"]

    if fn == "get_cost_stats" and "total_cost" in df.columns:
        df["total_cost"] = pd.to_numeric(df["total_cost"], errors="coerce").fillna(0)
        total = df["total_cost"].sum()
        lines.append(f"\nPRE-COMPUTED TOTALS (use these, do NOT re-sum):")
        lines.append(f"- Grand total cost: USD {total:.4f}")
        lines.append(f"- Total requests: {int(df['request_count'].sum()) if 'request_count' in df.columns else len(df)}")
        if "workflow_key" in df.columns:
            by_wf = df.groupby("workflow_key")["total_cost"].sum().sort_values(ascending=False)
            lines.append(f"\nCost by workflow:")
            for wf, cost in by_wf.items():
                lines.append(f"  - {wf}: USD {cost:.4f}")
        if "model" in df.columns:
            by_model = df.groupby("model")["total_cost"].sum().sort_values(ascending=False)
            lines.append(f"\nCost by model:")
            for m, cost in by_model.items():
                lines.append(f"  - {m}: USD {cost:.4f}")

    elif fn == "get_ingestion_stats" and "item_count" in df.columns:
        df["item_count"] = pd.to_numeric(df["item_count"], errors="coerce").fillna(0)
        total = int(df["item_count"].sum())
        lines.append(f"\nPRE-COMPUTED TOTALS:")
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
        rows = df.head(50).to_dict(orient="records") if len(df) > 50 else df.to_dict(orient="records")
        lines.append(f"\nRows ({min(len(df), 50)} of {len(df)}):")
        lines.append(json.dumps(rows, default=str))

    return "\n".join(lines)


def _execute_tool(name, args):
    """Execute a tool call and return the result as a string."""
    try:
        if name == "query_supabase":
            method = args.get("method", "rest")
            target = args.get("function_or_table", "")
            params = args.get("params", {})

            if method == "rpc":
                data = sb.rpc_fresh(target, params)
            else:
                data = sb.query_fresh(target, params)

            if not data:
                return json.dumps({"result": "No data returned", "rows": 0})

            df = pd.DataFrame(data)
            context = _build_data_context(df, args)
            return context

        elif name == "search_linear_issues":
            results = lc.search_issues(
                query=args["query"],
                team=args.get("team"),
                limit=args.get("limit", 10),
            )
            return json.dumps(results, default=str)

        elif name == "get_linear_issue":
            result = lc.get_issue(args["identifier"])
            return json.dumps(result, default=str)

        elif name == "create_linear_issue":
            result = lc.create_issue(
                team=args["team"],
                title=args["title"],
                description=args["description"],
                assignee_id=args.get("assignee_id"),
            )
            return json.dumps(result, default=str)

        elif name == "show_table":
            data = args.get("data", [])
            caption = args.get("caption", "")
            # Store for rendering after the agent loop
            if "visuals" not in st.session_state:
                st.session_state["visuals"] = []
            st.session_state["visuals"].append({
                "type": "table",
                "data": data,
                "caption": caption,
            })
            return json.dumps({"displayed": True, "rows": len(data)})

        elif name == "show_chart":
            chart_spec = {
                "type": args["chart_type"],
                "data": args["data"],
                "x": args["x"],
                "y": args["y"],
                "color": args.get("color"),
                "caption": args.get("caption", ""),
            }
            if "visuals" not in st.session_state:
                st.session_state["visuals"] = []
            st.session_state["visuals"].append(chart_spec)
            return json.dumps({"displayed": True, "chart_type": args["chart_type"]})

        elif name == "update_user_preferences":
            if not user_email:
                return json.dumps({"error": "No user email available — cannot save preferences"})

            add = args.get("add_domains", [])
            remove = args.get("remove_domains", [])
            notes = args.get("notes")

            # Fetch current prefs
            current = sb.query_fresh("user_preferences", {
                "email": f"eq.{user_email.lower()}",
                "limit": "1",
            })

            existing_extra = []
            existing_notes = ""
            if current:
                existing_extra = current[0].get("extra_domains") or []
                existing_notes = current[0].get("notes", "")

            # Merge domains
            new_extra = list(set(existing_extra + add) - set(remove))
            new_notes = notes if notes is not None else existing_notes

            # Upsert via POST with Prefer: resolution=merge-duplicates
            _upsert_preferences(user_email.lower(), new_extra, new_notes)

            # Update session state
            if "user_profile" in st.session_state:
                base_domains = st.session_state["user_profile"].get("_base_domains",
                    st.session_state["user_profile"].get("domains", []))
                st.session_state["user_profile"]["domains"] = list(
                    set(base_domains + new_extra)
                )
                st.session_state["user_profile"]["notes"] = new_notes

            return json.dumps({
                "saved": True,
                "extra_domains": new_extra,
                "notes": new_notes,
            })

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


def _upsert_preferences(email, extra_domains, notes):
    """Upsert user preferences into Supabase."""
    url, _ = sb._get_credentials()
    endpoint = f"{url}/rest/v1/user_preferences"
    hdrs = sb._headers()
    hdrs["Prefer"] = "resolution=merge-duplicates,return=minimal"
    body = json.dumps({
        "email": email,
        "extra_domains": extra_domains,
        "notes": notes,
    }).encode()
    req = urllib.request.Request(endpoint, data=body, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=30):
        pass


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 8


def _run_agent(user_message, history):
    """Run the agentic loop: send message → tool calls → repeat until text response."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history (last 20 messages, compressed)
    for msg in history[-20:]:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant" and msg.get("content"):
            messages.append({"role": "assistant", "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    # Clear visuals for this turn
    st.session_state["visuals"] = []

    text_parts = []

    for iteration in range(MAX_ITERATIONS):
        response = _llm_call(messages, tools=TOOLS)

        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "stop")

        # Collect any text content
        content = message.get("content", "")
        if content:
            text_parts.append(content)

        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            # No more tool calls — agent is done
            break

        # Append the assistant message (with tool calls) to history
        messages.append(message)

        # Execute each tool call
        for tc in tool_calls:
            fn_name = tc.get("function", {}).get("name", "")
            fn_args_raw = tc.get("function", {}).get("arguments", "{}")
            try:
                fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
            except json.JSONDecodeError:
                fn_args = {}

            with st.spinner(f"Running {fn_name}..."):
                result = _execute_tool(fn_name, fn_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result,
            })

    return "\n\n".join(text_parts) if text_parts else "I wasn't able to generate a response. Please try again."


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

# Personalized quick queries
if user_domains:
    first_domain = user_domains[0] if user_domains else ""
    quick_queries = [
        "What's relevant for me this week?",
        "What's hot right now?",
        f"Search for {first_domain} items",
        "Show my Linear issues",
    ]
else:
    quick_queries = [
        "What's hot right now?",
        "How many items came in today?",
        "How much did we spend this week?",
        "Show ingestion chart for last 7 days",
    ]

st.markdown("**Quick queries:**")
quick_cols = st.columns(len(quick_queries))
for col, q in zip(quick_cols, quick_queries):
    if col.button(q, use_container_width=True, key=f"quick_{q}"):
        st.session_state["ask_input"] = q
        st.rerun()

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    greeting = f"Hi {user_name}!" if user_name and user_name != "team member" else "Hi!"
    st.markdown(
        f'<p style="color: #94a3b8; text-align: center; margin: 3rem 0;">'
        f"{greeting} I'm Lunar AI — I can help you explore sourcing data, "
        f"find relevant themes and deals, search Linear issues, and even create new ones. "
        f'Try asking about hot clusters, items in your domain, or anything about the pipeline.'
        f"</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Visual rendering helper
# ---------------------------------------------------------------------------

def _render_visual(vis):
    """Render a stored visual (table or chart)."""
    if vis["type"] == "table":
        if vis.get("caption"):
            st.caption(vis["caption"])
        df = pd.DataFrame(vis["data"])
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        # Chart
        df = pd.DataFrame(vis["data"])
        if df.empty:
            return
        if vis.get("caption"):
            st.caption(vis["caption"])
        ct = vis["type"]
        x, y, color = vis.get("x"), vis.get("y"), vis.get("color")
        if x and x not in df.columns:
            x = df.columns[0]
        if y and y not in df.columns:
            y = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        if color and color not in df.columns:
            color = None
        try:
            if ct == "bar":
                fig = px.bar(df, x=x, y=y, color=color)
            elif ct == "line":
                fig = px.line(df, x=x, y=y, color=color)
            elif ct == "pie":
                fig = px.pie(df, names=x, values=y)
            else:
                return
            style_fig(fig)
            fig.update_layout(margin=dict(t=10))
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass


# Render chat history (text + visuals)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("content"):
            st.markdown(_safe_markdown(msg["content"]))
        for vis in msg.get("visuals", []):
            _render_visual(vis)


# --------------------------------------------------------------------------
# Handle new input
# --------------------------------------------------------------------------

prompt = st.chat_input("Ask anything about sourcing data, clusters, Linear issues...") or st.session_state.pop("ask_input", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response_text = _run_agent(prompt, st.session_state.messages[:-1])
            except Exception as e:
                response_text = f"Sorry, I encountered an error: {e}"

        # Render response text
        if response_text:
            st.markdown(_safe_markdown(response_text))

        # Render any visuals the agent produced this turn
        visuals = st.session_state.get("visuals", [])
        for vis in visuals:
            _render_visual(vis)

        # Store message with visuals for history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "visuals": visuals,
        })
