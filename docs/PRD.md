# PRD: E2E Developer Workflow MCP Server

## 1. Problem Statement

Developers manually shepherd a feature from a problem statement through issue-tracker grooming and into coding, switching tools and context at every step. This MCP server orchestrates that pipeline from a single input, delegating actual code generation to the connected AI assistant while automating the surrounding tracker process (Jira or GitHub Issues) and the pre-coding setup (branch creation).

## 2. Users

Software developers at Improving, working individually, who use an MCP-compatible AI assistant (e.g., Claude Code) as their interface. The tool is distributed as a team-wide capability, but each developer runs their own local instance configured with their own credentials.

## 3. MVP Features

Features are grouped into three stages. Stage 1 and Stage 2 are each driven by a single MCP tool call per stage (plus one approval-gate tool each), so the developer does not need to manually orchestrate feature creation, refinement, estimation, and scheduling as separate tool invocations. Stage 3 remains a sequence of discrete tool calls per user story, because its steps each require an intermediate checkpoint (explicit coding approval before implementation begins) that the developer or AI assistant must observe before continuing; collapsing these would remove the safety checkpoints required by §3.5–3.6 below.

**Tracker support (changed):** every Stage 1/2/3 tool accepts an explicit `tracker` argument (`"jira"` or `"github"`), resolved per call, not fixed per run or per server instance. Tracker-specific arguments (Jira project key/board/sprint vs. GitHub repo owner/name) are all present in each tool's schema but optional, and validated against the supplied `tracker` value at call time — e.g. a `tracker: "github"` call with a `sprint` argument is rejected as invalid, and vice versa.

### 3.1 Stage 1 — Feature Intake and AC Generation (single tool call)
- The system shall expose one tool that accepts a problem statement, a `tracker` selector (`jira` or `github`), and the tracker-specific target — a Jira project key when `tracker` is `jira`, or a repository owner/name when `tracker` is `github` — as required inputs.
- The system shall generate feature-level acceptance criteria from the problem statement by requesting a completion from the connected AI assistant via the MCP sampling capability; the server shall not call out to any independently configured LLM provider or hold its own model credentials.
- For `tracker: jira`, the system shall create a corresponding Jira Feature via the Jira MCP server, populated with the problem statement and the generated acceptance criteria.
- For `tracker: github`, the system shall create a corresponding parent Issue in the target repository via the GitHub MCP server, labeled to identify it as a feature-level issue, populated with the problem statement and the generated acceptance criteria in the issue body.
- The system shall return the created feature's identifier (Jira key or GitHub issue number) and the generated acceptance criteria to the developer and shall not begin Stage 2 for that feature until they are approved.

### 3.2 Stage 1 Approval Gate — Feature Acceptance Criteria
- The system shall expose an approval tool that accepts the tracker, the feature identifier, and either an approval or a revised/edited version of the acceptance criteria.
- The system shall not start Stage 2 (story generation) for a feature until this approval tool has been called and the acceptance criteria are approved.
- If the developer submits edited acceptance criteria instead of a plain approval, the system shall update the Jira Feature or GitHub parent Issue (per the feature's tracker) with the edited text and treat that submission as the approval.

### 3.3 Stage 2 — Story Generation, AC, and Scheduling (single tool call)
- The system shall expose one tool, usable only after the Stage 1 approval gate has been passed for a feature, that accepts the tracker, the feature identifier, and tracker-specific scheduling arguments:
  - For `tracker: jira`: the Jira board and sprint to schedule into (required), and optionally a default assignee.
  - For `tracker: github`: optionally a default assignee. Board and sprint arguments are not applicable and shall be rejected if supplied.
- The system shall generate a set of user stories that collectively satisfy the approved feature acceptance criteria, using the MCP sampling capability against the connected AI assistant.
- The system shall generate acceptance criteria for each generated story using the same sampling mechanism.
- For `tracker: jira`, the system shall additionally generate a story point estimate for each story via sampling, write it to the story, and schedule the story into the specified sprint.
- For `tracker: github`, the system shall create each generated story as a child Issue of the feature's parent Issue (or linked via GitHub's sub-issue relationship where supported by the GitHub MCP server), with the generated acceptance criteria in the issue body. No story point estimate or sprint scheduling is generated or written for GitHub-tracked stories in this increment (GitHub Issues has no native equivalent; GitHub Projects v2 support is deferred — see Open Questions).
- The system shall create each generated story in the target tracker via the corresponding MCP server (Jira or GitHub) in a single tool invocation covering all stories produced from the feature.
- The system shall support assigning each created story to a developer — in Jira or in GitHub Issues — when an assignee is supplied, for either tracker.
- The system shall return the full list of created story identifiers, their acceptance criteria, and (for Jira only) their estimates to the developer in the tool's response for review.

### 3.4 Stage 2 Approval Gate — Story Set Review
- The system shall expose an approval tool that accepts the tracker, the feature identifier, and either an approval of the generated story set or a request to regenerate it.
- The system shall not start Stage 3 (coding) for any story belonging to a feature until this approval tool has been called for that feature.

