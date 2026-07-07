# PRD: E2E Developer Workflow MCP Server

## 1. Problem Statement

Developers manually shepherd a feature from a problem statement through Jira grooming and into coding, switching tools and context at every step. This MCP server orchestrates that pipeline from a single input, delegating actual code generation to the connected AI assistant while automating the surrounding Jira process and the pre-coding setup (branch creation).

## 2. Users

Software developers at Improving, working individually, who use an MCP-compatible AI assistant (e.g., Claude Code) as their interface. The tool is distributed as a team-wide capability, but each developer runs their own local instance configured with their own credentials.

## 3. MVP Features

Features are grouped into three stages. Stage 1 and Stage 2 are each driven by a single MCP tool call per stage (plus one approval-gate tool each), so the developer does not need to manually orchestrate feature creation, refinement, estimation, and scheduling as separate tool invocations. Stage 3 remains a sequence of discrete tool calls per user story, because its steps each require an intermediate checkpoint (explicit coding approval before implementation begins) that the developer or AI assistant must observe before continuing; collapsing these would remove the safety checkpoints required by §3.5–3.6 below.

### 3.1 Stage 1 — Feature Intake and AC Generation (single tool call)
- The system shall expose one tool that accepts a problem statement and a target Jira project key as its only required inputs.
- The system shall generate feature-level acceptance criteria from the problem statement by requesting a completion from the connected AI assistant via the MCP sampling capability; the server shall not call out to any independently configured LLM provider or hold its own model credentials.
- The system shall create a corresponding Jira Feature via the Jira MCP server, populated with the problem statement and the generated acceptance criteria.
- The system shall return the created feature's key and the generated acceptance criteria to the developer and shall not begin Stage 2 for that feature until they are approved.

### 3.2 Stage 1 Approval Gate — Feature Acceptance Criteria
- The system shall expose an approval tool that accepts the feature key and either an approval or a revised/edited version of the acceptance criteria.
- The system shall not start Stage 2 (story generation) for a feature until this approval tool has been called and the acceptance criteria are approved.
- If the developer submits edited acceptance criteria instead of a plain approval, the system shall update the Jira Feature with the edited text and treat that submission as the approval.

### 3.3 Stage 2 — Story Generation, Estimation, AC, and Scheduling (single tool call)
- The system shall expose one tool, usable only after the Stage 1 approval gate has been passed for a feature, that accepts the feature key plus the Jira board and sprint to schedule into (and, optionally, a default assignee).
- The system shall generate a set of user stories that collectively satisfy the approved feature acceptance criteria, using the MCP sampling capability against the connected AI assistant.
- The system shall generate acceptance criteria and a story point estimate for each generated story, using the same sampling mechanism.
- The system shall create each generated story in Jira via the Jira MCP server, write its estimate and acceptance criteria to the story, and schedule it into the specified sprint, in a single tool invocation covering all stories produced from the feature.
- The system shall support assigning each created story to a developer in Jira when an assignee is supplied.
- The system shall return the full list of created story keys, their estimates, and their acceptance criteria to the developer in the tool's response for review.

### 3.4 Stage 2 Approval Gate — Story Set Review
- The system shall expose an approval tool that accepts the feature key and either an approval of the generated story set or a request to regenerate it.
- The system shall not start Stage 3 (coding) for any story belonging to a feature until this approval tool has been called for that feature.

### 3.5 Pre-Coding Approval Gate (Stage 3)
- The system shall expose a "proceed" tool that must be explicitly called before the coding stage begins for a given user story.
- The system shall not start the coding stage for a user story until the "proceed" tool has been called for it.

### 3.6 Coding (Delegated Implementation)
- The system shall delegate generation of implementation code for a user story to the calling AI assistant; the server itself shall not generate source code.
- The system shall create a git branch for the user story implementation in the repository selected for that run.
- The system shall support a repository being selected per run (not fixed per server instance).

## 4. Non-Functional Requirements

- **Security**: All credentials (Jira PAT and any other secrets required by the underlying Jira MCP server) shall be supplied via environment variables; the system shall not persist secrets to disk.
- **Configurability**: The Jira MCP server URL shall be configurable via environment variables, not hardcoded.
- **Secure coding**: The system shall instruct/guide the AI assistant to follow secure coding practices during the delegated coding stage (the server does not itself statically enforce this in v1).
- **Data handling**: The system is for Improving's internal engineering work only; no client-confidential data is in scope for v1.

## 5. Out of Scope

- A shared or centrally-hosted server deployment (v1 is single-developer, locally-hosted only).
- Multi-repo or multi-project orchestration within a single run.
- Support for tools other than Jira (e.g., GitLab, Azure DevOps, Linear).
- A UI or dashboard; all interaction is through the MCP client (AI assistant).
- Test execution, pull request creation, documentation updates, and release creation (the pipeline ends once the implementation branch is created; these remain manual steps for v1).

## 6. Constraints

- Must run as a locally-hosted process per developer machine.
- Must authenticate to Jira using a PAT/access token via the existing/official Jira MCP server, supplied as an environment variable.
- Internal Improving engineering use only; no client-confidential or PII data handling in v1.
- Per Improving's Third-Party Service Use Policy, this is built for use with Claude (Sonnet/Haiku) as the connected AI assistant.

## 7. Technology Stack

- **Language/Runtime**: Python, using the official MCP Python SDK — chosen for team familiarity and debuggability (primary developer is a Python developer).
- **Upstream integrations**: Official Atlassian/Jira MCP server, connected as a configurable child MCP server (URL/endpoint overridable via environment variables).
- **Execution model**: Locally-hosted process, one instance per developer, configured via environment variables for secrets and endpoints.
- **Code generation**: Delegated entirely to the calling AI assistant; this server does not generate source code itself.

## 8. Architecture Constraints

- Single-tenant, single-developer-process model — no shared state or multi-user coordination in v1.
- Repository and Jira project are selected per run, not fixed at server startup.
- The server acts as an orchestrator/MCP client-and-server hybrid: it exposes tools to the AI assistant and, in turn, calls the Jira MCP server as needed.
- No sandboxing/containerization layer for git operations in v1; branch creation runs directly in the developer's configured local environment.
- Approval gate is implemented as an explicit MCP tool call ("proceed"), not a UI element or Jira status transition.

## 9. Success Criteria

- A developer can call one Stage 1 tool with just a problem statement and project key and receive back a created Jira Feature with generated acceptance criteria, without manually drafting or writing the AC themselves.
- Story generation, estimation, per-story AC, and sprint scheduling for an approved feature happen from one Stage 2 tool call, not one tool call per story.
- No story creation occurs before the developer has approved the feature's acceptance criteria, and no coding activity occurs before the developer has explicitly triggered the "proceed" tool for that story.
- The server runs entirely from a developer's local machine using only environment-variable-supplied configuration, with no shared infrastructure required.

## 10. Open Questions

None outstanding — all resolved during interview. One documented assumption:
- Stage 1 and Stage 2 AC/story generation depend on the connected AI assistant supporting the MCP sampling capability. If a given client does not support sampling, those tools shall fail with a clear error rather than silently falling back to a lower-quality behavior; no non-sampling fallback is in scope for v1.
