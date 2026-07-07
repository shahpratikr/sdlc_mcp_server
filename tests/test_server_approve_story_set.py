"""Tests for the Phase 5 approve_story_set tool. PRD §3.4."""

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


def test_approving_story_set_returns_approved_status():
    server = create_server(TEST_CONFIG)

    result = asyncio.run(
        server.call_tool("approve_story_set", {"feature_key": "PROJ-1"}),
    )
    text = _result_text(result)
    assert "PROJ-1" in text
    assert "approved" in text


def test_requesting_regeneration_returns_regeneration_status():
    server = create_server(TEST_CONFIG)

    result = asyncio.run(
        server.call_tool(
            "approve_story_set",
            {"feature_key": "PROJ-1", "regenerate": True},
        ),
    )
    text = _result_text(result)
    assert "PROJ-1" in text
    assert "regeneration_requested" in text
