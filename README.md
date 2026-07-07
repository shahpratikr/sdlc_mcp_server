# E2E Developer Workflow MCP Server

An MCP (Model Context Protocol) server that orchestrates the Jira grooming and pre-coding portion of the developer workflow, from a single problem statement to an implementation branch ready for coding, by coordinating your AI assistant (e.g. Claude Code) and Jira. It does not write code itself; it drives the surrounding process (Jira grooming, approval gating, branch creation) while delegating actual implementation to the connected AI assistant.

## What this server does

Normally, shipping a feature means manually creating a Jira Feature, breaking it into stories, estimating and assigning them, scheduling them into a sprint, then writing code and creating a branch, each a separate manual step across separate tools.

This server exposes that pipeline as a small set of staged MCP tools your AI assistant calls in sequence, in a single conversation. The workflow is organized into three stages so that you mostly just supply a problem statement and a couple of review/approval decisions, rather than manually calling one tool per Jira field:

1. **Stage 1 — Feature intake and AC generation.** You give it a problem statement and a Jira project key. The server asks your AI assistant (via MCP sampling) to draft feature-level acceptance criteria, then creates the Jira Feature populated with them, in one tool call.
2. **Stage 1 approval gate.** You review the generated acceptance criteria and either approve them as-is or submit an edited version. Nothing in Stage 2 happens until this gate is passed.
3. **Stage 2 — Story generation, estimation, AC, and scheduling.** Once the feature's AC is approved, one tool call generates a set of stories that satisfy it, drafts AC and a story point estimate for each, creates all of them in Jira, and schedules them into the sprint you specify.
4. **Stage 2 approval gate.** You review the generated story set and either approve it or ask for it to be regenerated. Nothing in Stage 3 happens until this gate is passed.
5. **Stage 3 — Coding**, driven per story:
   - **Approval gate** — nothing is coded for a story until you explicitly call `proceed` for it.
   - **Branch creation** — the server creates the git branch for the story's implementation.
   - **Coding** — code generation is done entirely by your AI assistant, directly in your working copy on that branch.

Stage 3 stays as individual tool calls per story, on purpose: the approval gate is a checkpoint that you or your AI assistant need to see before coding starts. Collapsing it would remove the safety check the workflow depends on.

Test execution, pull request creation, documentation updates, and release creation are not part of this server's scope; once an implementation branch exists, those remain manual steps (or steps handled by other tooling) outside this pipeline.

## How it does it

- The server is itself an MCP server (it exposes tools to your AI assistant) and also an MCP client (it calls out to the official Jira MCP server to do the actual work). It never talks to the Jira REST API directly.
- Feature AC, story splitting, per-story AC, and story point estimates are generated using the MCP **sampling** capability: the server asks the connected AI assistant to generate that content mid-tool-call, rather than you or your assistant drafting it and passing it in as a tool argument. The server holds no LLM API key of its own — this only works if your AI assistant's MCP client supports sampling. If it doesn't, Stage 1/Stage 2 tools fail outright with no fallback.
- All workflow state (which feature/story has been approved) is kept in memory for the lifetime of the running process. There is no database and nothing is written to disk. If the process restarts, that state is lost and steps need to be re-driven.
- Git branch creation happens via a subprocess call against the repository path you provide, running unsandboxed with your local machine's permissions.
- Every credential (Jira token) and endpoint (Jira MCP URL) comes from environment variables only. Nothing is stored in code or config files.
- The repository path and Jira project are chosen per run, as arguments to tool calls, not fixed when the server starts. This is a single-developer, locally-hosted tool: one instance per developer machine, no shared or centralized deployment.

## Prerequisites

