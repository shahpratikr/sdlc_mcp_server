"""Tests for the Phase 2 start_feature tool. docs/ARCHITECTURE.md Phase 2."""

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


def test_start_feature_generates_ac_and_creates_jira_feature():
    server = create_server(TEST_CONFIG)
    fake_session = object()

    @asynccontextmanager
    async def _fake_jira_session(config):
        assert config is TEST_CONFIG
        yield fake_session

    async def _run():
        with (
            patch(
                "e2e_mcp_server.server.generate_feature_acceptance_criteria",
                AsyncMock(return_value="- AC one\n- AC two"),
            ) as fake_generate,
            patch("e2e_mcp_server.server.jira_session", _fake_jira_session),
            patch(
                "e2e_mcp_server.server.create_feature",
                AsyncMock(return_value="PROJ-42"),
            ) as fake_create_feature,
        ):
            result = await server.call_tool(
                "start_feature",
                {
                    "problem_statement": "Users need faster checkout",
                    "project_key": "PROJ",
                },
            )
            fake_generate.assert_awaited_once()
            assert fake_generate.await_args.args[1] == "Users need faster checkout"
            fake_create_feature.assert_awaited_once_with(
                fake_session,
                "PROJ",
                "Users need faster checkout",
                "- AC one\n- AC two",
            )
            return result

    result = asyncio.run(_run())
    text = _result_text(result)
    assert "PROJ-42" in text
    assert "AC one" in text
