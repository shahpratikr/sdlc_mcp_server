"""Tests for the Phase 1 MCP server scaffold. docs/ARCHITECTURE.md Phase 1."""

import asyncio
import os
import subprocess
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server, run_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    github_mcp_url="http://localhost:9002/mcp",
    jira_api_token="jira-token",  # noqa: S106
    github_token="github-token",  # noqa: S106
)


def test_create_server_returns_fastmcp_instance():
    server = create_server(TEST_CONFIG)
    assert isinstance(server, FastMCP)


def test_server_exposes_ping_tool():
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert "ping" in tool_names


def test_ping_tool_returns_pong():
    server = create_server(TEST_CONFIG)

    async def _call_ping():
        return await server.call_tool("ping", {})

    result = asyncio.run(_call_ping())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert text == "pong"


def test_server_exposes_create_feature_from_problem_statement_tool():
    """PRD §3.1: server exposes a tool to create a Jira Feature."""
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert "create_feature_from_problem_statement" in tool_names


def test_create_feature_from_problem_statement_delegates_to_jira_client():
    server = create_server(TEST_CONFIG)
    fake_session = AsyncMock()

    @asynccontextmanager
    async def _fake_jira_session(config):
        yield fake_session

    async def _call():
        with (
            patch("e2e_mcp_server.server.jira_session", _fake_jira_session),
            patch(
                "e2e_mcp_server.server.create_feature",
                AsyncMock(return_value="PROJ-1"),
            ) as fake_create_feature,
        ):
            result = await server.call_tool(
                "create_feature_from_problem_statement",
                {"problem_statement": "Users can't log in", "project_key": "PROJ"},
            )
            fake_create_feature.assert_awaited_once_with(
                fake_session,
                "PROJ",
                "Users can't log in",
            )
            return result

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert text == "PROJ-1"


def test_server_exposes_phase_3_tools():
    """PRD §3.2: server exposes refinement/estimation/assignment/scheduling tools."""
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert {
        "refine_feature_into_stories",
        "estimate_story",
        "assign_story_to_developer",
        "list_board_sprints",
        "schedule_story_in_sprint",
    }.issubset(tool_names)


def _run_tool_delegation_test(
    tool_name,
    args,
    patch_target,
    expected_args,
    return_value,
):
    server = create_server(TEST_CONFIG)
    fake_session = AsyncMock()

    @asynccontextmanager
    async def _fake_jira_session(config):
        yield fake_session

    async def _call():
        with (
            patch("e2e_mcp_server.server.jira_session", _fake_jira_session),
            patch(
                f"e2e_mcp_server.server.{patch_target}",
                AsyncMock(return_value=return_value),
            ) as fake_fn,
        ):
            result = await server.call_tool(tool_name, args)
            fake_fn.assert_awaited_once_with(fake_session, *expected_args)
            return result

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert text == return_value


def test_refine_feature_into_stories_delegates_to_jira_client():
    _run_tool_delegation_test(
        "refine_feature_into_stories",
        {
            "project_key": "PROJ",
            "feature_key": "PROJ-1",
            "summary": "Story summary",
            "description": "Story description",
        },
        "create_story",
        ("PROJ", "PROJ-1", "Story summary", "Story description"),
        "PROJ-2",
    )


def test_estimate_story_delegates_to_jira_client():
    _run_tool_delegation_test(
        "estimate_story",
        {"issue_key": "PROJ-2", "story_points": 3.0},
        "set_story_estimate",
        ("PROJ-2", 3.0),
        "PROJ-2",
    )


def test_assign_story_to_developer_delegates_to_jira_client():
    _run_tool_delegation_test(
        "assign_story_to_developer",
        {"issue_key": "PROJ-2", "assignee": "jdoe"},
        "assign_story",
        ("PROJ-2", "jdoe"),
        "PROJ-2",
    )


def test_list_board_sprints_delegates_to_jira_client():
    _run_tool_delegation_test(
        "list_board_sprints",
        {"board_id": "1"},
        "list_sprints",
        ("1",),
        "[]",
    )


