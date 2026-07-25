# E2E Developer Workflow MCP Server

An MCP (Model Context Protocol) server that orchestrates the issue-tracker grooming and pre-coding portion of the developer workflow, from a single problem statement to an implementation branch ready for coding, by coordinating your AI assistant (e.g. Claude Code) and your issue tracker of choice — Jira or GitHub Issues. It does not write code itself; it drives the surrounding process (tracker grooming, approval gating, branch creation) while delegating actual implementation to the connected AI assistant.

## What this server does

Normally, shipping a feature means manually creating a tracker item, breaking it into stories, estimating/assigning/scheduling them, then writing code and creating a branch, each a separate manual step across separate tools.

This server exposes that pipeline as a small set of staged MCP tools your AI assistant calls in sequence, in a single conversation. Every tool takes an explicit `tracker` argument (`"jira"` or `"github"`), chosen per call — one tracker per call, not both at once. The workflow is organized into three stages so that you mostly just supply a problem statement and a couple of review/approval decisions, rather than manually calling one tool per tracker field:

1. **Stage 1 — Feature intake and AC generation.** You give it a problem statement, `tracker`, and the tracker-specific target (Jira project key, or GitHub repo owner/name). The server asks your AI assistant (via MCP sampling) to draft feature-level acceptance criteria, then creates the Jira Feature or GitHub parent Issue populated with them, in one tool call.
2. **Stage 1 approval gate.** You review the generated acceptance criteria and either approve them as-is or submit an edited version. Nothing in Stage 2 happens until this gate is passed.
3. **Stage 2 — Story generation, AC, and (Jira only) estimation/scheduling.** Once the feature's AC is approved, one tool call generates a set of stories that satisfy it and drafts AC for each. For `tracker: jira`, it also generates a story point estimate per story and schedules each into the board/sprint you specify. For `tracker: github`, it creates each story as a child Issue of the parent feature Issue instead — no points or sprint scheduling, since GitHub Issues has no native equivalent in this increment.
4. **Stage 2 approval gate.** You review the generated story set and either approve it or ask for it to be regenerated. Nothing in Stage 3 happens until this gate is passed.
5. **Stage 3 — Coding**, driven per story:
   - **Approval gate** — nothing is coded for a story until you explicitly call `proceed` for it.
   - **Branch creation** — the server creates the git branch for the story's implementation.
   - **Coding** — code generation is done entirely by your AI assistant, directly in your working copy on that branch.

Stage 3 stays as individual tool calls per story, on purpose: the approval gate is a checkpoint that you or your AI assistant need to see before coding starts. Collapsing it would remove the safety check the workflow depends on.

Test execution, pull request creation, documentation updates, and release creation are not part of this server's scope; once an implementation branch exists, those remain manual steps (or steps handled by other tooling) outside this pipeline.

## How it does it

- The server is itself an MCP server (it exposes tools to your AI assistant) and also an MCP client (it calls out to the official Jira MCP server and/or the official GitHub MCP server to do the actual work, exactly one per tool call, selected by `tracker`). It never talks to the Jira or GitHub REST APIs directly.
- Feature AC, story splitting, per-story AC, and (Jira only) story point estimates are generated using the MCP **sampling** capability: the server asks the connected AI assistant to generate that content mid-tool-call, rather than you or your assistant drafting it and passing it in as a tool argument. The server holds no LLM API key of its own — this only works if your AI assistant's MCP client supports sampling. If it doesn't, Stage 1/Stage 2 tools fail outright with no fallback.
- All workflow state (which feature/story has been approved, and which tracker owns it) is kept in memory for the lifetime of the running process. There is no database and nothing is written to disk. If the process restarts, that state is lost and steps need to be re-driven.
- Git branch creation happens via a subprocess call against the repository path you provide, running unsandboxed with your local machine's permissions.
- Every credential (Jira token, GitHub token) and endpoint (Jira MCP URL, GitHub MCP URL) comes from environment variables only. Nothing is stored in code or config files. GitHub's variables are only required once a call actually uses `tracker: github`.
- The repository path and tracker target (Jira project, or GitHub repo owner/name) are chosen per tool call, not fixed when the server starts. This is a single-developer, locally-hosted tool: one instance per developer machine, no shared or centralized deployment.

## Prerequisites

