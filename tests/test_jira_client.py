"""Tests for jira_client Feature/Story helpers. PRD §3.1, §3.2."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from e2e_mcp_server.jira_client import (
    assign_story,
    create_feature,
    create_story,
    list_sprints,
    schedule_story,
    set_story_estimate,
)


class _FakeSession:
    def __init__(self, issue_key: str):
        self.call_tool = AsyncMock(
            return_value=SimpleNamespace(content=[SimpleNamespace(text=issue_key)]),
        )


def test_create_feature_calls_jira_mcp_server_with_project_and_statement():
    session = _FakeSession("PROJ-123")
    statement = "Users can't log in"

    result = asyncio.run(
        create_feature(session, project_key="PROJ", problem_statement=statement),
    )

    assert result == "PROJ-123"
    session.call_tool.assert_awaited_once_with(
        "createJiraIssue",
        {
            "projectKey": "PROJ",
            "issueType": "Feature",
            "summary": statement,
            "description": statement,
        },
    )


def test_create_story_calls_jira_mcp_server_with_feature_link():
    session = _FakeSession("PROJ-124")

    result = asyncio.run(
        create_story(
            session,
            project_key="PROJ",
            feature_key="PROJ-123",
            summary="As a user, I can reset my password",
            description="Details",
        ),
    )

    assert result == "PROJ-124"
    session.call_tool.assert_awaited_once_with(
        "createJiraIssue",
        {
            "projectKey": "PROJ",
            "issueType": "Story",
            "summary": "As a user, I can reset my password",
            "description": "Details",
            "parentKey": "PROJ-123",
        },
    )


def test_set_story_estimate_writes_story_points():
    session = _FakeSession("PROJ-124")

    result = asyncio.run(
        set_story_estimate(session, issue_key="PROJ-124", story_points=3.0),
    )

    assert result == "PROJ-124"
    session.call_tool.assert_awaited_once_with(
        "updateJiraIssue",
        {"issueKey": "PROJ-124", "fields": {"storyPoints": 3.0}},
    )


def test_assign_story_writes_assignee():
    session = _FakeSession("PROJ-124")

    result = asyncio.run(assign_story(session, issue_key="PROJ-124", assignee="jdoe"))

    assert result == "PROJ-124"
    session.call_tool.assert_awaited_once_with(
        "updateJiraIssue",
        {"issueKey": "PROJ-124", "fields": {"assignee": "jdoe"}},
    )


def test_list_sprints_reads_board_sprint_structure():
    session = _FakeSession("[]")

    result = asyncio.run(list_sprints(session, board_id="1"))

    assert result == "[]"
    session.call_tool.assert_awaited_once_with("getSprintsForBoard", {"boardId": "1"})


def test_schedule_story_moves_issue_to_sprint():
    session = _FakeSession("PROJ-124")

    result = asyncio.run(schedule_story(session, issue_key="PROJ-124", sprint_id="10"))

    assert result == "PROJ-124"
    session.call_tool.assert_awaited_once_with(
        "moveIssueToSprint",
        {"issueKey": "PROJ-124", "sprintId": "10"},
    )
