"""MCP server definition exposing workflow tools to the calling AI assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from e2e_mcp_server.jira_client import (
    assign_story,
    create_feature,
    create_story,
    jira_session,
    list_sprints,
    schedule_story,
    set_story_estimate,
)

if TYPE_CHECKING:
    from e2e_mcp_server.config import Config


def create_server(config: Config) -> FastMCP:
    """Build and return the MCP server instance for this run."""
    mcp_server = FastMCP("e2e-developer-workflow")

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

    return mcp_server


def run_server(config: Config) -> None:
    """Start the MCP server for this run using the given configuration."""
    server = create_server(config)
    server.run()
