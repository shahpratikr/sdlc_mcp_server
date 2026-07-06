"""Tests for jira_client.create_feature. PRD §3.1 (Feature Creation)."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from e2e_mcp_server.jira_client import create_feature


class _FakeSession:
    def __init__(self, issue_key: str):
        self.call_tool = AsyncMock(
            return_value=SimpleNamespace(content=[SimpleNamespace(text=issue_key)]),
        )


def test_create_feature_calls_jira_mcp_server_with_project_and_statement():  # noqa: D103
    session = _FakeSession("PROJ-123")
    statement = "Users can't log in"

    result = asyncio.run(
        create_feature(session, project_key="PROJ", problem_statement=statement),
    )

    assert result == "PROJ-123"  # noqa: S101
    session.call_tool.assert_awaited_once_with(
        "createJiraIssue",
        {
            "projectKey": "PROJ",
            "issueType": "Feature",
            "summary": statement,
            "description": statement,
        },
    )
