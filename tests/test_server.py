"""Tests for the Phase 1 MCP server scaffold. docs/ARCHITECTURE.md Phase 1."""

import asyncio
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server, run_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    jira_api_token="jira-token",  # noqa: S106
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


def test_run_server_builds_and_runs_the_server():
    with patch("e2e_mcp_server.server.FastMCP") as fake_fastmcp_cls:
        fake_server = fake_fastmcp_cls.return_value
        run_server(TEST_CONFIG)
        fake_server.run.assert_called_once_with()
