"""GitHub MCP client wiring: session management and issue creation. ARCHITECTURE Phase 8."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from e2e_mcp_server.config import Config

_FEATURE_LABEL = "feature"


class GitHubClientError(Exception):
    """Raised when the GitHub MCP server's response cannot be parsed or used."""


@asynccontextmanager
async def github_session(config: Config) -> AsyncIterator[ClientSession]:
    """Open an initialized MCP session to the GitHub child MCP server. PRD §6/§7."""
    headers = {"Authorization": f"Bearer {config.github_api_token}"}
    async with streamablehttp_client(config.github_mcp_url, headers=headers) as (
        read_stream,
        write_stream,
        _get_session_id,
    ), ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        yield session


async def create_feature_issue(
    session: ClientSession,
    repo_owner: str,
    repo_name: str,
    problem_statement: str,
    acceptance_criteria: str,
) -> str:
    """Create a GitHub parent Issue labeled as feature-level. PRD §3.1."""
    body = f"{problem_statement}\n\nAcceptance Criteria:\n{acceptance_criteria}"
    result = await session.call_tool(
        "createIssue",
        {
            "owner": repo_owner,
            "repo": repo_name,
            "title": problem_statement,
            "body": body,
            "labels": [_FEATURE_LABEL],
        },
    )
    return _extract_issue_number(result)


async def update_feature_issue_body(
    session: ClientSession,
    repo_owner: str,
    repo_name: str,
    issue_number: str,
    acceptance_criteria: str,
) -> None:
    """Update a GitHub parent Issue's body with edited acceptance criteria. PRD §3.2."""
    body = f"Acceptance Criteria:\n{acceptance_criteria}"
    await session.call_tool(
        "updateIssue",
        {
            "owner": repo_owner,
            "repo": repo_name,
            "issueNumber": issue_number,
            "body": body,
        },
    )


async def get_feature_issue_body(
    session: ClientSession,
    repo_owner: str,
    repo_name: str,
    issue_number: str,
) -> str:
    """Fetch the approved acceptance criteria stored on a GitHub parent Issue. PRD §3.3."""
    result = await session.call_tool(
        "getIssue",
        {"owner": repo_owner, "repo": repo_name, "issueNumber": issue_number},
    )
    content = result.content[0]  # type: ignore[attr-defined]
    text = getattr(content, "text", None)
    if text is None:
        msg = "GitHub MCP getIssue response did not contain text content"
        raise GitHubClientError(msg)
    try:
        data = json.loads(text)
        return data["body"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        msg = "GitHub MCP getIssue response did not contain a usable body"
        raise GitHubClientError(msg) from exc


async def create_story_issue(
    session: ClientSession,
    repo_owner: str,
    repo_name: str,
    parent_issue_number: str,
    summary: str,
    acceptance_criteria: str,
) -> str:
    """Create a GitHub child Issue for a story, linked to its parent feature Issue. PRD §3.3."""
    body = f"{summary}\n\nAcceptance Criteria:\n{acceptance_criteria}"
    result = await session.call_tool(
        "createIssue",
        {
            "owner": repo_owner,
            "repo": repo_name,
            "title": summary,
            "body": body,
            "parentIssueNumber": parent_issue_number,
        },
    )
    return _extract_issue_number(result)


async def assign_issue(
    session: ClientSession,
    repo_owner: str,
    repo_name: str,
    issue_number: str,
    assignee: str,
) -> None:
    """Assign a GitHub Issue to a developer. PRD §3.3."""
    await session.call_tool(
        "assignIssue",
        {
            "owner": repo_owner,
            "repo": repo_name,
            "issueNumber": issue_number,
            "assignee": assignee,
        },
    )


def _extract_issue_number(result: object) -> str:
    """Parse the GitHub MCP createIssue result for the created issue number. PRD §3.1."""
    content = result.content[0]  # type: ignore[attr-defined]
    text = getattr(content, "text", None)
    if text is None:
        msg = "GitHub MCP createIssue response did not contain text content"
        raise GitHubClientError(msg)
    try:
        data = json.loads(text)
        return str(data["number"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        msg = "GitHub MCP createIssue response did not contain a usable issue number"
        raise GitHubClientError(msg) from exc
