"""Tests for GitHub child Issue (story) creation and assignment. ARCHITECTURE Phase 8."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from e2e_mcp_server.github_client import (
    GitHubClientError,
    assign_issue,
    create_story_issue,
)


def _fake_session(response_text=None):
    session = MagicMock()
    result = MagicMock()
    result.content = [MagicMock(text=response_text)]
    session.call_tool = AsyncMock(return_value=result)
    return session


def test_create_story_issue_calls_create_issue_and_returns_number():
    session = _fake_session(json.dumps({"number": 2}))

    number = asyncio.run(
        create_story_issue(
            session,
            "acme",
            "widgets",
            "1",
            "As a user, I want X",
            "- AC one",
        ),
    )

    assert number == "2"
    tool_name, args = session.call_tool.call_args.args
    assert tool_name == "createIssue"
    assert args["owner"] == "acme"
    assert args["repo"] == "widgets"
    assert args["parentIssueNumber"] == "1"
    assert "As a user, I want X" in args["body"]
    assert "- AC one" in args["body"]


def test_create_story_issue_raises_on_unparseable_response():
    session = _fake_session("not json")

    with pytest.raises(GitHubClientError):
        asyncio.run(
            create_story_issue(session, "acme", "widgets", "1", "Story", "- AC"),
        )


def test_assign_issue_calls_assign_issue():
    session = _fake_session()

    asyncio.run(assign_issue(session, "acme", "widgets", "2", "dev@example.com"))

    session.call_tool.assert_awaited_once_with(
        "assignIssue",
        {
            "owner": "acme",
            "repo": "widgets",
            "issueNumber": "2",
            "assignee": "dev@example.com",
        },
    )
