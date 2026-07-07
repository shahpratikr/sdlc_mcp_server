"""Tests for Phase 4 Jira Story creation, estimation, and scheduling."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from e2e_mcp_server.jira_client import (
    JiraClientError,
    assign_story,
    create_story,
    get_feature_acceptance_criteria,
    project_key_from_issue_key,
    schedule_story_into_sprint,
    update_story_estimate_and_acceptance_criteria,
)


def _fake_session(response_text=None):
    session = MagicMock()
    result = MagicMock()
    result.content = [MagicMock(text=response_text)]
    session.call_tool = AsyncMock(return_value=result)
    return session


def test_project_key_from_issue_key():
    assert project_key_from_issue_key("PROJ-42") == "PROJ"


def test_get_feature_acceptance_criteria_calls_get_issue_and_returns_description():
    session = _fake_session(json.dumps({"description": "- AC one"}))

    text = asyncio.run(get_feature_acceptance_criteria(session, "PROJ-1"))

    assert text == "- AC one"
    session.call_tool.assert_awaited_once_with("getIssue", {"issueKey": "PROJ-1"})


def test_get_feature_acceptance_criteria_raises_on_unparseable_response():
    session = _fake_session("not json")

    with pytest.raises(JiraClientError):
        asyncio.run(get_feature_acceptance_criteria(session, "PROJ-1"))


def test_create_story_calls_create_issue_and_returns_key():
    session = _fake_session(json.dumps({"key": "PROJ-2"}))

    key = asyncio.run(create_story(session, "PROJ", "As a user, I want X"))

    assert key == "PROJ-2"
    tool_name, args = session.call_tool.call_args.args
    assert tool_name == "createIssue"
    assert args["projectKey"] == "PROJ"
    assert args["issueType"] == "Story"
    assert args["summary"] == "As a user, I want X"


def test_update_story_estimate_and_acceptance_criteria_calls_update_issue():
    session = _fake_session()

    asyncio.run(
        update_story_estimate_and_acceptance_criteria(session, "PROJ-2", 3, "- AC one"),
    )

    session.call_tool.assert_awaited_once_with(
        "updateIssue",
        {
            "issueKey": "PROJ-2",
            "description": "Acceptance Criteria:\n- AC one",
            "storyPoints": 3,
        },
    )


def test_schedule_story_into_sprint_calls_schedule_issue():
    session = _fake_session()

    asyncio.run(schedule_story_into_sprint(session, "PROJ-2", "Board 1", "Sprint 4"))

    session.call_tool.assert_awaited_once_with(
        "scheduleIssue",
        {"issueKey": "PROJ-2", "board": "Board 1", "sprint": "Sprint 4"},
    )


def test_assign_story_calls_assign_issue():
    session = _fake_session()

    asyncio.run(assign_story(session, "PROJ-2", "dev@example.com"))

    session.call_tool.assert_awaited_once_with(
        "assignIssue",
        {"issueKey": "PROJ-2", "assignee": "dev@example.com"},
    )
