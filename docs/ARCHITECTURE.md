# ARCHITECTURE.md — E2E Developer Workflow MCP Server

## Decision

Build a locally-hosted Python MCP server (`e2e_mcp_server`) using the official MCP Python SDK, packaged and dependency-managed with Poetry, started via a Typer CLI entry point. The server acts as both an MCP server (exposing workflow tools to the calling AI assistant) and an MCP client (calling out to the official Jira MCP server as a configurable child server). No database or persistent storage is used; all run state (selected repo, Jira project, per-feature/per-story approval-gate flags) lives in in-process memory for the duration of a run. Code generation itself is delegated entirely to the calling AI assistant.

Feature-level and story-level content generation (acceptance criteria, story splitting, story point estimates) is delegated to the connected AI assistant as well, but without requiring the developer to manually invoke a separate generation tool call per artifact. The server does this using the MCP **sampling** capability: a tool handler running inside the server can call `ctx.session.create_message(...)` to ask the connected client (the AI assistant) to generate a completion mid-call, then use that text to populate the Jira Feature/stories before returning. This lets Stage 1 (`start_feature`) and Stage 2 (`generate_stories_for_feature`) each do "generate content, then call Jira" inside one tool invocation, instead of the developer generating text themselves and passing it in as a tool argument on a separate call.

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
      content_generation.py  # sampling-based AC/story/estimate generation helpers
      workflow_state.py
  pyproject.toml
  README.md
