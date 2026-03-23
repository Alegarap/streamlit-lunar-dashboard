"""Linear GraphQL client for the Lunar Dashboard.

Provides search, get, create, and update operations for Linear issues.
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

# "Lunar Dashboard" label IDs per team (auto-applied to all created issues)
_LUNAR_DASHBOARD_LABELS = {
    "THE": "e3166dec-1c84-4b59-8438-ab18c18ab123",
    "DEAL": "d271a7e7-11be-496d-a308-cc80e498f2fb",
    "IN": "8a3846e9-6e9d-4355-9986-c6910348872a",
}

# Known label name → ID mapping (workspace + team-specific)
KNOWN_LABELS = {
    # Workspace-level
    "Academic Sourcing": "36d45be9-4df7-4004-8ee1-5e835331302e",
    # THE team
    "Hacker News": "85634327-3a0f-4845-862b-88770aa3600a",
    "Conference": "eca14233-e7b8-4874-89c8-eff6d127316e",
    # DEAL team
    "Deal Validation": "69a4fba5-8e38-4b1c-bafa-8240e017d8ae",
    "Validated": "b63bb96a-fdea-4269-94f2-29d077134fbc",
    "Unverified": "dd46fa9e-2cb2-4551-a34a-98ccb57be79f",
    "Unactionable": "327b87e4-2b92-4ac6-898a-2ba230de749a",
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


def _resolve_label_ids(label_names: list[str], team: str) -> list[str]:
    """Resolve label names to IDs. Always includes 'Lunar Dashboard' for the team."""
    ids = []

    # Always add "Lunar Dashboard" label for this team
    dashboard_label = _LUNAR_DASHBOARD_LABELS.get(team)
    if dashboard_label:
        ids.append(dashboard_label)

    # Resolve additional labels by name
    for name in label_names:
        if name == "Lunar Dashboard":
            continue  # already added
        label_id = KNOWN_LABELS.get(name)
        if label_id:
            ids.append(label_id)

    return ids


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
    query SearchIssues($term: String!, $limit: Int!) {{
      searchIssues(term: $term, first: $limit{team_filter}) {{
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
    data = _graphql(gql, {"term": query, "limit": limit})
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

    Uses the `issue(id:)` query which accepts identifiers like "ENG-263".
    Returns {id, identifier, title, description, state, assignee, labels, url, comments}.
    """
    gql = """
    query GetIssue($id: String!) {
      issue(id: $id) {
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
    """
    data = _graphql(gql, {"id": identifier})
    if "error" in data:
        return {"error": data["error"]}

    n = data.get("issue")
    if not n:
        return {"error": f"Issue {identifier} not found"}

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
    label_names: list[str] | None = None,
) -> dict:
    """Create a new Linear issue.

    Args:
        team: Team key (THE, DEAL)
        title: Issue title
        description: Issue description (markdown)
        assignee_id: Optional Linear user UUID to assign
        label_names: Optional label names from the source item (e.g. ["Academic Sourcing"]).
                     "Lunar Dashboard" is always added automatically.

    Returns {id, identifier, title, url} or {error: ...}.
    """
    team_id = TEAMS.get(team)
    if not team_id:
        return {"error": f"Unknown team: {team}. Use one of: {', '.join(TEAMS.keys())}"}

    label_ids = _resolve_label_ids(label_names or [], team)

    variables = {
        "input": {
            "teamId": team_id,
            "title": title,
            "description": description,
        }
    }
    if assignee_id:
        variables["input"]["assigneeId"] = assignee_id
    if label_ids:
        variables["input"]["labelIds"] = label_ids

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


def update_issue(
    issue_id: str,
    title: str | None = None,
    description: str | None = None,
    assignee_id: str | None = None,
    state_name: str | None = None,
    add_label_names: list[str] | None = None,
    comment: str | None = None,
) -> dict:
    """Update an existing Linear issue.

    Args:
        issue_id: Linear issue ID (UUID) or identifier (e.g. "THE-1234")
        title: New title (optional)
        description: New description (optional)
        assignee_id: New assignee Linear user UUID (optional)
        state_name: New state name like "In Progress", "Done" (optional)
        add_label_names: Label names to add (optional)
        comment: Comment to add to the issue (optional)

    Returns {success: true, identifier, url} or {error: ...}.
    """
    # If identifier like "THE-1234" was passed, resolve to UUID first
    if "-" in issue_id and not _is_uuid(issue_id):
        issue_data = get_issue(issue_id)
        if "error" in issue_data:
            return issue_data
        issue_id = issue_data["id"]

    # Build update input
    update_input = {}
    if title is not None:
        update_input["title"] = title
    if description is not None:
        update_input["description"] = description
    if assignee_id is not None:
        update_input["assigneeId"] = assignee_id

    # Resolve state name to ID if provided
    if state_name:
        state_id = _resolve_state(issue_id, state_name)
        if state_id:
            update_input["stateId"] = state_id

    # Resolve label names to IDs and add
    if add_label_names:
        label_ids = []
        for name in add_label_names:
            lid = KNOWN_LABELS.get(name)
            if lid:
                label_ids.append(lid)
        if label_ids:
            # Get existing labels and merge
            existing = get_issue(issue_id) if not update_input else {"labels": []}
            # We'll use addedLabelIds which appends without removing existing
            update_input["addedLabelIds"] = label_ids

    result_data = {}

    # Apply update if there are fields to change
    if update_input:
        gql = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue {
              id
              identifier
              title
              url
              state { name }
            }
          }
        }
        """
        data = _graphql(gql, {"id": issue_id, "input": update_input})
        if "error" in data:
            return {"error": data["error"]}
        result = data.get("issueUpdate", {})
        if not result.get("success"):
            return {"error": "Issue update failed"}
        issue = result.get("issue", {})
        result_data = {
            "success": True,
            "identifier": issue.get("identifier", ""),
            "url": issue.get("url", ""),
            "state": issue.get("state", {}).get("name", ""),
        }

    # Add comment if provided
    if comment:
        gql_comment = """
        mutation AddComment($input: CommentCreateInput!) {
          commentCreate(input: $input) {
            success
          }
        }
        """
        comment_data = _graphql(gql_comment, {"input": {"issueId": issue_id, "body": comment}})
        if "error" in comment_data:
            if result_data:
                result_data["comment_error"] = comment_data["error"]
            else:
                return {"error": comment_data["error"]}
        else:
            if not result_data:
                result_data = {"success": True}
            result_data["comment_added"] = True

    return result_data if result_data else {"error": "Nothing to update — provide at least one field"}


def _is_uuid(s: str) -> bool:
    """Check if string looks like a UUID."""
    parts = s.split("-")
    return len(parts) == 5 and all(len(p) > 3 for p in parts)


def _resolve_state(issue_id: str, state_name: str) -> str | None:
    """Resolve a state name to ID by querying the issue's team workflow states."""
    gql = """
    query IssueTeamStates($id: String!) {
      issue(id: $id) {
        team {
          states { nodes { id name } }
        }
      }
    }
    """
    data = _graphql(gql, {"id": issue_id})
    if "error" in data:
        return None
    states = data.get("issue", {}).get("team", {}).get("states", {}).get("nodes", [])
    target = state_name.lower()
    for s in states:
        if s["name"].lower() == target:
            return s["id"]
    return None
