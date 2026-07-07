"""Tests for the Phase 6 proceed tool. PRD §3.5."""

import asyncio

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    jira_api_token="jira-token",  # noqa: S106
)


def _result_text(result):
    content = result[0]
    return content[0].text if isinstance(content, list) else content.content[0].text


def test_proceed_returns_proceeded_status():
    server = create_server(TEST_CONFIG)

    result = asyncio.run(
        server.call_tool("proceed", {"story_key": "PROJ-2"}),
    )
    text = _result_text(result)
    assert "PROJ-2" in text
    assert "proceeded" in text