```

`__main__.py` holds the Typer app directly (no separate `cli.py`): it loads config via `config.py`, then starts the MCP server defined in `server.py`. Started with `poetry run python -m e2e_mcp_server`; no separate Poetry script entry point is defined.

## Rationale

- **Python + official MCP SDK**: mandated by PRD §7 ("chosen for team familiarity and debuggability; primary developer is a Python developer").
- **Poetry as package manager**: user preference; changes only how `pyproject.toml` is structured (`[tool.poetry]` sections, `poetry.lock`) and how dependencies/scripts are installed/run. No effect on runtime architecture.
- **Typer for the CLI entry point**: user preference for starting the server process (`poetry run e2e-mcp-server`); PRD §6/§8 require the server run as a locally-hosted process configured via environment variables, and Typer provides the command that boots it, wires config loading, and surfaces startup errors (e.g., missing required env vars) with a clear exit rather than a raw traceback. No effect on the MCP tool surface itself, since MCP tool definitions are separate from the process boot command.
- **No database**: PRD §8 explicitly states "no shared state or multi-user coordination in v1," and §3.1/§3.2 imply Jira itself is the system of record for features/stories/estimates/assignments/sprints. Persisting a duplicate copy locally would violate the single-tenant, stateless-orchestrator model.
- **Jira accessed only via its official MCP server, never direct REST calls**: PRD §6 constrains authentication to the "existing/official Jira MCP server," and §7 requires it be "connected as a configurable child MCP server" with its URL/endpoint overridable via environment variables (also NFR in §4 Configurability).
- **`subprocess` for git branch creation**: required directly by §3.6 (git branch per user story); no sandboxing per §5/§8 (explicitly out of scope for v1).
- **Explicit `workflow_state.py` in-memory tracking of the "proceed" flag per story**: required by §3.3, which mandates the approval gate be an explicit MCP tool call, not a UI element or Jira status transition (§8).
- **Repository and Jira project selected per run, not fixed at startup**: PRD §3.1, §3.4, §8 (per-run selection, not per-instance fixed).
- **Credentials via environment variables only, never persisted to disk**: PRD §4 (Security NFR) and §6 (Constraints).
- **Single Claude-only assistant target (Sonnet/Haiku)**: PRD §6, aligned with Improving's Third-Party Service Use Policy; no code in this server needs to special-case other assistants since MCP is the interface boundary.
- **MCP sampling for Stage 1/2 content generation, rather than a per-artifact tool argument**: PRD §3.1/§3.3 require the developer to supply only a problem statement (plus project key) for Stage 1, and only a feature key/board/sprint for Stage 2 — the AC, story split, per-story AC, and estimates are generated inside the tool call itself, not passed in by the caller. Sampling is the only MCP-native way to do this without the server holding its own model credentials, which would conflict with §4/§6's environment-variable-only, no-independent-provider posture.
- **Two explicit approval-gate tools (Stage 1 AC approval, Stage 2 story-set approval), separate from the existing pre-coding `proceed` gate**: PRD §3.2 and §3.4 require the developer to review generated content (AC text, generated story set) before it becomes the basis for further Jira writes or coding, mirroring the same "explicit tool call, not a UI element or Jira status transition" pattern already established for the pre-coding gate in §3.5/§8.

## Rejected Options

- **TypeScript/Node MCP SDK**: rejected. PRD §7 explicitly locks the language choice to Python for team familiarity; no PRD requirement favors Node's ecosystem here.
- **Persisting workflow state to a local SQLite/file-based store**: rejected. PRD §8 rules out shared/persistent state for v1; Jira is the durable system of record for story data, so a local duplicate would only introduce a synchronization-drift risk with no corresponding requirement driving it.
- **Direct Jira REST API calls instead of its MCP server**: rejected. PRD §6 and §7 explicitly require going through the official Jira MCP server as a child server, not direct API integration, to keep credential handling and endpoint configuration consistent with the MCP architecture.
- **pip + `requirements.txt` or plain setuptools**: rejected in favor of Poetry per explicit user preference. Poetry's lockfile and `[tool.poetry]` metadata replace these without changing any runtime architecture decision above.
- **Plain `argparse` or bare `if __name__ == "__main__"` startup script**: rejected in favor of Typer per explicit user preference. Both would satisfy §6/§8's "runs as a locally-hosted process" requirement, but Typer was the user's chosen entry point mechanism.
- **Server-side LLM integration (server holds its own model API key and calls it directly to generate AC/stories/estimates)**: rejected. This would work without depending on client sampling support, but it introduces a new credential the server would have to accept and handle (conflicting with the "environment variables are the exclusive credential source" pattern being for Jira specifically) and duplicates a capability the connected AI assistant already has. Sampling reuses the existing client connection instead of adding a second, independently configured model dependency.
- **One tool call per generated artifact (separate tools for "generate feature AC," "generate stories," "generate story AC," "generate estimates")**: rejected. This is closer to the original v1 design but is exactly what this revision is meant to replace — the developer would still be manually sequencing multiple tool calls per feature, which is the workflow friction PRD §3.1/§3.3 now explicitly rule out.

## Risks

- **Availability/version drift of the official Jira MCP server**: since this server is a thin orchestrator on top of it, any breaking change in its tool schemas breaks this server's Jira client wrapper. Mitigate by pinning known-compatible versions/endpoints via env var config.
- **In-memory-only state loss on crash**: if the server process crashes mid-run (e.g., after Jira stories are created but before the "proceed" gate), there is no persisted run state to resume from; the developer would need to re-drive remaining steps manually. Acceptable for a single-developer local tool per PRD's single-tenant model, but worth surfacing to the user as a known limitation.
- **Secrets in environment variables**: while compliant with PRD §4/§6, env vars can still leak via process listing or crash dumps on some systems; standard OS-level environment hygiene is the developer's responsibility, not enforced by this server.
- **Client sampling-capability dependency**: Stage 1 and Stage 2 tools now depend on the connected AI assistant supporting the MCP sampling capability (PRD §10). If a client doesn't support it, those tools fail outright with no fallback; this narrows which MCP clients this server works with beyond just "any MCP-compatible assistant."
- **Generated content quality is unreviewed until the approval gate**: because AC and story generation happen inside a single tool call before the developer sees anything, a poor problem statement or a model's misunderstanding of scope can produce a full story set that needs to be rejected and regenerated wholesale via the Stage 2 approval gate, rather than corrected incrementally story-by-story as in the original per-story-call design.

## Phase Plan

Grouping unit: **feature group**, following the PRD's own §3.x feature numbering, since each is independently describable, independently testable via its own MCP tool calls, and maps to the PRD's structure directly.

- **Phase 1 — Foundation**: MCP server scaffold (`server.py`), config loading from env vars (`config.py`), and connection wiring to the Jira child MCP server (no tools with business logic yet — just a running, connectable server). Independently runnable: server starts, accepts a connection, and can be pinged.
- **Phase 2 — Stage 1: Feature Intake and AC Generation (§3.1)**: `content_generation.py` sampling helper for AC generation; `start_feature` tool that generates feature AC via sampling and creates the Jira Feature in one call.
- **Phase 3 — Stage 1 Approval Gate (§3.2)**: Approval tool for feature AC, with `workflow_state.py` gate enforcement blocking Stage 2 for a feature until called.
- **Phase 4 — Stage 2: Story Generation, Estimation, AC, and Scheduling (§3.3)**: `generate_stories_for_feature` tool that, once the Stage 1 gate is passed, generates the story set, per-story AC, and estimates via sampling, then creates/estimates/schedules all stories in Jira in one call.
- **Phase 5 — Stage 2 Approval Gate (§3.4)**: Approval tool for the generated story set, with `workflow_state.py` gate enforcement blocking Stage 3 coding tools for any story under that feature until called.
- **Phase 6 — Pre-Coding Approval Gate (§3.5)**: `proceed` tool and gate enforcement blocking coding-stage tools until called for a given story (unchanged from original design).
- **Phase 7 — Coding Support (§3.6)**: Git branch creation per user story in the per-run selected repository (code generation itself remains delegated to the calling assistant, no server-side implementation). This is the last stage in scope for v1; test verification, PR creation, documentation, and release remain manual steps.
