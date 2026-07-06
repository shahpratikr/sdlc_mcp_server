# PRD: E2E Developer Workflow MCP Server

## 1. Problem Statement

Developers manually shepherd a feature from a problem statement through Jira grooming, coding, testing, PR creation, documentation, and release, switching tools and context at every step. This MCP server orchestrates that entire pipeline from a single input, delegating actual code generation to the connected AI assistant while automating the surrounding process.

## 2. Users

Software developers at Improving, working individually, who use an MCP-compatible AI assistant (e.g., Claude Code) as their interface. The tool is distributed as a team-wide capability, but each developer runs their own local instance configured with their own credentials.

## 3. MVP Features

### 3.1 Feature Creation from Problem Statement
- The system shall accept a problem statement as input and create a corresponding Jira Feature via the Jira MCP server.
- The system shall allow the target Jira project to be specified per run.

### 3.2 Refinement, Estimation, Assignment, Scheduling
- The system shall refine a Jira Feature into one or more user stories.
- The system shall generate a story point estimate for each user story.
- The system shall write the generated estimate to each user story in Jira.
- The system shall support assigning each user story to a developer in Jira.
- The system shall support scheduling each user story into a sprint, using read access to the Jira board/sprint structure to select or confirm the target sprint.

### 3.3 Pre-Coding Approval Gate
- The system shall expose a "proceed" tool that must be explicitly called before the coding stage begins for a given user story.
- The system shall not start the coding stage for a user story until the "proceed" tool has been called for it.

### 3.4 Coding (Delegated Implementation)
- The system shall delegate generation of implementation code for a user story to the calling AI assistant; the server itself shall not generate source code.
- The system shall create a git branch for the user story implementation in the repository selected for that run.
- The system shall support a repository being selected per run (not fixed per server instance).

### 3.5 Test Verification
- The system shall execute the project's test suite in the developer's local environment after implementation.
- The system shall report pass/fail results of the test run back to the calling AI assistant.
- The system shall block PR creation if the test run fails, unless explicitly overridden by the developer.

### 3.6 Pull Request Creation
- The system shall create a GitHub pull request via the GitHub MCP server once tests pass.
- The system shall link the pull request description back to the originating Jira user story.
- The system shall not automatically merge pull requests.

### 3.7 Documentation
- The system shall update the repository's README to reflect the implemented changes.

### 3.8 Release
- The system shall create a GitHub Release (tag and release notes) representing the completed work.

## 4. Non-Functional Requirements

- **Security**: All credentials (Jira PAT, GitHub token, and any other secrets required by the underlying GitHub/Jira MCP servers) shall be supplied via environment variables; the system shall not persist secrets to disk.
- **Configurability**: The Jira MCP server URL and GitHub MCP server URL/endpoint shall be configurable via environment variables, not hardcoded.
- **Secure coding**: The system shall instruct/guide the AI assistant to follow secure coding practices during the delegated coding stage (the server does not itself statically enforce this in v1).
- **Data handling**: The system is for Improving's internal engineering work only; no client-confidential data is in scope for v1.

## 5. Out of Scope

- Automatic pull request merging.
- A shared or centrally-hosted server deployment (v1 is single-developer, locally-hosted only).
- Multi-repo or multi-project orchestration within a single run.
- Support for tools other than Jira and GitHub (e.g., GitLab, Azure DevOps, Linear).
- A UI or dashboard; all interaction is through the MCP client (AI assistant).
- Containerized or sandboxed test execution (tests run in the developer's local environment for v1).

## 6. Constraints

- Must run as a locally-hosted process per developer machine.
- Must authenticate to Jira and GitHub using PATs/access tokens via existing/official Jira and GitHub MCP servers, supplied as environment variables.
- Internal Improving engineering use only; no client-confidential or PII data handling in v1.
- Per Improving's Third-Party Service Use Policy, this is built for use with Claude (Sonnet/Haiku) as the connected AI assistant.

## 7. Technology Stack

- **Language/Runtime**: Python, using the official MCP Python SDK — chosen for team familiarity and debuggability (primary developer is a Python developer).
- **Upstream integrations**: Official GitHub MCP server and official Atlassian/Jira MCP server, connected as configurable child MCP servers (URLs/endpoints overridable via environment variables).
- **Execution model**: Locally-hosted process, one instance per developer, configured via environment variables for secrets and endpoints.
- **Code generation**: Delegated entirely to the calling AI assistant; this server does not generate source code itself.

## 8. Architecture Constraints

- Single-tenant, single-developer-process model — no shared state or multi-user coordination in v1.
- Repository and Jira project are selected per run, not fixed at server startup.
- The server acts as an orchestrator/MCP client-and-server hybrid: it exposes tools to the AI assistant and, in turn, calls the Jira and GitHub MCP servers as needed.
- No sandboxing/containerization layer for test execution in v1; tests run directly in the developer's configured local environment.
- Approval gate is implemented as an explicit MCP tool call ("proceed"), not a UI element or Jira status transition.

## 9. Success Criteria

- A developer can submit a single problem statement and have a Jira Feature, refined stories with estimates/assignees/sprint scheduling created without manual Jira interaction.
- No coding activity occurs before the developer has explicitly triggered the "proceed" tool.
- Implemented user stories have passing tests verified by an actual test run before a PR is opened.
- Every PR created traces back to its originating Jira story.
- README updates and a GitHub Release are produced as part of the completed workflow without manual doc/release steps.
- The server runs entirely from a developer's local machine using only environment-variable-supplied configuration, with no shared infrastructure required.

## 10. Open Questions

None outstanding — all resolved during interview. One documented assumption: test execution runs unsandboxed in the developer's local environment for v1 (no containerization), to be revisited if this proves unsafe or inconsistent across machines.
