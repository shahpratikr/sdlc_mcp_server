from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from e2e_mcp_server.config import Config


def create_server(config: Config) -> FastMCP:
    """Build and return the MCP server instance for this run."""
    mcp_server = FastMCP("e2e-developer-workflow")

    @mcp_server.tool()
    def ping() -> str:
        """Health-check tool confirming the server is running and connectable."""
        return "pong"

    return mcp_server


def run_server(config: Config) -> None:
    """Start the MCP server for this run using the given configuration."""
    server = create_server(config)
    server.run()