### 3.5 Pre-Coding Approval Gate (Stage 3)
- The system shall expose a "proceed" tool that must be explicitly called before the coding stage begins for a given user story, accepting the tracker and the story identifier.
- The system shall not start the coding stage for a user story until the "proceed" tool has been called for it.

### 3.6 Coding (Delegated Implementation)
- The system shall delegate generation of implementation code for a user story to the calling AI assistant; the server itself shall not generate source code.
- The system shall create a git branch for the user story implementation in the repository selected for that run.
- The system shall support a repository being selected per run (not fixed per server instance).

## 4. Non-Functional Requirements

- **Security**: All credentials (Jira PAT, GitHub PAT, and any other secrets required by the underlying tracker MCP servers) shall be supplied via environment variables; the system shall not persist secrets to disk.
- **Configurability**: The Jira MCP server URL and the GitHub MCP server URL shall each be configurable via environment variables, not hardcoded.
- **Secure coding**: The system shall instruct/guide the AI assistant to follow secure coding practices during the delegated coding stage (the server does not itself statically enforce this in v1).
- **Data handling**: The system is for Improving's internal engineering work only; no client-confidential data is in scope for v1.

## 5. Out of Scope

- A shared or centrally-hosted server deployment (v1 is single-developer, locally-hosted only).
- Multi-repo or multi-project orchestration within a single run.
- Support for issue trackers other than Jira and GitHub Issues (e.g., GitLab, Azure DevOps, Linear).
- GitHub Projects v2 (boards, sprints, custom-field story points) for GitHub-tracked work — GitHub runs use plain Issues only in this increment.
- Mirroring or syncing a feature/story set to both trackers simultaneously within a single run; each run targets exactly one tracker, selected per tool call via the `tracker` argument.
- A UI or dashboard; all interaction is through the MCP client (AI assistant).
- Test execution, pull request creation, documentation updates, and release creation (the pipeline ends once the implementation branch is created; these remain manual steps for v1).

## 6. Constraints

- Must run as a locally-hosted process per developer machine.
- Must authenticate to Jira using a PAT/access token via the existing/official Jira MCP server, supplied as an environment variable.
- Must authenticate to GitHub using a PAT/access token via an official GitHub MCP server, supplied as an environment variable; the system shall not call the GitHub REST API directly.
- Internal Improving engineering use only; no client-confidential or PII data handling in v1.
- Per Improving's Third-Party Service Use Policy, this is built for use with Claude (Sonnet/Haiku) as the connected AI assistant.

## 7. Technology Stack

- **Language/Runtime**: Python, using the official MCP Python SDK — chosen for team familiarity and debuggability (primary developer is a Python developer).
- **Upstream integrations**: Official Atlassian/Jira MCP server and official GitHub MCP server, each connected as a configurable child MCP server (URL/endpoint overridable via environment variables); exactly one is used per tool call, selected by the `tracker` argument.
- **Execution model**: Locally-hosted process, one instance per developer, configured via environment variables for secrets and endpoints.
- **Code generation**: Delegated entirely to the calling AI assistant; this server does not generate source code itself.

## 8. Architecture Constraints

- Single-tenant, single-developer-process model — no shared state or multi-user coordination in v1.
- Repository and tracker target (Jira project, or GitHub repo) are selected per tool call via explicit arguments, not fixed at server startup.
- The server acts as an orchestrator/MCP client-and-server hybrid: it exposes tools to the AI assistant and, in turn, calls the Jira MCP server or the GitHub MCP server as needed, based on the `tracker` argument of the incoming call.
- No sandboxing/containerization layer for git operations in v1; branch creation runs directly in the developer's configured local environment.
- Approval gate is implemented as an explicit MCP tool call ("proceed"), not a UI element or tracker status transition.
- Feature/story identifier handling is tracker-shaped: Jira keys (e.g. `PROJ-123`) and GitHub issue numbers are both valid identifiers but are not interchangeable; workflow state tracks which tracker owns each identifier.

## 9. Success Criteria

- A developer can call one Stage 1 tool with a problem statement, a `tracker` selection, and the matching target (Jira project key or GitHub repo) and receive back a created Feature/parent Issue with generated acceptance criteria, without manually drafting the AC themselves.
- Story generation and per-story AC (plus, for Jira, estimation and sprint scheduling) for an approved feature happen from one Stage 2 tool call, not one tool call per story, regardless of tracker.
- No story creation occurs before the developer has approved the feature's acceptance criteria, and no coding activity occurs before the developer has explicitly triggered the "proceed" tool for that story, regardless of tracker.
- The server runs entirely from a developer's local machine using only environment-variable-supplied configuration, with no shared infrastructure required, for either tracker.

## 10. Open Questions

- Should a future increment add GitHub Projects v2 support (custom fields for story points, sprint-equivalent iterations) to bring GitHub-tracked work to parity with Jira's estimation/scheduling, or is plain-Issues-only a permanent characteristic of GitHub support rather than a temporary gap? Deferred; not required for this increment.

One documented assumption (carried forward):
- Stage 1 and Stage 2 AC/story generation depend on the connected AI assistant supporting the MCP sampling capability. If a given client does not support sampling, those tools shall fail with a clear error rather than silently falling back to a lower-quality behavior; no non-sampling fallback is in scope for v1.
