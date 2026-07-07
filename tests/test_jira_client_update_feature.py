"""Tests for Phase 3 Jira Feature AC update via the Jira MCP server."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from e2e_mcp_server.jira_client import update_feature_acceptance_criteria


def test_update_feature_acceptance_criteria_calls_update_issue():
    session = MagicMock()
    session.call_tool = AsyncMock()

    asyncio.run(
        update_feature_acceptance_criteria(session, "PROJ-1", "- edited AC"),
    )

    session.call_tool.assert_awaited_once()
    tool_name, args = session.call_tool.call_args.args
    assert tool_name == "updateIssue"
    assert args["issueKey"] == "PROJ-1"
    assert "- edited AC" in args["description"]
