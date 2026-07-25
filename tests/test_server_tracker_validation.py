"""Tests for tracker-argument validation helpers in server.py. PRD §3.1-§3.3."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    jira_api_token="jira-token",  # noqa: S106
)


def test_start_feature_rejects_unknown_tracker():
    server = create_server(TEST_CONFIG)

    async def _run():
        with pytest.raises(Exception, match="tracker must be one of"):
            await server.call_tool(
                "start_feature",
                {
                    "problem_statement": "Users need faster checkout",
                    "tracker": "gitlab",
                    "project_key": "PROJ",
                },
            )

    asyncio.run(_run())


def test_start_feature_rejects_github_only_argument_for_jira():
    server = create_server(TEST_CONFIG)

    async def _run():
        with pytest.raises(Exception, match="does not accept"):
            await server.call_tool(
                "start_feature",
                {
                    "problem_statement": "Users need faster checkout",
                    "tracker": "jira",
                    "project_key": "PROJ",
                    "repo_owner": "improving",
                    "repo_name": "widgets",
                },
            )

    asyncio.run(_run())


def test_start_feature_requires_project_key_for_jira():
    server = create_server(TEST_CONFIG)

    async def _run():
        with (
            patch(
                "e2e_mcp_server.server.generate_feature_acceptance_criteria",
                AsyncMock(return_value="- AC one"),
            ),
            pytest.raises(Exception, match="requires argument"),
        ):
            await server.call_tool(
                "start_feature",
                {
                    "problem_statement": "Users need faster checkout",
                    "tracker": "jira",
                },
            )

    asyncio.run(_run())
