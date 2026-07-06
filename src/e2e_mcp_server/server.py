"""MCP server definition exposing workflow tools to the calling AI assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from e2e_mcp_server.jira_client import create_feature, jira_session

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

    return mcp_server


def run_server(config: Config) -> None:
    """Start the MCP server for this run using the given configuration."""
    server = create_server(config)
    server.run()
