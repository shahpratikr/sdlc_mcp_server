"""Tests for the Phase 3 approve_feature_acceptance_criteria tool."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    jira_api_token="jira-token",  # noqa: S106
)


def _result_text(result):
    content = result[0]
    return content[0].text if isinstance(content, list) else content.content[0].text


def test_plain_approval_does_not_update_jira():
    server = create_server(TEST_CONFIG)

    async def _run():
        with patch(
            "e2e_mcp_server.server.update_feature_acceptance_criteria",
            AsyncMock(),
        ) as fake_update:
            result = await server.call_tool(
                "approve_feature_acceptance_criteria",
                {"feature_key": "PROJ-1", "tracker": "jira"},
            )
            fake_update.assert_not_called()
            return result

    result = asyncio.run(_run())
    text = _result_text(result)
    assert "PROJ-1" in text
    assert "approved" in text


def test_plain_approval_does_not_update_github():
    server = create_server(TEST_CONFIG)

    async def _run():
        with patch(
            "e2e_mcp_server.server.update_feature_issue_body",
            AsyncMock(),
        ) as fake_update:
            result = await server.call_tool(
                "approve_feature_acceptance_criteria",
                {
                    "feature_key": "1",
                    "tracker": "github",
                    "repo_owner": "improving",
                    "repo_name": "widgets",
                },
            )
            fake_update.assert_not_called()
            return result

    result = asyncio.run(_run())
    text = _result_text(result)
    assert "1" in text
    assert "approved" in text


def test_edited_acceptance_criteria_updates_github_and_approves():
    server = create_server(TEST_CONFIG)
    fake_session = object()

    @asynccontextmanager
    async def _fake_github_session(config):
        assert config is TEST_CONFIG
        yield fake_session

    async def _run():
        with (
            patch("e2e_mcp_server.server.github_session", _fake_github_session),
            patch(
                "e2e_mcp_server.server.update_feature_issue_body",
                AsyncMock(),
            ) as fake_update,
        ):
            result = await server.call_tool(
                "approve_feature_acceptance_criteria",
                {
                    "feature_key": "1",
                    "tracker": "github",
                    "repo_owner": "improving",
                    "repo_name": "widgets",
                    "edited_acceptance_criteria": "- new AC",
                },
            )
            fake_update.assert_awaited_once_with(
                fake_session,
                "improving",
                "widgets",
                "1",
                "- new AC",
            )
            return result

    result = asyncio.run(_run())
    text = _result_text(result)
    assert "1" in text
    assert "approved" in text


def test_edited_acceptance_criteria_updates_jira_and_approves():
    server = create_server(TEST_CONFIG)
    fake_session = object()

    @asynccontextmanager
    async def _fake_jira_session(config):
        assert config is TEST_CONFIG
        yield fake_session

    async def _run():
        with (
            patch("e2e_mcp_server.server.jira_session", _fake_jira_session),
            patch(
                "e2e_mcp_server.server.update_feature_acceptance_criteria",
                AsyncMock(),
            ) as fake_update,
        ):
            result = await server.call_tool(
                "approve_feature_acceptance_criteria",
                {
                    "feature_key": "PROJ-1",
                    "tracker": "jira",
                    "edited_acceptance_criteria": "- new AC",
                },
            )
            fake_update.assert_awaited_once_with(fake_session, "PROJ-1", "- new AC")
            return result

    result = asyncio.run(_run())
    text = _result_text(result)
    assert "PROJ-1" in text
    assert "approved" in text