def test_schedule_story_in_sprint_delegates_to_jira_client():
    _run_tool_delegation_test(
        "schedule_story_in_sprint",
        {"issue_key": "PROJ-2", "sprint_id": "10"},
        "schedule_story",
        ("PROJ-2", "10"),
        "PROJ-2",
    )


def test_server_exposes_proceed_tool():
    """Server exposes an explicit 'proceed' approval-gate tool."""
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert "proceed" in tool_names


def test_proceed_tool_approves_the_story():
    server = create_server(TEST_CONFIG)

    async def _call():
        return await server.call_tool("proceed", {"issue_key": "PROJ-2"})

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert "PROJ-2" in text


def test_server_exposes_create_branch_for_story_tool():
    """PRD §3.4: server exposes a tool to create a git branch for a story."""
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert "create_branch_for_story" in tool_names


def test_create_branch_for_story_blocked_without_proceed(tmp_path):
    """PRD §3.3/§3.4: coding stage (branch creation) is blocked until 'proceed'."""
    subprocess.run(  # noqa: S603
        ["git", "init", str(tmp_path)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    server = create_server(TEST_CONFIG)

    async def _call():
        return await server.call_tool(
            "create_branch_for_story",
            {
                "issue_key": "PROJ-2",
                "repository_path": str(tmp_path),
                "branch_name": "feature/proj-2",
            },
        )

    with pytest.raises(ToolError, match="PROJ-2") as exc_info:
        asyncio.run(_call())
    assert "proceed" in str(exc_info.value)


def test_create_branch_for_story_creates_branch_after_proceed(tmp_path):
    """PRD §3.4: create a git branch in the selected repository once approved."""
    subprocess.run(  # noqa: S603
        ["git", "init", str(tmp_path)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],  # noqa: S607
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )
    server = create_server(TEST_CONFIG)

    async def _call():
        await server.call_tool("proceed", {"issue_key": "PROJ-2"})
        return await server.call_tool(
            "create_branch_for_story",
            {
                "issue_key": "PROJ-2",
                "repository_path": str(tmp_path),
                "branch_name": "feature/proj-2",
            },
        )

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert "feature/proj-2" in text

    branch_check = subprocess.run(
        ["git", "branch", "--show-current"],  # noqa: S607
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert branch_check.stdout.strip() == "feature/proj-2"


def test_server_exposes_test_verification_tools():
    """PRD §3.5: server exposes tools to run tests and override a failed run."""
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert {"run_tests_for_story", "override_failed_tests"}.issubset(tool_names)


def test_run_tests_for_story_reports_pass(tmp_path):
    """PRD §3.5: passing test run is reported back to the calling AI assistant."""
    server = create_server(TEST_CONFIG)

    async def _call():
        return await server.call_tool(
            "run_tests_for_story",
            {
                "issue_key": "PROJ-2",
                "repository_path": str(tmp_path),
                "test_command": "true",
            },
        )

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert "PASSED" in text
    assert "PROJ-2" in text


def test_run_tests_for_story_reports_failure(tmp_path):
    """PRD §3.5: failing test run is reported back to the calling AI assistant."""
    server = create_server(TEST_CONFIG)

    async def _call():
        return await server.call_tool(
            "run_tests_for_story",
            {
                "issue_key": "PROJ-2",
                "repository_path": str(tmp_path),
                "test_command": "false",
            },
        )

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert "FAILED" in text


def test_override_failed_tests_unblocks_pr_gate(tmp_path):
    """PRD §3.5: explicit override records unblock for a story's failed run."""
    server = create_server(TEST_CONFIG)

    async def _call():
        await server.call_tool(
            "run_tests_for_story",
            {
                "issue_key": "PROJ-2",
                "repository_path": str(tmp_path),
                "test_command": "false",
            },
        )
        return await server.call_tool("override_failed_tests", {"issue_key": "PROJ-2"})

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert "PROJ-2" in text


def test_server_exposes_create_pull_request_for_story_tool():
    """PRD §3.6: server exposes a tool to create a GitHub PR for a story."""
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert "create_pull_request_for_story" in tool_names


def test_create_pull_request_for_story_delegates_to_github_client():
    """PRD §3.6: PR is created via the GitHub MCP server once tests pass."""
    server = create_server(TEST_CONFIG)
    fake_session = AsyncMock()

    @asynccontextmanager
    async def _fake_github_session(config):
        yield fake_session

    async def _call():
        await server.call_tool(
            "run_tests_for_story",
            {
                "issue_key": "PROJ-2",
                "repository_path": ".",
                "test_command": "true",
            },
        )
        with (
            patch("e2e_mcp_server.server.github_session", _fake_github_session),
            patch(
                "e2e_mcp_server.server.create_pull_request",
                AsyncMock(return_value="PR created: #7"),
            ) as fake_create_pr,
        ):
            result = await server.call_tool(
                "create_pull_request_for_story",
                {
                    "issue_key": "PROJ-2",
                    "repository": "org/repo",
                    "head_branch": "feature/proj-2",
                    "base_branch": "main",
                    "title": "Implement PROJ-2",
                },
            )
            fake_create_pr.assert_awaited_once_with(
                fake_session,
                "org/repo",
                "feature/proj-2",
                "main",
                "PROJ-2",
                "Implement PROJ-2",
            )
        return result

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert "PR created" in text


def test_create_pull_request_for_story_blocked_when_tests_failed():
    """PRD §3.5/§3.6: PR creation is blocked after a failed, non-overridden test run."""
    server = create_server(TEST_CONFIG)

    async def _call():
        await server.call_tool(
            "run_tests_for_story",
            {
                "issue_key": "PROJ-3",
                "repository_path": ".",
                "test_command": "false",
            },
        )
        return await server.call_tool(
            "create_pull_request_for_story",
            {
                "issue_key": "PROJ-3",
                "repository": "org/repo",
                "head_branch": "feature/proj-3",
                "base_branch": "main",
                "title": "Implement PROJ-3",
            },
        )

    with pytest.raises(ToolError):
        asyncio.run(_call())


def test_run_server_builds_and_runs_the_server():
    with patch("e2e_mcp_server.server.FastMCP") as fake_fastmcp_cls:
        fake_server = fake_fastmcp_cls.return_value
        run_server(TEST_CONFIG)
        fake_server.run.assert_called_once_with()


def test_server_exposes_update_readme_for_story_tool():
    """PRD §3.7: server exposes a tool to update the README."""
    server = create_server(TEST_CONFIG)

    async def _list_tools():
        return await server.list_tools()

    tools = asyncio.run(_list_tools())
    tool_names = {tool.name for tool in tools}
    assert "update_readme_for_story" in tool_names


def test_update_readme_for_story_creates_readme_when_missing(tmp_path):
    """PRD §3.7: README is created and reflects the implemented changes."""
    server = create_server(TEST_CONFIG)

    async def _call():
        return await server.call_tool(
            "update_readme_for_story",
            {
                "issue_key": "PROJ-4",
                "repository_path": str(tmp_path),
                "summary": "Added the new login flow.",
            },
        )

    result = asyncio.run(_call())
    content = result[0]
    text = content[0].text if isinstance(content, list) else content.content[0].text
    assert "PROJ-4" in text

    readme_content = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "## PROJ-4" in readme_content
    assert "Added the new login flow." in readme_content


def test_update_readme_for_story_appends_to_existing_readme(tmp_path):
    """PRD §3.7: existing README content is preserved and appended to."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Project\n", encoding="utf-8")
    server = create_server(TEST_CONFIG)

    async def _call():
        return await server.call_tool(
            "update_readme_for_story",
            {
                "issue_key": "PROJ-5",
                "repository_path": str(tmp_path),
                "summary": "Fixed the logout bug.",
            },
        )

    asyncio.run(_call())

    readme_content = readme_path.read_text(encoding="utf-8")
    assert readme_content.startswith("# My Project\n")
    assert "## PROJ-5" in readme_content
    assert "Fixed the logout bug." in readme_content
