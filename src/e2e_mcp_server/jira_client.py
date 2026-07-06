from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from e2e_mcp_server.config import Config


@asynccontextmanager
async def jira_session(config: Config) -> AsyncIterator[ClientSession]:
    """Open an initialized MCP client session to the Jira child MCP server."""
    headers = {"Authorization": f"Bearer {config.jira_api_token}"}
    async with streamablehttp_client(config.jira_mcp_url, headers=headers) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session
