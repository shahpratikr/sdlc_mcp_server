"""Jira MCP client wrapper: session mgmt and Feature creation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from e2e_mcp_server.config import Config


@asynccontextmanager
async def jira_session(config: Config) -> AsyncIterator[ClientSession]:
    """Open an initialized MCP client session to the Jira child MCP server."""
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
) -> str:
    """Create a Jira Feature issue for a problem statement via the Jira MCP server."""
    result = await session.call_tool(
        "createJiraIssue",
        {
            "projectKey": project_key,
            "issueType": "Feature",
            "summary": problem_statement,
            "description": problem_statement,
        },
    )
    content = result.content[0]
    return content.text if hasattr(content, "text") else str(content)


def _text_of(result) -> str:
    """Extract text content from an MCP tool call result."""
    content = result.content[0]
    return content.text if hasattr(content, "text") else str(content)


async def create_story(
    session: ClientSession,
    project_key: str,
    feature_key: str,
    summary: str,
    description: str,
) -> str:
    """Refine a Feature into a user story issue in Jira."""
    result = await session.call_tool(
        "createJiraIssue",
        {
            "projectKey": project_key,
            "issueType": "Story",
            "summary": summary,
            "description": description,
            "parentKey": feature_key,
        },
    )
    return _text_of(result)


async def set_story_estimate(
    session: ClientSession,
    issue_key: str,
    story_points: float,
) -> str:
    """Write a generated story point estimate to a user story in Jira."""
    result = await session.call_tool(
        "updateJiraIssue",
        {
            "issueKey": issue_key,
            "fields": {"storyPoints": story_points},
        },
    )
    return _text_of(result)


async def assign_story(
    session: ClientSession,
    issue_key: str,
    assignee: str,
) -> str:
    """Assign a user story to a developer in Jira."""
    result = await session.call_tool(
        "updateJiraIssue",
        {
            "issueKey": issue_key,
            "fields": {"assignee": assignee},
        },
    )
    return _text_of(result)


async def list_sprints(
    session: ClientSession,
    board_id: str,
) -> str:
    """Read board/sprint structure to select or confirm a target sprint."""
    result = await session.call_tool(
        "getSprintsForBoard",
        {"boardId": board_id},
    )
    return _text_of(result)


async def schedule_story(
    session: ClientSession,
    issue_key: str,
    sprint_id: str,
) -> str:
    """Schedule a user story into a sprint in Jira."""
    result = await session.call_tool(
        "moveIssueToSprint",
        {
            "issueKey": issue_key,
            "sprintId": sprint_id,
        },
    )
    return _text_of(result)
