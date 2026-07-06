"""Jira MCP client wrapper: session mgmt and Feature creation. PRD §3.1, §6, §7."""

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
