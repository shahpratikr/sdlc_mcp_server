from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from e2e_mcp_server.config import Config


@asynccontextmanager
async def github_session(config: Config) -> AsyncIterator[ClientSession]:
    """Open an initialized MCP client session to the GitHub child MCP server."""
    headers = {"Authorization": f"Bearer {config.github_token}"}
    async with streamablehttp_client(config.github_mcp_url, headers=headers) as (
        read_stream,
        write_stream,
        _get_session_id,
    ), ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        yield session


def _text_of(result) -> str:
    """Extract text content from an MCP tool call result."""
    content = result.content[0]
    return content.text if hasattr(content, "text") else str(content)


async def create_pull_request(  # noqa: PLR0913
    session: ClientSession,
    repository: str,
    head_branch: str,
    base_branch: str,
    issue_key: str,
    title: str,
) -> str:
    """Create a GitHub PR linked to the originating Jira story. PRD §3.6."""
    body = f"Resolves {issue_key}\n\nLinked Jira story: {issue_key}"
    result = await session.call_tool(
        "createPullRequest",
        {
            "repository": repository,
            "head": head_branch,
            "base": base_branch,
            "title": title,
            "body": body,
        },
    )
    return _text_of(result)


async def create_release(
    session: ClientSession,
    repository: str,
    tag_name: str,
    release_notes: str,
) -> str:
    """Create a GitHub Release (tag + notes) for completed work. PRD §3.8."""
    result = await session.call_tool(
        "createRelease",
        {
            "repository": repository,
            "tag_name": tag_name,
            "body": release_notes,
        },
    )
    return _text_of(result)