- Python 3.14 and [Poetry](https://python-poetry.org/) installed.
- For Jira runs: a running instance of the official Atlassian/Jira MCP server, reachable at a URL you control, and a Jira API token (PAT) with permission to create and update issues in your target project (see PAT permissions below).
- For GitHub runs: a running instance of an official GitHub MCP server, reachable at a URL you control, and a GitHub PAT with permission to create and update issues in your target repository (see PAT permissions below).
- A local git repository already cloned.
- An MCP-compatible AI assistant (Claude Code) to act as the client driving these tools. Only Claude Sonnet or Claude Haiku are approved for this use.
- An AI assistant/MCP client that supports the MCP **sampling** capability. Stage 1 and Stage 2 tools generate acceptance criteria, story splits, and (Jira only) estimates by requesting completions from the client over sampling; without it, those tools fail.

## PAT permissions

Both tokens are bearer credentials sent to their respective *official* MCP server (never to this server directly, and never to the Jira/GitHub REST APIs directly). Scope each one to the minimum this workflow actually needs.

### Jira API token (`JIRA_API_TOKEN`)

This server only creates and updates Features/stories in the project you specify — it never reads or writes anything else in your Jira instance. Scope the token's underlying account to:

- **Browse projects** — to look up and validate the target project key.
- **Create issues** — to create the Feature (Stage 1) and each story (Stage 2).
- **Edit issues** — to update acceptance criteria text (Stage 1 approval-gate edits) and to write story point estimates.
- **Schedule issues** / **Manage sprints** (board-level permission) — to assign created stories into the sprint specified in Stage 2. Skip this if you only ever plan to use `tracker: jira` without sprint scheduling, but Stage 2 requires it whenever `sprint` is supplied.
- **Assign issues** — only needed if you pass a `default_assignee` in Stage 2.

Restrict the token to the specific project(s) you'll target with this tool, not a site-wide admin scope. If your org uses Atlassian's OAuth-based remote MCP server (see below) instead of a classic API token, grant the equivalent OAuth scopes (`read:jira-work`, `write:jira-work`) during the one-time authorization instead of provisioning a separate PAT.

### GitHub PAT (`GITHUB_API_TOKEN`)

This server only creates and updates Issues in the repository you specify — it never touches code, branches, or other repository content through this token (the git branch created in Stage 3 uses your local git credentials, not this PAT). Scope a fine-grained PAT to:

- **Repository access**: the specific repository/repositories you'll target, not all repositories.
- **Issues: Read and write** — to create the parent feature Issue and child story Issues, update AC text on approval-gate edits, and set assignees.
- **Metadata: Read** (fine-grained PATs require this alongside any other permission) — to resolve labels and repo details.

A classic PAT with the `repo` scope also works but is broader than necessary, since `repo` also grants code/branch/webhook access this server never uses. Prefer a fine-grained PAT scoped as above. No `admin:org`, `workflow`, or `write:packages` scopes are needed for anything this server does.

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
| `GITHUB_MCP_URL` | Only for `tracker: github` calls | URL of the running GitHub MCP server. |
| `GITHUB_API_TOKEN` | Only for `tracker: github` calls | GitHub PAT/API token, sent as a bearer token to the GitHub MCP server. |

`JIRA_MCP_URL`/`JIRA_API_TOKEN` are required at startup regardless of which tracker you end up using. `GITHUB_MCP_URL`/`GITHUB_API_TOKEN` are optional at startup — the server only fails if a tool is actually called with `tracker: "github"` and they're unset.

Set them in your shell before starting the server, for example:

```bash
export JIRA_MCP_URL="https://your-jira-mcp-host:port"
export JIRA_API_TOKEN="your-jira-pat"
export GITHUB_MCP_URL="https://your-github-mcp-host:port"
export GITHUB_API_TOKEN="your-github-pat"
```

If `JIRA_MCP_URL`/`JIRA_API_TOKEN` are missing, the server prints a configuration error and exits immediately without starting.

## Starting the server

This server speaks MCP over stdio: it doesn't bind to a network port itself. It's meant to be launched as a local subprocess by your AI assistant, not connected to over a URL. You can still run it standalone to sanity-check that configuration is valid:

```bash
make run
```

With valid environment variables, this blocks waiting for an MCP client to speak to it over stdin/stdout (there's no output because a real client hasn't attached). Ctrl+C to stop it. In normal use, though, you register it with your AI assistant (next section) and let the assistant start and stop the process for you.

## Adding/running the official Jira and GitHub MCP servers

This server never talks to Jira or GitHub directly — it calls out to the official Jira MCP server and/or the official GitHub MCP server as child processes/services. You need at least one of these already running and reachable before starting this server.

### Official Atlassian (Jira) MCP server

Atlassian provides a hosted remote MCP server, so there's usually nothing to self-host. Register it with Claude Code as a remote SSE server:

```bash
claude mcp add atlassian --transport sse https://mcp.atlassian.com/v1/sse
```

The first call from Claude Code triggers an OAuth login against your Atlassian account in the browser; approve it once and the token is stored by Claude Code. Once connected, use the URL Claude Code exposes for this connection as your `JIRA_MCP_URL` when configuring this server (or check Atlassian's MCP docs if your org self-hosts a Data Center variant instead of Atlassian Cloud, in which case use that URL). Confirm it's live with:

```bash
claude mcp list
```

### Official GitHub MCP server

GitHub publishes an official server at [github/github-mcp-server](https://github.com/github/github-mcp-server). GitHub also hosts a remote version; register that with Claude Code the same way as Atlassian's:

```bash
claude mcp add github --transport sse https://api.githubcopilot.com/mcp/
```

This also triggers a one-time OAuth flow in the browser tied to your GitHub account. If you'd rather self-host it locally (e.g. to use a fine-grained PAT instead of OAuth), run the published Docker image and point this server's `GITHUB_MCP_URL` at it:

```bash
docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN="your-github-pat" \
  ghcr.io/github/github-mcp-server
```

Either way, verify the connection with `claude mcp list` before wiring it into this server's configuration below.

### Then point this server at them

Whichever URLs/tokens you end up with from the two steps above are what you supply as `JIRA_MCP_URL`/`JIRA_API_TOKEN` and `GITHUB_MCP_URL`/`GITHUB_API_TOKEN` in the Configuration section — this server is a separate MCP server from both of those, chained together only through the environment variables you set for it.

## Registering it as an MCP server with your AI assistant

Because the transport is stdio, "registering" the server means telling your AI assistant what command to run to launch it, plus which environment variables to pass in. The assistant then starts/stops the process itself each session; you don't run it manually.

### Claude Code CLI

From the repository directory:

```bash
claude mcp add e2e-workflow \
  --env JIRA_MCP_URL="https://your-jira-mcp-host:port" \
  --env JIRA_API_TOKEN="your-jira-pat" \
  --env GITHUB_MCP_URL="https://your-github-mcp-host:port" \
  --env GITHUB_API_TOKEN="your-github-pat" \
  -- poetry run python -m e2e_mcp_server start
```

Omit the `GITHUB_*` variables if you only intend to use `tracker: jira` in this instance.

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
        "JIRA_API_TOKEN": "your-jira-pat",
        "GITHUB_MCP_URL": "https://your-github-mcp-host:port",
        "GITHUB_API_TOKEN": "your-github-pat"
      }
    }
  }
}
```

`cwd` must be an absolute path to this repository so Poetry resolves its virtualenv correctly regardless of where the client process itself launches from. Tokens go directly in this file's `env` block since the launching client, not your login shell, is what needs to see them — keep this file out of version control or restrict its permissions, since it holds plaintext credentials.

### What you need before any of this works

1. The official **Jira MCP server** already running somewhere reachable, with a Jira PAT that can create/update issues in your target project (always), and/or the official **GitHub MCP server** already running somewhere reachable, with a GitHub PAT that can create/update issues in your target repo (only if you intend to use `tracker: github`).
2. This repository cloned locally with `poetry install` already run (see Installation above).
3. A local clone of the repository you intend to work in.

Once those three things exist and the config above points at them, ask your AI assistant to call `ping` — a `"pong"` response confirms the whole chain (assistant → this server → environment) is wired correctly, before you start driving real Jira work through it.

## Step-by-step usage

All tools below are implemented in [`server.py`](src/e2e_mcp_server/server.py) today, for both trackers. Every Stage 1/2/3 tool takes an explicit `tracker` argument (`"jira"` or `"github"`), plus whichever tracker-specific arguments apply — those are optional in the schema but validated against `tracker` at call time (e.g. passing `sprint` with `tracker: "github"` is rejected, and omitting `project_key` with `tracker: "jira"` is rejected as missing).

Once your AI assistant is connected to this server, drive the workflow by asking it to call the tools below, in order, for a given piece of work. In practice you don't type these as raw arguments yourself: you describe what you want in plain English, and your AI assistant fills in the actual parameter values, carrying forward identifiers like `feature_key` or `story_key` from the results of earlier tool calls in the same conversation.

### Stage 1 — Feature intake and AC generation

1. **Check the connection**
   Call `ping`. It returns `"pong"` if the server is reachable.

2. **Create the feature and generate its acceptance criteria**
   Call `start_feature(problem_statement, tracker, project_key, repo_owner, repo_name)`.
   - `tracker: "jira"` requires `project_key`.
   - `tracker: "github"` requires `repo_owner` and `repo_name`.

   Example (Jira): "Create a feature for 'Users cannot reset their password from mobile' in Jira project `ENG`."
   Example (GitHub): "Create a feature for 'Users cannot reset their password from mobile' in the `improving/mobile-app` GitHub repo."

   The server asks your AI assistant (via MCP sampling) to draft acceptance criteria, then creates the Jira Feature or the GitHub parent Issue with them, and returns the feature's identifier (`feature_key`) plus the generated AC text for your review.

3. **Approve or edit the feature's acceptance criteria**
   Call `approve_feature_acceptance_criteria(feature_key, tracker, edited_acceptance_criteria, repo_owner, repo_name)`. Omit `edited_acceptance_criteria` to approve as-is, or pass edited text to both update the tracker item and approve it in one call. `tracker: "github"` requires `repo_owner`/`repo_name` here too (GitHub has no equivalent of a Jira key alone resolving to a project). Stage 2 is blocked for this feature until this call succeeds.

### Stage 2 — Story generation, AC, and (Jira only) estimation/scheduling

4. **Generate and create the stories**
   Call `generate_stories_for_feature(feature_key, tracker, board, sprint, assignee, repo_owner, repo_name)`.
   - `tracker: "jira"` requires `board` and `sprint`; `assignee` is optional. The server drafts AC and a story point estimate for each generated story, creates them in Jira, schedules each into the given sprint, and returns every story's key, estimate, and AC. `board`/`sprint` are passed through to the Jira MCP server's `scheduleIssue` tool as opaque strings with no format validation on this side — whether it expects numeric board/sprint IDs or human-readable names depends on that server's own schema, so check its docs/tool description before guessing a value here.
   - `tracker: "github"` requires `repo_owner`/`repo_name`; `board`/`sprint` are rejected if supplied. `assignee` is optional. The server drafts AC for each story and creates each as a child Issue of the feature's parent Issue — no story points or sprint scheduling are generated or written for GitHub-tracked stories.

5. **Approve or reject the generated story set**
   Call `approve_story_set(feature_key, tracker, regenerate)`. Leave `regenerate` false to approve; set it true to reject and allow `generate_stories_for_feature` to be called again. Stage 3 is blocked for every story under this feature until this call succeeds with approval.

### Stage 3 — Coding (per story)

6. **Approve the story for coding**
   Call `proceed(story_key, tracker)`. No coding-stage tool works for this story before this call, and this call itself is blocked until the story's feature has passed the Stage 2 approval gate.

7. **Create the implementation branch**
   Call `create_implementation_branch(story_key, tracker, repository_path)`. This fails with an approval-gate error if step 6 was skipped.

8. **Write the code**
   This step is not a server tool. Have your AI assistant write the implementation directly in your working copy at `repository_path`, on the branch just created, the same way it would for any other coding task.

That sequence, steps 2 through 8, covers the pipeline from problem statement through implementation branch — with two review/approval decisions from you along the way (feature AC, story set) before per-story coding begins, for either tracker. Testing, PR creation, documentation, and release are up to you (or other tooling) once the code is written.

## Limitations to know before you rely on this

- Stage 1/Stage 2 tools require your AI assistant's MCP client to support the sampling capability. Without it, feature/story generation fails outright; there's no fallback to a non-generated path.
- Because AC and story generation happen inside a single tool call before you see anything, a vague problem statement can produce a full story set that needs to be rejected and regenerated wholesale via the Stage 2 approval gate, rather than corrected story-by-story.
- GitHub Issues support is plain Issues only in this increment: no story points, no sprints/boards, no GitHub Projects v2 integration. Jira-tracked work gets estimation and sprint scheduling; GitHub-tracked work doesn't.
- Exactly one tracker per tool call. This server does not mirror or sync a feature/story set to both Jira and GitHub simultaneously within a single run.
- State lives only in memory. A server restart mid-workflow loses the approval history for every story; you'll need to re-call `proceed` for anything in flight.
- Branch creation is not sandboxed. It runs directly on your machine with your local permissions.
- This is a single-developer, single-repository, single-tracker-target-per-run tool. It does not coordinate multiple developers or multiple repositories/projects in one run.
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
- **No multi-user or multi-repo coordination.** It's built for one developer, one repository, one tracker target (Jira project or GitHub repo) per run. Running it centrally for a team would require redesigning the state model (which today is explicitly rejected in favor of "the tracker is the system of record, nothing else persists").
- **Secrets hygiene is left to the OS.** Tokens are read from environment variables and never written to disk by this server, which is good, but there's no secrets-manager integration, no rotation support, and env vars are still visible via process listing on some systems. Two independently configured credentials (Jira PAT, GitHub PAT) widen this surface versus a Jira-only setup.
- **Dependency on the Jira/GitHub MCP servers' stability.** Since this is a thin orchestrator over the official Jira MCP server and (for GitHub runs) the official GitHub MCP server, a breaking change in either one's tool schemas breaks only that tracker's client wrapper silently until updated.

None of this makes the code low-quality; the test suite is solid and the architecture is intentionally minimal. But it's built and scoped as a personal productivity tool for a single developer's local machine, not a service you'd deploy centrally, expose to a team, or run unattended in CI. Treat it as a local assistant-augmentation tool. If you want to move it toward production/shared use, the priority items would be: persistent workflow state with crash recovery, sandboxed branch creation, and an authn/authz boundary in front of the MCP tool surface.
