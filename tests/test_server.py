"""Tests for the Phase 1 MCP server scaffold. docs/ARCHITECTURE.md Phase 1."""

import asyncio

from mcp.server.fastmcp import FastMCP

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    github_mcp_url="http://localhost:9002/mcp",
    jira_api_token="jira-token",
    github_token="github-token",
)


def test_create_server_returns_fastmcp_instance():
    server = create_server(TEST_CONFIG)
    assert isinstance(server, FastMCP)


def test_server_exposes_ping_tool():
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert "ping" in tool_names


def test_ping_tool_returns_pong():
    server = create_server(TEST_CONFIG)

    async def _call_ping():
        return await server.call_tool("ping", {})

    result = asyncio.run(_call_ping())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert text == "pong"
