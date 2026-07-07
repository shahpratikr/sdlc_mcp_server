"""Tests for Phase 2 Jira Feature creation via the Jira MCP server."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from e2e_mcp_server.jira_client import JiraClientError, create_feature


def _fake_session(response_text):
    session = MagicMock()
    result = MagicMock()
    result.content = [MagicMock(text=response_text)]
    session.call_tool = AsyncMock(return_value=result)
    return session


def test_create_feature_calls_create_issue_and_returns_key():
    session = _fake_session(json.dumps({"key": "PROJ-1"}))

    key = asyncio.run(create_feature(session, "PROJ", "Users need X", "- AC one"))

    assert key == "PROJ-1"
    session.call_tool.assert_awaited_once()
    tool_name, args = session.call_tool.call_args.args
    assert tool_name == "createIssue"
    assert args["projectKey"] == "PROJ"
    assert args["issueType"] == "Feature"
    assert "Users need X" in args["description"]
    assert "- AC one" in args["description"]


def test_create_feature_raises_on_unparseable_response():
    session = _fake_session("not json")

    with pytest.raises(JiraClientError):
        asyncio.run(create_feature(session, "PROJ", "Users need X", "- AC one"))
