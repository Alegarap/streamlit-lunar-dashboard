"""Linear GraphQL client for the Lunar Dashboard.

Provides search, get, and create operations for Linear issues.
Uses the n8n_agent API key (bot-attributed).
"""

from __future__ import annotations

import json
import os
import urllib.request

try:
    import streamlit as st
except ImportError:
    st = None  # allow import outside Streamlit for testing

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LINEAR_API_URL = "https://api.linear.app/graphql"

# Corrected team IDs (CLAUDE.md has them swapped — see feedback_linear_team_ids.md)
TEAMS = {
    "THE": "e7f22ea8-18ae-477a-9ec5-7971f501b480",  # Theme & Thesis
    "DEAL": "44c6002d-49f7-4891-8c14-d4e77bd40d01",  # Dealflow
    "IN": "7e6d42c2-7804-44cb-8e13-578db1d96c83",    # Investment
    "GEN": "c9e2f090-1a32-4a24-9c85-1b4e0e1e3c0d",  # General
    "ENG": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  # Engineering (placeholder)
}


def _resolve_api_key() -> str:
    """Resolve Linear API key from Streamlit secrets or env."""
    key = ""
    if st is not None:
        try:
            key = st.secrets.get("LINEAR_API_KEY", "")
        except FileNotFoundError:
            pass
    if not key:
        key = os.environ.get("LINEAR_API_KEY", "")
    return key


def _graphql(query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL request against the Linear API."""
    api_key = _resolve_api_key()
    if not api_key:
        return {"error": "LINEAR_API_KEY not configured. Add it to Streamlit secrets or environment."}

    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        LINEAR_API_URL,
        data=body,
        headers={
            "Authorization": api_key,  # No "Bearer" prefix per Linear convention
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if "errors" in result:
                return {"error": "; ".join(e.get("message", str(e)) for e in result["errors"])}
            return result.get("data", {})
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_issues(query: str, team: str | None = None, limit: int = 10) -> list[dict]:
    """Search Linear issues by text, optionally filtered by team key (THE, DEAL, etc.).

    Returns list of {id, identifier, title, state, url, assignee, labels, description}.
    """
    team_filter = ""
    if team and team in TEAMS:
        team_filter = f', filter: {{ team: {{ id: {{ eq: "{TEAMS[team]}" }} }} }}'

    gql = f"""
    query SearchIssues($query: String!, $limit: Int!) {{
      searchIssues(query: $query, first: $limit{team_filter}) {{
        nodes {{
          id
          identifier
          title
          url
          description
          state {{ name }}
          assignee {{ name }}
          labels {{ nodes {{ name }} }}
          createdAt
        }}
      }}
    }}
    """
    data = _graphql(gql, {"query": query, "limit": limit})
    if "error" in data:
        return [{"error": data["error"]}]

    nodes = data.get("searchIssues", {}).get("nodes", [])
    return [
        {
            "id": n["id"],
            "identifier": n["identifier"],
            "title": n["title"],
            "url": n["url"],
            "description": (n.get("description") or "")[:500],
            "state": n.get("state", {}).get("name", ""),
            "assignee": n.get("assignee", {}).get("name", "") if n.get("assignee") else "",
            "labels": [l["name"] for l in n.get("labels", {}).get("nodes", [])],
            "created_at": n.get("createdAt", ""),
        }
        for n in nodes
    ]


def get_issue(identifier: str) -> dict:
    """Get full details of a Linear issue by identifier (e.g. THE-1234).

    Returns {id, identifier, title, description, state, assignee, labels, url, comments}.
    """
    gql = """
    query GetIssue($filter: IssueFilter!) {
      issues(filter: $filter, first: 1) {
        nodes {
          id
          identifier
          title
          description
          url
          state { name }
          assignee { name }
          labels { nodes { name } }
          comments(first: 5) {
            nodes { body user { name } createdAt }
          }
          createdAt
          updatedAt
        }
      }
    }
    """
    # Parse identifier like "THE-1234" → team prefix + number
    data = _graphql(gql, {"filter": {"identifier": {"eq": identifier}}})
    if "error" in data:
        return {"error": data["error"]}

    nodes = data.get("issues", {}).get("nodes", [])
    if not nodes:
        return {"error": f"Issue {identifier} not found"}

    n = nodes[0]
    return {
        "id": n["id"],
        "identifier": n["identifier"],
        "title": n["title"],
        "description": (n.get("description") or "")[:2000],
        "url": n["url"],
        "state": n.get("state", {}).get("name", ""),
        "assignee": n.get("assignee", {}).get("name", "") if n.get("assignee") else "",
        "labels": [l["name"] for l in n.get("labels", {}).get("nodes", [])],
        "comments": [
            {"body": c["body"][:500], "author": c.get("user", {}).get("name", ""), "date": c["createdAt"]}
            for c in n.get("comments", {}).get("nodes", [])
        ],
        "created_at": n.get("createdAt", ""),
        "updated_at": n.get("updatedAt", ""),
    }


def create_issue(
    team: str,
    title: str,
    description: str,
    assignee_id: str | None = None,
) -> dict:
    """Create a new Linear issue.

    Args:
        team: Team key (THE, DEAL)
        title: Issue title
        description: Issue description (markdown)
        assignee_id: Optional Linear user UUID to assign

    Returns {id, identifier, title, url} or {error: ...}.
    """
    team_id = TEAMS.get(team)
    if not team_id:
        return {"error": f"Unknown team: {team}. Use one of: {', '.join(TEAMS.keys())}"}

    variables = {
        "input": {
            "teamId": team_id,
            "title": title,
            "description": description,
        }
    }
    if assignee_id:
        variables["input"]["assigneeId"] = assignee_id

    gql = """
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue {
          id
          identifier
          title
          url
        }
      }
    }
    """
    data = _graphql(gql, variables)
    if "error" in data:
        return {"error": data["error"]}

    result = data.get("issueCreate", {})
    if not result.get("success"):
        return {"error": "Issue creation failed"}

    issue = result.get("issue", {})
    return {
        "id": issue.get("id", ""),
        "identifier": issue.get("identifier", ""),
        "title": issue.get("title", ""),
        "url": issue.get("url", ""),
    }
