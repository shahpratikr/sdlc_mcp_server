"""MCP server definition exposing workflow tools to the calling AI assistant."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from e2e_mcp_server.github_client import (
    create_pull_request,
    create_release,
    github_session,
)
from e2e_mcp_server.jira_client import (
    assign_story,
    create_feature,
    create_story,
    jira_session,
    list_sprints,
    schedule_story,
    set_story_estimate,
)
from e2e_mcp_server.test_runner import run_test_suite
from e2e_mcp_server.workflow_state import WorkflowState

if TYPE_CHECKING:
    from e2e_mcp_server.config import Config


def _create_git_branch(repository_path: str, branch_name: str) -> None:
    """Create a git branch via subprocess in the selected repository."""
    result = subprocess.run(  # noqa: S603
        ["git", "checkout", "-b", branch_name],  # noqa: S607
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = (
            f"Failed to create branch '{branch_name}' in '{repository_path}': "
            f"{result.stderr.strip()}"
        )
        raise RuntimeError(msg)


def _update_readme(repository_path: str, issue_key: str, summary: str) -> str:
    """Append a summary of implemented changes to the repository's README."""
    readme_path = Path(repository_path) / "README.md"
    existing_content = (
        readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    )
    entry = f"\n## {issue_key}\n\n{summary}\n"
    readme_path.write_text(existing_content + entry, encoding="utf-8")
    return str(readme_path)


def create_server(config: Config) -> FastMCP:
    """Build and return the MCP server instance for this run."""
    mcp_server = FastMCP("e2e-developer-workflow")
    workflow_state = WorkflowState()  #: per-run in-memory approval-gate state

    @mcp_server.tool()
    def ping() -> str:
        """Health-check tool confirming the server is running and connectable."""
        return "pong"

    @mcp_server.tool()
    async def create_feature_from_problem_statement(
        problem_statement: str,
        project_key: str,
    ) -> str:
        """Create a Jira Feature from a problem statement in the given project."""
        async with jira_session(config) as session:
            return await create_feature(session, project_key, problem_statement)

    @mcp_server.tool()
    async def refine_feature_into_stories(
        project_key: str,
        feature_key: str,
        summary: str,
        description: str,
    ) -> str:
        """Refine a Jira Feature into a user story issue."""
        async with jira_session(config) as session:
            return await create_story(
                session,
                project_key,
                feature_key,
                summary,
                description,
            )

    @mcp_server.tool()
    async def estimate_story(issue_key: str, story_points: float) -> str:
        """Write a generated story point estimate to a user story."""
        async with jira_session(config) as session:
            return await set_story_estimate(session, issue_key, story_points)

    @mcp_server.tool()
    async def assign_story_to_developer(issue_key: str, assignee: str) -> str:
        """Assign a user story to a developer in Jira."""
        async with jira_session(config) as session:
            return await assign_story(session, issue_key, assignee)

    @mcp_server.tool()
    async def list_board_sprints(board_id: str) -> str:
        """Read board/sprint structure to confirm target sprint."""
        async with jira_session(config) as session:
            return await list_sprints(session, board_id)

    @mcp_server.tool()
    async def schedule_story_in_sprint(issue_key: str, sprint_id: str) -> str:
        """Schedule a user story into a sprint in Jira."""
        async with jira_session(config) as session:
            return await schedule_story(session, issue_key, sprint_id)

    @mcp_server.tool()
    def proceed(issue_key: str) -> str:
        """Explicitly approve the coding stage for a user story."""
        workflow_state.mark_proceed(issue_key)
        return f"Approved: coding stage unblocked for '{issue_key}'"

    @mcp_server.tool()
    def create_branch_for_story(
        issue_key: str,
        repository_path: str,
        branch_name: str,
    ) -> str:
        """Create a git branch for a story's implementation once approved."""
        workflow_state.require_approval(issue_key)
        _create_git_branch(repository_path, branch_name)
        return (
            f"Created branch '{branch_name}' in '{repository_path}' for '{issue_key}'"
        )

    _register_test_verification_tools(mcp_server, workflow_state)
    _register_pull_request_tools(mcp_server, workflow_state, config)
    _register_documentation_tools(mcp_server)
    _register_release_tools(mcp_server, config)

    return mcp_server


def _register_test_verification_tools(
    mcp_server: FastMCP,
    workflow_state: WorkflowState,
) -> None:
    """Register the test-run and override tools onto the server."""

    @mcp_server.tool()
    def run_tests_for_story(
        issue_key: str,
        repository_path: str,
        test_command: str,
    ) -> str:
        """Run the test suite for a story and report pass/fail results."""
        result = run_test_suite(repository_path, test_command)
        workflow_state.record_test_result(issue_key, passed=result.passed)
        status = "PASSED" if result.passed else "FAILED"
        return f"Tests {status} for '{issue_key}'\n{result.output}"

    @mcp_server.tool()
    def override_failed_tests(issue_key: str) -> str:
        """Explicitly override a failed test run to unblock PR creation."""
        workflow_state.mark_test_override(issue_key)
        return f"Test failure override recorded for '{issue_key}'"


def _register_pull_request_tools(
    mcp_server: FastMCP,
    workflow_state: WorkflowState,
    config: Config,
) -> None:
    """Register the PR-creation tool onto the server."""

    @mcp_server.tool()
    async def create_pull_request_for_story(
        issue_key: str,
        repository: str,
        head_branch: str,
        base_branch: str,
        title: str,
    ) -> str:
        """Create a GitHub PR for a story once tests pass, linked to Jira."""
        workflow_state.require_tests_passed(issue_key)
        async with github_session(config) as session:
            return await create_pull_request(
                session,
                repository,
                head_branch,
                base_branch,
                issue_key,
                title,
            )


def _register_documentation_tools(mcp_server: FastMCP) -> None:
    """Register the README update tool onto the server."""

    @mcp_server.tool()
    def update_readme_for_story(
        issue_key: str,
        repository_path: str,
        summary: str,
    ) -> str:
        """Update the repository's README to reflect a story's changes."""
        readme_path = _update_readme(repository_path, issue_key, summary)
        return f"Updated '{readme_path}' with changes for '{issue_key}'"


def _register_release_tools(mcp_server: FastMCP, config: Config) -> None:
    """Register the GitHub Release-creation tool onto the server."""

    @mcp_server.tool()
    async def create_release_for_completed_work(
        repository: str,
        tag_name: str,
        release_notes: str,
    ) -> str:
        """Create a GitHub Release (tag + notes) for completed work."""
        async with github_session(config) as session:
            return await create_release(session, repository, tag_name, release_notes)


def run_server(config: Config) -> None:
    """Start the MCP server for this run using the given configuration."""
    server = create_server(config)
    server.run()
