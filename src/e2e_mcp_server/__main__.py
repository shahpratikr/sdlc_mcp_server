from __future__ import annotations

import sys

import typer

from e2e_mcp_server.config import ConfigError, load_config
from e2e_mcp_server.server import run_server

app = typer.Typer(add_completion=False)


@app.command()
def start() -> None:
    """Start the E2E Developer Workflow MCP server."""
    try:
        config = load_config()
    except ConfigError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    run_server(config)


def main() -> None:
    """Module entry point invoked via `python -m e2e_mcp_server`."""
    app()


if __name__ == "__main__":
    sys.exit(main())