- Python 3.14 and [Poetry](https://python-poetry.org/) installed.
- A running instance of the official Atlassian/Jira MCP server, reachable at a URL you control.
- A Jira API token (PAT) with permission to create and update issues in your target project.
- A local git repository already cloned.
- An MCP-compatible AI assistant (Claude Code) to act as the client driving these tools. Only Claude Sonnet or Claude Haiku are approved for this use.
- An AI assistant/MCP client that supports the MCP **sampling** capability. Stage 1 and Stage 2 tools generate acceptance criteria, story splits, and estimates by requesting completions from the client over sampling; without it, those tools fail.

## Installation

```bash
cd sdlc_mcp_server
make install
```

This installs the server and its dependencies into a Poetry-managed virtual environment.

## Configuration

The server reads all configuration from environment variables. None of these are ever written to disk by the server.

| Variable | Required | Description |
|---|---|---|
| `JIRA_MCP_URL` | Yes | URL of the running Jira MCP server. |
| `JIRA_API_TOKEN` | Yes | Jira PAT/API token, sent as a bearer token to the Jira MCP server. |

Set them in your shell before starting the server, for example:

```bash
export JIRA_MCP_URL="https://your-jira-mcp-host:port"
export JIRA_API_TOKEN="your-jira-pat"
```

If any of these are missing, the server prints a configuration error and exits immediately without starting.

## Starting the server

This server speaks MCP over stdio: it doesn't bind to a network port itself. It's meant to be launched as a local subprocess by your AI assistant, not connected to over a URL. You can still run it standalone to sanity-check that configuration is valid:

```bash
make run
```

With valid environment variables, this blocks waiting for an MCP client to speak to it over stdin/stdout (there's no output because a real client hasn't attached). Ctrl+C to stop it. In normal use, though, you register it with your AI assistant (next section) and let the assistant start and stop the process for you.

## Registering it as an MCP server with your AI assistant

Because the transport is stdio, "registering" the server means telling your AI assistant what command to run to launch it, plus which environment variables to pass in. The assistant then starts/stops the process itself each session; you don't run it manually.

### Claude Code CLI

From the repository directory:

```bash
claude mcp add e2e-workflow \
  --env JIRA_MCP_URL="https://your-jira-mcp-host:port" \
  --env JIRA_API_TOKEN="your-jira-pat" \
  -- poetry run python -m e2e_mcp_server start
```

Run this from inside `sdlc_mcp_server/` (or add `--cwd /absolute/path/to/sdlc_mcp_server` if your `claude mcp add` version supports it), since Poetry needs to find `pyproject.toml` to resolve the right virtualenv. Verify it's registered with `claude mcp list`, and check connectivity from inside a Claude Code session by asking it to call the `ping` tool.

### Manual MCP client config (Claude Code `.mcp.json` or equivalent)

If you're editing an MCP config file directly instead of using the CLI:

```json
{
  "mcpServers": {
    "e2e-workflow": {
      "command": "poetry",
      "args": ["run", "python", "-m", "e2e_mcp_server", "start"],
      "cwd": "/absolute/path/to/sdlc_mcp_server",
      "env": {
        "JIRA_MCP_URL": "https://your-jira-mcp-host:port",
        "JIRA_API_TOKEN": "your-jira-pat"
      }
    }
  }
}
```

`cwd` must be an absolute path to this repository so Poetry resolves its virtualenv correctly regardless of where the client process itself launches from. Tokens go directly in this file's `env` block since the launching client, not your login shell, is what needs to see them — keep this file out of version control or restrict its permissions, since it holds plaintext credentials.

### What you need before any of this works

1. The official **Jira MCP server** already running somewhere reachable, with a Jira PAT that can create/update issues in your target project.
2. This repository cloned locally with `poetry install` already run (see Installation above).
3. A local clone of the repository you intend to work in.

Once those three things exist and the config above points at them, ask your AI assistant to call `ping` — a `"pong"` response confirms the whole chain (assistant → this server → environment) is wired correctly, before you start driving real Jira work through it.

## Step-by-step usage

> **Implementation status:** this section describes the target workflow defined in [`docs/PRD.md`](docs/PRD.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The Stage 3 tools below (`proceed`, `create_branch_for_story`) exist in the current code today. The Stage 1/Stage 2 tools (`start_feature`, `approve_feature_ac`, `generate_stories_for_feature`, `approve_story_set`) are the newly designed replacement for the older per-field Jira tools and have not been implemented in `server.py` yet.

Once your AI assistant is connected to this server, drive the workflow by asking it to call the tools below, in order, for a given piece of work.

Every parameter shown below is required on every call; the server has no defaults, no saved config, and no memory of values from earlier calls beyond what's tracked internally for the approval gate. In practice you don't type these as raw arguments yourself: you describe what you want in plain English, and your AI assistant fills in the actual parameter values, carrying forward identifiers like `feature_key` or `issue_key` from the results of earlier tool calls in the same conversation.

### Stage 1 — Feature intake and AC generation

1. **Check the connection**
   Call `ping`. It returns `"pong"` if the server is reachable.

2. **Create the feature and generate its acceptance criteria**
   Call `start_feature(problem_statement, project_key)`.
   Example: "Create a feature for 'Users cannot reset their password from mobile' in project `ENG`."
   The server asks your AI assistant (via MCP sampling) to draft acceptance criteria, creates the Jira Feature with them, and returns the feature's issue key plus the generated AC text for your review.

3. **Approve or edit the feature's acceptance criteria**
   Call `approve_feature_ac(feature_key, approved)`, or pass edited AC text instead of a plain approval if the draft needs changes. Stage 2 is blocked for this feature until this call succeeds.

### Stage 2 — Story generation, estimation, AC, and scheduling

4. **Generate, estimate, and schedule the stories**
   Call `generate_stories_for_feature(feature_key, board_id, sprint_id, assignee)` (assignee optional). The server asks your AI assistant to split the approved feature AC into stories, drafts AC and a story point estimate for each, creates and schedules all of them in Jira, and returns every created story's key, estimate, and AC in one response.

5. **Approve or reject the generated story set**
   Call `approve_story_set(feature_key, approved)`. If rejected, `generate_stories_for_feature` can be called again to regenerate. Stage 3 is blocked for every story under this feature until this call succeeds with approval.

### Stage 3 — Coding (per story)

6. **Approve the story for coding**
   Call `proceed(issue_key)`. No coding-stage tool works for this story before this call.

7. **Create the implementation branch**
   Call `create_branch_for_story(issue_key, repository_path, branch_name)`. This fails with an approval-gate error if step 6 was skipped.

8. **Write the code**
   This step is not a server tool. Have your AI assistant write the implementation directly in your working copy at `repository_path`, on the branch just created, the same way it would for any other coding task.

That sequence, steps 2 through 8, covers the pipeline from problem statement through implementation branch — with two review/approval decisions from you along the way (feature AC, story set) before per-story coding begins. Testing, PR creation, documentation, and release are up to you (or other tooling) once the code is written.

## Limitations to know before you rely on this

- Stage 1/Stage 2 tools require your AI assistant's MCP client to support the sampling capability. Without it, feature/story generation fails outright; there's no fallback to a non-generated path.
- Because AC and story generation happen inside a single tool call before you see anything, a vague problem statement can produce a full story set that needs to be rejected and regenerated wholesale via the Stage 2 approval gate, rather than corrected story-by-story.
- State lives only in memory. A server restart mid-workflow loses the approval history for every story; you'll need to re-call `proceed` for anything in flight.
- Branch creation is not sandboxed. It runs directly on your machine with your local permissions.
- This is a single-developer, single-repository, single-Jira-project-per-run tool. It does not coordinate multiple developers or multiple repositories in one run.
- The pipeline stops at branch creation. Test execution, PR creation, README updates, and releases are out of scope for v1 and are not automated by this server.

## Running tests

```bash
poetry run pytest
```

## Is this production-ready?

No, not as-is, and it isn't intended to be. This is explicitly a v1, single-developer, locally-hosted tool, and both the PRD and architecture docs call out the tradeoffs behind that:

- **No persistence or crash recovery.** All approval-gate state lives in process memory. If the server crashes or restarts partway through a story (say, right after `proceed` but before the branch is created), that state is gone and there's no way to resume; you re-drive the remaining steps by hand. Fine for one developer working interactively, not fine for anything that needs to be reliable or auditable.
- **No sandboxing on branch creation.** It runs as an unsandboxed subprocess with the full permissions of whoever started the server. This is an accepted, documented tradeoff for v1, not an oversight, but it's a real risk if this were exposed more broadly.
- **No authn/authz layer of its own.** The server trusts whatever AI assistant is connected to it and whatever environment variables it was started with. There's no user identity, no audit log, no rate limiting, and no protection against a compromised or misconfigured client issuing destructive Jira calls.
- **No multi-user or multi-repo coordination.** It's built for one developer, one repository, one Jira project per run. Running it centrally for a team would require redesigning the state model (which today is explicitly rejected in favor of "Jira is the system of record, nothing else persists").
- **Secrets hygiene is left to the OS.** Tokens are read from environment variables and never written to disk by this server, which is good, but there's no secrets-manager integration, no rotation support, and env vars are still visible via process listing on some systems.
- **Dependency on the Jira MCP server's stability.** Since this is a thin orchestrator over the official Jira MCP server, any breaking change in its tool schemas breaks this server silently until updated.

None of this makes the code low-quality; the test suite is solid and the architecture is intentionally minimal. But it's built and scoped as a personal productivity tool for a single developer's local machine, not a service you'd deploy centrally, expose to a team, or run unattended in CI. Treat it as a local assistant-augmentation tool. If you want to move it toward production/shared use, the priority items would be: persistent workflow state with crash recovery, sandboxed branch creation, and an authn/authz boundary in front of the MCP tool surface.
