# E2E Developer Workflow MCP Server

@docs/PRD.md
@docs/ARCHITECTURE.md

## Commands

- `poetry install` — install dependencies
- `poetry run python -m e2e_mcp_server` — start the MCP server (Typer entry point via `__main__.py`)
- `poetry run pytest` — run test suite

## Conventions

- Folder structure: `src/e2e_mcp_server/` contains `__init__.py`, `__main__.py`, `server.py`, `config.py`, `jira_client.py`, `github_client.py`, `content_generation.py`, `workflow_state.py`
- `__main__.py` is the Typer CLI entry point; loads config from environment variables via `config.py`, then starts the MCP server defined in `server.py`
- All credentials supplied via environment variables only; never stored in code or config files
- Jira and GitHub Issues accessed exclusively via their official MCP servers as child processes; never via direct REST API calls
- Child server URLs configurable via env vars: `JIRA_MCP_URL`, `GITHUB_MCP_URL` (not hardcoded); GitHub URLs/credentials optional until a call uses `tracker: github`
- Every Stage 1/2/3 tool has a `tracker` argument (`"jira"` or `"github"`), selected per tool call, not fixed at startup
- Repository path selected per run (passed as tool argument), not fixed at server startup
- Tracker target (Jira project key or GitHub repo owner/name) selected per run and per tool call (tracker-specific arguments validated against the `tracker` argument)
- Workflow state (approval gates, per-story proceed flags, tracker ownership of each identifier) tracked in-process memory via `workflow_state.py`; no persistent storage or database
- Content generation helpers in `content_generation.py` use MCP sampling to delegate AC/story/estimate generation to the connected AI assistant
- Git branch creation via subprocess; no sandboxing in v1
- MCP tools organized by feature phase matching PRD §3.x sections
- Code generation delegated entirely to calling AI assistant; server orchestrates workflow only

## Constraints

- Never persist credentials to disk; environment variables are the exclusive credential source
- Never generate, modify, or create source code in the server (orchestration and delegation only)
- Never make direct REST API calls to Jira or GitHub; always use their official child MCP servers
- Per-run configuration only; no multi-repo/multi-project orchestration within a single run
- One tracker (Jira or GitHub) per tool call, not both simultaneously in one run
- Single-developer, locally-hosted execution model; no shared or centralized deployment
