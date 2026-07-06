# ARCHITECTURE.md — E2E Developer Workflow MCP Server

## Decision

Build a locally-hosted Python MCP server (`e2e_mcp_server`) using the official MCP Python SDK, packaged and dependency-managed with Poetry, started via a Typer CLI entry point. The server acts as both an MCP server (exposing workflow tools to the calling AI assistant) and an MCP client (calling out to the official Jira and GitHub MCP servers as configurable child servers). No database or persistent storage is used; all run state (selected repo, Jira project, per-story approval-gate flags) lives in in-process memory for the duration of a run. Code generation itself is delegated entirely to the calling AI assistant.

## Folder Tree

```
e2e_mcp_server/
  docs/
    PRD.md
    ARCHITECTURE.md
  src/
    e2e_mcp_server/
      __init__.py
      __main__.py       # Typer app; starts the server
      server.py
      config.py
      jira_client.py
      github_client.py
      workflow_state.py
      test_runner.py
  pyproject.toml
  README.md
```

`__main__.py` holds the Typer app directly (no separate `cli.py`): it loads config via `config.py`, then starts the MCP server defined in `server.py`. Started with `poetry run python -m e2e_mcp_server`; no separate Poetry script entry point is defined.

## Rationale

- **Python + official MCP SDK**: mandated by PRD §7 ("chosen for team familiarity and debuggability; primary developer is a Python developer").
- **Poetry as package manager**: user preference; changes only how `pyproject.toml` is structured (`[tool.poetry]` sections, `poetry.lock`) and how dependencies/scripts are installed/run. No effect on runtime architecture.
- **Typer for the CLI entry point**: user preference for starting the server process (`poetry run e2e-mcp-server`); PRD §6/§8 require the server run as a locally-hosted process configured via environment variables, and Typer provides the command that boots it, wires config loading, and surfaces startup errors (e.g., missing required env vars) with a clear exit rather than a raw traceback. No effect on the MCP tool surface itself, since MCP tool definitions are separate from the process boot command.
- **No database**: PRD §8 explicitly states "no shared state or multi-user coordination in v1," and §3.1/§3.2 imply Jira itself is the system of record for features/stories/estimates/assignments/sprints. Persisting a duplicate copy locally would violate the single-tenant, stateless-orchestrator model.
- **Jira and GitHub accessed only via their official MCP servers, never direct REST calls**: PRD §6 constrains authentication to "existing/official Jira and GitHub MCP servers," and §7 requires these be "connected as configurable child MCP servers" with URLs/endpoints overridable via environment variables (also NFR in §4 Configurability).
- **`subprocess` for git branch creation and test execution**: required directly by §3.4 (git branch per user story) and §3.5 (execute the project's test suite locally); no sandboxing per §5/§8 (explicitly out of scope for v1).
- **Explicit `workflow_state.py` in-memory tracking of the "proceed" flag per story**: required by §3.3, which mandates the approval gate be an explicit MCP tool call, not a UI element or Jira status transition (§8).
- **Repository and Jira project selected per run, not fixed at startup**: PRD §3.1, §3.4, §8 (per-run selection, not per-instance fixed).
- **Credentials via environment variables only, never persisted to disk**: PRD §4 (Security NFR) and §6 (Constraints).
- **Single Claude-only assistant target (Sonnet/Haiku)**: PRD §6, aligned with Improving's Third-Party Service Use Policy; no code in this server needs to special-case other assistants since MCP is the interface boundary.

## Rejected Options

- **TypeScript/Node MCP SDK**: rejected. PRD §7 explicitly locks the language choice to Python for team familiarity; no PRD requirement favors Node's ecosystem here.
- **Persisting workflow state to a local SQLite/file-based store**: rejected. PRD §8 rules out shared/persistent state for v1; Jira is the durable system of record for story data, so a local duplicate would only introduce a synchronization-drift risk with no corresponding requirement driving it.
- **Direct Jira/GitHub REST API calls instead of their MCP servers**: rejected. PRD §6 and §7 explicitly require going through the official Jira and GitHub MCP servers as child servers, not direct API integration, to keep credential handling and endpoint configuration consistent with the MCP architecture.
- **Containerized/sandboxed test execution**: rejected. PRD §5 lists this as explicitly out of scope for v1; §10 documents this as a deliberate, revisitable assumption, not an oversight.
- **pip + `requirements.txt` or plain setuptools**: rejected in favor of Poetry per explicit user preference. Poetry's lockfile and `[tool.poetry]` metadata replace these without changing any runtime architecture decision above.
- **Plain `argparse` or bare `if __name__ == "__main__"` startup script**: rejected in favor of Typer per explicit user preference. Both would satisfy §6/§8's "runs as a locally-hosted process" requirement, but Typer was the user's chosen entry point mechanism.

## Risks

- **Availability/version drift of official Jira and GitHub MCP servers**: since this server is a thin orchestrator on top of them, any breaking change in their tool schemas breaks this server's Jira/GitHub client wrappers. Mitigate by pinning known-compatible versions/endpoints via env var config.
- **Unsandboxed local test execution (§10 documented assumption)**: a malicious or broken test suite runs with the developer's full local privileges. Accepted as a v1 tradeoff per PRD; revisit if it proves unsafe.
- **In-memory-only state loss on crash**: if the server process crashes mid-run (e.g., after Jira stories are created but before the "proceed" gate), there is no persisted run state to resume from; the developer would need to re-drive remaining steps manually. Acceptable for a single-developer local tool per PRD's single-tenant model, but worth surfacing to the user as a known limitation.
- **Secrets in environment variables**: while compliant with PRD §4/§6, env vars can still leak via process listing or crash dumps on some systems; standard OS-level environment hygiene is the developer's responsibility, not enforced by this server.

## Phase Plan

Grouping unit: **feature group**, following the PRD's own §3.x feature numbering, since each is independently describable, independently testable via its own MCP tool calls, and maps to the PRD's structure directly.

- **Phase 1 — Foundation**: MCP server scaffold (`server.py`), config loading from env vars (`config.py`), and connection wiring to the Jira and GitHub child MCP servers (no tools with business logic yet — just a running, connectable server). Independently runnable: server starts, accepts a connection, and can be pinged.
- **Phase 2 — Feature Creation (§3.1)**: Tool to accept a problem statement and create a Jira Feature via the Jira MCP server, with per-run project selection.
- **Phase 3 — Refinement, Estimation, Assignment, Scheduling (§3.2)**: Tools to refine a Feature into stories, estimate story points, write estimates to Jira, assign developers, and schedule into a sprint.
- **Phase 4 — Approval Gate (§3.3)**: `proceed` tool and `workflow_state.py` gate enforcement blocking coding-stage tools until called for a given story.
- **Phase 5 — Coding Support (§3.4)**: Git branch creation per user story in the per-run selected repository (code generation itself remains delegated to the calling assistant, no server-side implementation).
- **Phase 6 — Test Verification (§3.5)**: Local test suite execution, pass/fail reporting back to the assistant, and PR-creation blocking on failure (with explicit override).
- **Phase 7 — Pull Request Creation (§3.6)**: GitHub PR creation via the GitHub MCP server, linked back to the originating Jira story.
- **Phase 8 — Documentation (§3.7)**: README update tool reflecting implemented changes.
- **Phase 9 — Release (§3.8)**: GitHub Release (tag + notes) creation for completed work.
