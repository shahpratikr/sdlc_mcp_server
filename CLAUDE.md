# E2E Developer Workflow MCP Server

@docs/PRD.md
@docs/ARCHITECTURE.md

## Commands

- `poetry install` — install dependencies
- `poetry run python -m e2e_mcp_server` — start the MCP server (Typer entry point via `__main__.py`)
- `poetry run pytest` — run test suite (if configured)

## Conventions

- Folder structure: `src/e2e_mcp_server/` contains `__init__.py`, `__main__.py`, `server.py`, `config.py`, `jira_client.py`, `workflow_state.py`
- `__main__.py` is the Typer CLI entry point; loads config from environment variables via `config.py`, then starts the MCP server defined in `server.py`
- All credentials supplied via environment variables only; never stored in code or config files
- Jira accessed exclusively via its official MCP server as a child process; never via direct REST API calls
- Child server URL configurable via env var: `JIRA_MCP_URL` (not hardcoded)
- Repository path and Jira project selected per run (passed as tool arguments), not fixed at server startup
- Workflow state (approval gates, per-story proceed flags) tracked in-process memory via `workflow_state.py`; no persistent storage or database
- Git branch creation via subprocess; no sandboxing in v1
- MCP tools organized by feature phase matching PRD §3.x sections
- Code generation delegated entirely to calling AI assistant; server orchestrates workflow only
- Explicit `proceed` MCP tool enforces approval gate; blocks coding-stage tools until called per story
- Pipeline ends at implementation branch creation; test execution, PR creation, documentation, and release are out of scope for v1

## Constraints

- Never persist credentials to disk; environment variables are the exclusive credential source
- Never generate, modify, or create source code in the server (orchestration and delegation only)
- Never make direct REST API calls to Jira; always use the child MCP server
- Per-run configuration only; no multi-repo or multi-project orchestration within a single run
- Single-developer, locally-hosted execution model; no shared or centralized deployment
