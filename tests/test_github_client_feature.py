"""Tests for GitHub parent Issue (feature) creation and update. ARCHITECTURE Phase 8."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from e2e_mcp_server.github_client import (
    GitHubClientError,
    create_feature_issue,
    get_feature_issue_body,
    update_feature_issue_body,
)


def _fake_session(response_text):
    session = MagicMock()
    result = MagicMock()
    result.content = [MagicMock(text=response_text)]
    session.call_tool = AsyncMock(return_value=result)
    return session


def test_create_feature_issue_calls_create_issue_and_returns_number():
    session = _fake_session(json.dumps({"number": 1}))

    number = asyncio.run(
        create_feature_issue(session, "acme", "widgets", "Users need X", "- AC one"),
    )

    assert number == "1"
    session.call_tool.assert_awaited_once()
    tool_name, args = session.call_tool.call_args.args
    assert tool_name == "createIssue"
    assert args["owner"] == "acme"
    assert args["repo"] == "widgets"
    assert args["labels"] == ["feature"]
    assert "Users need X" in args["body"]
    assert "- AC one" in args["body"]


def test_create_feature_issue_raises_on_unparseable_response():
    session = _fake_session("not json")

    with pytest.raises(GitHubClientError):
        asyncio.run(
            create_feature_issue(session, "acme", "widgets", "Users need X", "- AC one"),
        )


def test_update_feature_issue_body_calls_update_issue():
    session = _fake_session(None)

    asyncio.run(
        update_feature_issue_body(session, "acme", "widgets", "1", "- edited AC"),
    )

    session.call_tool.assert_awaited_once()
    tool_name, args = session.call_tool.call_args.args
    assert tool_name == "updateIssue"
    assert args["owner"] == "acme"
    assert args["repo"] == "widgets"
    assert args["issueNumber"] == "1"
    assert "- edited AC" in args["body"]


def test_get_feature_issue_body_calls_get_issue_and_returns_body():
    session = _fake_session(json.dumps({"body": "- AC one"}))

    text = asyncio.run(get_feature_issue_body(session, "acme", "widgets", "1"))

    assert text == "- AC one"
    session.call_tool.assert_awaited_once_with(
        "getIssue",
        {"owner": "acme", "repo": "widgets", "issueNumber": "1"},
    )


def test_get_feature_issue_body_raises_on_unparseable_response():
    session = _fake_session("not json")

    with pytest.raises(GitHubClientError):
        asyncio.run(get_feature_issue_body(session, "acme", "widgets", "1"))


def test_get_feature_issue_body_raises_when_no_text_content():
    session = _fake_session(None)

    with pytest.raises(GitHubClientError, match="did not contain text content"):
        asyncio.run(get_feature_issue_body(session, "acme", "widgets", "1"))


def test_create_feature_issue_raises_when_no_text_content():
    session = _fake_session(None)

    with pytest.raises(GitHubClientError, match="did not contain text content"):
        asyncio.run(
            create_feature_issue(session, "acme", "widgets", "Users need X", "- AC one"),
        )
