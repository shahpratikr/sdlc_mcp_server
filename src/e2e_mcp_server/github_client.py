from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from e2e_mcp_server.config import Config


@asynccontextmanager
async def github_session(config: Config) -> AsyncIterator[ClientSession]:
    """Open an initialized MCP client session to the GitHub child MCP server."""
    headers = {"Authorization": f"Bearer {config.github_token}"}
    async with streamablehttp_client(config.github_mcp_url, headers=headers) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session
