"""Tests for the Phase 4 generate_stories_for_feature tool. See ARCHITECTURE Phase 4."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    jira_api_token="jira-token",  # noqa: S106
)
_EXPECTED_STORY_COUNT = 2


def _result_text(result):
    content = result[0]
    return content[0].text if isinstance(content, list) else content.content[0].text


def test_generate_stories_rejects_unapproved_feature():
    server = create_server(TEST_CONFIG)

    async def _run():
        with pytest.raises(Exception, match="approval gate"):
            await server.call_tool(
                "generate_stories_for_feature",
                {"feature_key": "PROJ-1", "board": "Board 1", "sprint": "Sprint 1"},
            )

    asyncio.run(_run())


def test_generate_stories_creates_estimates_and_schedules_all_stories():
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
                "e2e_mcp_server.server.get_feature_acceptance_criteria",
                AsyncMock(return_value="- feature AC"),
            ),
            patch(
                "e2e_mcp_server.server.generate_user_stories",
                AsyncMock(return_value=["Story A", "Story B"]),
            ),
            patch(
                "e2e_mcp_server.server.generate_story_acceptance_criteria_and_estimate",
                AsyncMock(side_effect=[("- AC A", 2), ("- AC B", 5)]),
            ),
            patch(
                "e2e_mcp_server.server.create_story",
                AsyncMock(side_effect=["PROJ-2", "PROJ-3"]),
            ),
            patch(
                "e2e_mcp_server.server.update_story_estimate_and_acceptance_criteria",
                AsyncMock(),
            ) as fake_update,
            patch(
                "e2e_mcp_server.server.schedule_story_into_sprint",
                AsyncMock(),
            ) as fake_schedule,
            patch("e2e_mcp_server.server.assign_story", AsyncMock()) as fake_assign,
        ):
            # Approve the Stage 1 gate first via the real approval tool.
            with patch(
                "e2e_mcp_server.server.update_feature_acceptance_criteria",
                AsyncMock(),
            ):
                await server.call_tool(
                    "approve_feature_acceptance_criteria",
                    {"feature_key": "PROJ-1"},
                )

            result = await server.call_tool(
                "generate_stories_for_feature",
                {
                    "feature_key": "PROJ-1",
                    "board": "Board 1",
                    "sprint": "Sprint 1",
                    "assignee": "dev@example.com",
                },
            )

            assert fake_update.await_count == _EXPECTED_STORY_COUNT
            assert fake_schedule.await_count == _EXPECTED_STORY_COUNT
            assert fake_assign.await_count == _EXPECTED_STORY_COUNT
            return result

    result = asyncio.run(_run())
    text = _result_text(result)
    assert "PROJ-2" in text
    assert "PROJ-3" in text
    assert "- AC A" in text


def test_generate_stories_skips_assignment_when_not_supplied():
    server = create_server(TEST_CONFIG)
    fake_session = object()

    @asynccontextmanager
    async def _fake_jira_session(config):
        yield fake_session

    async def _run():
        with (
            patch("e2e_mcp_server.server.jira_session", _fake_jira_session),
            patch(
                "e2e_mcp_server.server.get_feature_acceptance_criteria",
                AsyncMock(return_value="- feature AC"),
            ),
            patch(
                "e2e_mcp_server.server.generate_user_stories",
                AsyncMock(return_value=["Story A"]),
            ),
            patch(
                "e2e_mcp_server.server.generate_story_acceptance_criteria_and_estimate",
                AsyncMock(return_value=("- AC A", 2)),
            ),
            patch(
                "e2e_mcp_server.server.create_story",
                AsyncMock(return_value="PROJ-2"),
            ),
            patch(
                "e2e_mcp_server.server.update_story_estimate_and_acceptance_criteria",
                AsyncMock(),
            ),
            patch("e2e_mcp_server.server.schedule_story_into_sprint", AsyncMock()),
            patch("e2e_mcp_server.server.assign_story", AsyncMock()) as fake_assign,
            patch(
                "e2e_mcp_server.server.update_feature_acceptance_criteria",
                AsyncMock(),
            ),
        ):
            await server.call_tool(
                "approve_feature_acceptance_criteria",
                {"feature_key": "PROJ-1"},
            )
            await server.call_tool(
                "generate_stories_for_feature",
                {"feature_key": "PROJ-1", "board": "Board 1", "sprint": "Sprint 1"},
            )
            fake_assign.assert_not_called()

    asyncio.run(_run())
