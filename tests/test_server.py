"""Tests for the Phase 1 MCP server scaffold. docs/ARCHITECTURE.md Phase 1."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from mcp.server.fastmcp import FastMCP

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server, run_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    github_mcp_url="http://localhost:9002/mcp",
    jira_api_token="jira-token",  # noqa: S106
    github_token="github-token",  # noqa: S106
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


def test_server_exposes_create_feature_from_problem_statement_tool():
    """PRD §3.1: server exposes a tool to create a Jira Feature."""
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert "create_feature_from_problem_statement" in tool_names


def test_create_feature_from_problem_statement_delegates_to_jira_client():
    server = create_server(TEST_CONFIG)
    fake_session = AsyncMock()

    @asynccontextmanager
    async def _fake_jira_session(config):
        yield fake_session

    async def _call():
        with (
            patch("e2e_mcp_server.server.jira_session", _fake_jira_session),
            patch(
                "e2e_mcp_server.server.create_feature",
                AsyncMock(return_value="PROJ-1"),
            ) as fake_create_feature,
        ):
            result = await server.call_tool(
                "create_feature_from_problem_statement",
                {"problem_statement": "Users can't log in", "project_key": "PROJ"},
            )
            fake_create_feature.assert_awaited_once_with(
                fake_session,
                "PROJ",
                "Users can't log in",
            )
            return result

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert text == "PROJ-1"


def test_run_server_builds_and_runs_the_server():
    with patch("e2e_mcp_server.server.FastMCP") as fake_fastmcp_cls:
        fake_server = fake_fastmcp_cls.return_value
        run_server(TEST_CONFIG)
        fake_server.run.assert_called_once_with()
