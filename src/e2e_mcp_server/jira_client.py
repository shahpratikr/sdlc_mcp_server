"""Jira MCP client wiring: session management and issue creation (Phase 1, 2, 4)."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from e2e_mcp_server.config import Config

_FEATURE_ISSUE_TYPE = "Feature"
_STORY_ISSUE_TYPE = "Story"


class JiraClientError(Exception):
    """Raised when the Jira MCP server's response cannot be parsed or used."""


@asynccontextmanager
async def jira_session(config: Config) -> AsyncIterator[ClientSession]:
    """Open an initialized MCP session to the Jira child MCP server. R: Phase 1."""
    headers = {"Authorization": f"Bearer {config.jira_api_token}"}
    async with streamablehttp_client(config.jira_mcp_url, headers=headers) as (
        read_stream,
        write_stream,
        _get_session_id,
    ), ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        yield session


async def create_feature(
    session: ClientSession,
    project_key: str,
    problem_statement: str,
    acceptance_criteria: str,
) -> str:
    """Create a Jira Feature via the Jira MCP server and return its key. PRD §3.1."""
    description = f"{problem_statement}\n\nAcceptance Criteria:\n{acceptance_criteria}"
    result = await session.call_tool(
        "createIssue",
        {
            "projectKey": project_key,
            "issueType": _FEATURE_ISSUE_TYPE,
            "summary": problem_statement,
            "description": description,
        },
    )
    return _extract_issue_key(result)


async def update_feature_acceptance_criteria(
    session: ClientSession,
    feature_key: str,
    acceptance_criteria: str,
) -> None:
    """Update a Jira Feature's acceptance criteria via the Jira MCP server. PRD §3.2."""
    description = f"Acceptance Criteria:\n{acceptance_criteria}"
    await session.call_tool(
        "updateIssue",
        {
            "issueKey": feature_key,
            "description": description,
        },
    )


def project_key_from_issue_key(issue_key: str) -> str:
    """Derive a Jira project key from an issue key such as 'PROJ-1'. PRD §3.3."""
    return issue_key.split("-", maxsplit=1)[0]


async def get_feature_acceptance_criteria(
    session: ClientSession,
    feature_key: str,
) -> str:
    """Fetch the approved acceptance criteria stored on a Jira Feature. PRD §3.3."""
    result = await session.call_tool("getIssue", {"issueKey": feature_key})
    content = result.content[0]  # type: ignore[attr-defined]
    text = getattr(content, "text", None)
    if text is None:
        msg = "Jira MCP getIssue response did not contain text content"
        raise JiraClientError(msg)
    try:
        data = json.loads(text)
        return data["description"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        msg = "Jira MCP getIssue response did not contain a usable description"
        raise JiraClientError(msg) from exc


async def create_story(
    session: ClientSession,
    project_key: str,
    summary: str,
) -> str:
    """Create a Jira Story via the Jira MCP server and return its key. PRD §3.3."""
    result = await session.call_tool(
        "createIssue",
        {
            "projectKey": project_key,
            "issueType": _STORY_ISSUE_TYPE,
            "summary": summary,
            "description": summary,
        },
    )
    return _extract_issue_key(result)


async def update_story_estimate_and_acceptance_criteria(
    session: ClientSession,
    story_key: str,
    story_points: int,
    acceptance_criteria: str,
) -> None:
    """Write a story's point estimate and acceptance criteria to Jira. PRD §3.3."""
    description = f"Acceptance Criteria:\n{acceptance_criteria}"
    await session.call_tool(
        "updateIssue",
        {
            "issueKey": story_key,
            "description": description,
            "storyPoints": story_points,
        },
    )


async def schedule_story_into_sprint(
    session: ClientSession,
    story_key: str,
    board: str,
    sprint: str,
) -> None:
    """Schedule a Jira Story into the given board and sprint. PRD §3.3."""
    await session.call_tool(
        "scheduleIssue",
        {
            "issueKey": story_key,
            "board": board,
            "sprint": sprint,
        },
    )


async def assign_story(
    session: ClientSession,
    story_key: str,
    assignee: str,
) -> None:
    """Assign a Jira Story to a developer. PRD §3.3."""
    await session.call_tool(
        "assignIssue",
        {
            "issueKey": story_key,
            "assignee": assignee,
        },
    )


def _extract_issue_key(result: object) -> str:
    """Parse the Jira MCP createIssue result for the created issue key. PRD §3.1."""
    content = result.content[0]  # type: ignore[attr-defined]
    text = getattr(content, "text", None)
    if text is None:
        msg = "Jira MCP createIssue response did not contain text content"
        raise JiraClientError(msg)
    try:
        data = json.loads(text)
        return data["key"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        msg = "Jira MCP createIssue response did not contain a usable issue key"
        raise JiraClientError(msg) from exc
