"""Tests for the Phase 7 create_implementation_branch tool. PRD §3.6."""

# ruff: noqa: S607

import asyncio
import subprocess

import pytest

from e2e_mcp_server.config import Config
from e2e_mcp_server.server import create_server

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    jira_api_token="jira-token",  # noqa: S106
)


def _result_text(result):
    content = result[0]
    return content[0].text if isinstance(content, list) else content.content[0].text


def _init_repo(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    (repo_path / "README.md").write_text("init")
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    return repo_path


def test_create_implementation_branch_requires_proceed(tmp_path):
    server = create_server(TEST_CONFIG)
    repo_path = _init_repo(tmp_path)

    with pytest.raises(Exception, match="approval gate"):
        asyncio.run(
            server.call_tool(
                "create_implementation_branch",
                {"story_key": "PROJ-2", "repository_path": str(repo_path)},
            ),
        )


def test_create_implementation_branch_creates_branch_after_proceed(tmp_path):
    server = create_server(TEST_CONFIG)
    repo_path = _init_repo(tmp_path)

    asyncio.run(server.call_tool("proceed", {"story_key": "PROJ-2"}))
    result = asyncio.run(
        server.call_tool(
            "create_implementation_branch",
            {"story_key": "PROJ-2", "repository_path": str(repo_path)},
        ),
    )
    text = _result_text(result)
    assert "story/proj-2" in text
    assert "created" in text

    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert branch == "story/proj-2"
