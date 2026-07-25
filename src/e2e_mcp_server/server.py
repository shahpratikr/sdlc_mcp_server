"""MCP server scaffold exposing workflow tools to the calling AI assistant."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from mcp.server.fastmcp import Context, FastMCP

from e2e_mcp_server.content_generation import (
    generate_feature_acceptance_criteria,
    generate_story_acceptance_criteria_and_estimate,
    generate_user_stories,
)
from e2e_mcp_server.github_client import (
    assign_issue,
    create_feature_issue,
    create_story_issue,
    get_feature_issue_body,
    github_session,
    update_feature_issue_body,
)
from e2e_mcp_server.jira_client import (
    assign_story,
    create_feature,
    create_story,
    get_feature_acceptance_criteria,
    jira_session,
    project_key_from_issue_key,
    schedule_story_into_sprint,
    update_feature_acceptance_criteria,
    update_story_estimate_and_acceptance_criteria,
)
from e2e_mcp_server.workflow_state import (
    FeatureNotApprovedError,
    StoryNotProceededError,
    WorkflowState,
)

if TYPE_CHECKING:
    from e2e_mcp_server.config import Config

_TRACKERS = ("jira", "github")


class TrackerArgumentError(ValueError):
    """Raised when a tool's arguments don't match its `tracker` value. PRD §3.1."""


def _validate_tracker(tracker: str) -> None:
    """Reject any tracker value other than 'jira' or 'github'. PRD §3.1-§3.6."""
    if tracker not in _TRACKERS:
        msg = f"tracker must be one of {_TRACKERS}, got '{tracker}'"
        raise TrackerArgumentError(msg)


def _validate_jira_only(tracker: str, **github_only_args: object) -> None:
    """Reject GitHub-only arguments when tracker is jira. PRD §3.1-§3.3."""
    if tracker == "github":
        return
    supplied = [name for name, value in github_only_args.items() if value is not None]
    if supplied:
        msg = f"tracker 'jira' does not accept argument(s): {', '.join(supplied)}"
        raise TrackerArgumentError(msg)


def _validate_github_only(tracker: str, **jira_only_args: object) -> None:
    """Reject Jira-only arguments when tracker is github. PRD §3.1-§3.3."""
    if tracker == "jira":
        return
    supplied = [name for name, value in jira_only_args.items() if value is not None]
    if supplied:
        msg = f"tracker 'github' does not accept argument(s): {', '.join(supplied)}"
        raise TrackerArgumentError(msg)


def _require(tracker: str, **required_args: object) -> None:
    """Require the given tracker-specific arguments to be present. PRD §3.1-§3.3."""
    missing = [name for name, value in required_args.items() if value is None]
    if missing:
        msg = f"tracker '{tracker}' requires argument(s): {', '.join(missing)}"
        raise TrackerArgumentError(msg)


def _approve_story_set(
    workflow_state: WorkflowState,
    feature_key: str,
    tracker: str,
    *,
    regenerate: bool,
) -> dict[str, str]:
    """Stage 2 approval gate: approve or request regeneration of stories. PRD §3.4."""
    _validate_tracker(tracker)
    if regenerate:
        workflow_state.reject_story_set(feature_key, tracker)
        return {"feature_key": feature_key, "status": "regeneration_requested"}
    workflow_state.approve_story_set(feature_key, tracker)
    return {"feature_key": feature_key, "status": "approved"}


def _proceed(
    workflow_state: WorkflowState,
    story_key: str,
    tracker: str,
) -> dict[str, str]:
    """Pre-coding approval gate: clears a story for coding. PRD §3.5."""
    _validate_tracker(tracker)
    workflow_state.proceed(story_key, tracker)
    return {"story_key": story_key, "status": "proceeded"}


class GitBranchError(Exception):
    """Raised when git branch creation for a user story fails. PRD §3.6."""


def _branch_name_for_story(story_key: str) -> str:
    """Derive the implementation branch name for a user story. PRD §3.6."""
    return f"story/{story_key.lower()}"


def _create_git_branch(repository_path: str, branch_name: str) -> None:
    """Create a git branch via subprocess in the selected repository. PRD §3.6."""
    result = subprocess.run(  # noqa: S603
        ["git", "-C", repository_path, "checkout", "-b", branch_name],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git branch creation failed: {result.stderr.strip()}"
        raise GitBranchError(msg)


def _create_implementation_branch(
    workflow_state: WorkflowState,
    story_key: str,
    tracker: str,
    repository_path: str,
) -> dict[str, str]:
    """Create the implementation branch for a proceeded user story. PRD §3.6."""
    _validate_tracker(tracker)
    if not workflow_state.has_proceeded(story_key, tracker):
        msg = f"Story '{story_key}' has not passed the pre-coding approval gate"
        raise StoryNotProceededError(msg)
    branch_name = _branch_name_for_story(story_key)
    _create_git_branch(repository_path, branch_name)
    return {"story_key": story_key, "branch_name": branch_name, "status": "created"}


def create_server(config: Config) -> FastMCP:  # noqa: C901, PLR0915
    """Build and return the MCP server instance for this run. R: Phase 1."""
    mcp_server = FastMCP("e2e-developer-workflow")
    workflow_state = WorkflowState()

    @mcp_server.tool()
    def ping() -> str:
        """Health-check tool confirming the server is running and connectable."""
        return "pong"

    @mcp_server.tool()
    async def start_feature(  # noqa: PLR0913
        problem_statement: str,
        tracker: str,
        ctx: Context,
        project_key: str | None = None,
        repo_owner: str | None = None,
        repo_name: str | None = None,
    ) -> dict[str, str]:
        """Stage 1: generate AC, create the Feature/parent Issue. PRD §3.1."""
        _validate_tracker(tracker)
        _validate_jira_only(tracker, repo_owner=repo_owner, repo_name=repo_name)
        _validate_github_only(tracker, project_key=project_key)
        acceptance_criteria = await generate_feature_acceptance_criteria(
            ctx,
            problem_statement,
        )
        if tracker == "jira":
            _require(tracker, project_key=project_key)
            async with jira_session(config) as session:
                feature_key = await create_feature(
                    session,
                    project_key,
                    problem_statement,
                    acceptance_criteria,
                )
        else:
            _require(tracker, repo_owner=repo_owner, repo_name=repo_name)
            async with github_session(config) as session:
                feature_key = await create_feature_issue(
                    session,
                    repo_owner,
                    repo_name,
                    problem_statement,
                    acceptance_criteria,
                )
        return {"feature_key": feature_key, "acceptance_criteria": acceptance_criteria}

    @mcp_server.tool()
    async def approve_feature_acceptance_criteria(
        feature_key: str,
        tracker: str,
        edited_acceptance_criteria: str | None = None,
        repo_owner: str | None = None,
        repo_name: str | None = None,
    ) -> dict[str, str]:
        """Stage 1 approval gate: approve or edit feature AC. PRD §3.2."""
        _validate_tracker(tracker)
        _validate_jira_only(tracker, repo_owner=repo_owner, repo_name=repo_name)
        if tracker == "github":
            _require(tracker, repo_owner=repo_owner, repo_name=repo_name)
        if edited_acceptance_criteria is not None:
            if tracker == "jira":
                async with jira_session(config) as session:
                    await update_feature_acceptance_criteria(
                        session,
                        feature_key,
                        edited_acceptance_criteria,
                    )
            else:
                async with github_session(config) as session:
                    await update_feature_issue_body(
                        session,
                        repo_owner,
                        repo_name,
                        feature_key,
                        edited_acceptance_criteria,
                    )
        workflow_state.approve_feature(feature_key, tracker)
        return {"feature_key": feature_key, "status": "approved"}

    @mcp_server.tool()
    async def generate_stories_for_feature(  # noqa: PLR0913
        feature_key: str,
        tracker: str,
        ctx: Context,
        board: str | None = None,
        sprint: str | None = None,
        assignee: str | None = None,
        repo_owner: str | None = None,
        repo_name: str | None = None,
    ) -> dict[str, object]:
        """Stage 2: generate/create stories; Jira only estimates/schedules. PRD §3.3."""
        _validate_tracker(tracker)
        _validate_jira_only(tracker, repo_owner=repo_owner, repo_name=repo_name)
        _validate_github_only(tracker, board=board, sprint=sprint)
        if not workflow_state.is_feature_approved(feature_key, tracker):
            msg = f"Feature '{feature_key}' has not passed the Stage 1 approval gate"
            raise FeatureNotApprovedError(msg)

        if tracker == "jira":
            _require(tracker, board=board, sprint=sprint)
            project_key = project_key_from_issue_key(feature_key)
            async with jira_session(config) as session:
                feature_acceptance_criteria = await get_feature_acceptance_criteria(
                    session,
                    feature_key,
                )
                story_summaries = await generate_user_stories(
                    ctx,
                    feature_acceptance_criteria,
                )
                created_stories = []
                for summary in story_summaries:
                    acceptance_criteria, story_points = (
                        await generate_story_acceptance_criteria_and_estimate(
                            ctx,
                            summary,
                        )
                    )
                    story_key = await create_story(session, project_key, summary)
                    workflow_state.register_story(story_key, feature_key, tracker)
                    await update_story_estimate_and_acceptance_criteria(
                        session,
                        story_key,
                        story_points,
                        acceptance_criteria,
                    )
                    await schedule_story_into_sprint(session, story_key, board, sprint)
                    if assignee is not None:
                        await assign_story(session, story_key, assignee)
                    created_stories.append(
                        {
                            "story_key": story_key,
                            "summary": summary,
                            "story_points": story_points,
                            "acceptance_criteria": acceptance_criteria,
                        },
                    )
        else:
            _require(tracker, repo_owner=repo_owner, repo_name=repo_name)
            async with github_session(config) as session:
                feature_acceptance_criteria = await get_feature_issue_body(
                    session,
                    repo_owner,
                    repo_name,
                    feature_key,
                )
                story_summaries = await generate_user_stories(
                    ctx,
                    feature_acceptance_criteria,
                )
                created_stories = []
                for summary in story_summaries:
                    acceptance_criteria, _story_points = (
                        await generate_story_acceptance_criteria_and_estimate(
                            ctx,
                            summary,
                        )
                    )
                    story_key = await create_story_issue(
                        session,
                        repo_owner,
                        repo_name,
                        feature_key,
                        summary,
                        acceptance_criteria,
                    )
                    workflow_state.register_story(story_key, feature_key, tracker)
                    if assignee is not None:
                        await assign_issue(
                            session,
                            repo_owner,
                            repo_name,
                            story_key,
                            assignee,
                        )
                    created_stories.append(
                        {
                            "story_key": story_key,
                            "summary": summary,
                            "acceptance_criteria": acceptance_criteria,
                        },
                    )
        return {"feature_key": feature_key, "stories": created_stories}

    @mcp_server.tool()
    def approve_story_set(
        feature_key: str,
        tracker: str,
        *,
        regenerate: bool = False,
    ) -> dict[str, str]:
        """Stage 2 approval gate tool wrapper. PRD §3.4."""
        return _approve_story_set(
            workflow_state,
            feature_key,
            tracker,
            regenerate=regenerate,
        )

    @mcp_server.tool()
    def proceed(story_key: str, tracker: str) -> dict[str, str]:
        """Pre-coding approval gate tool wrapper. PRD §3.5."""
        return _proceed(workflow_state, story_key, tracker)

    @mcp_server.tool()
    def create_implementation_branch(
        story_key: str,
        tracker: str,
        repository_path: str,
    ) -> dict[str, str]:
        """Coding stage: create the story's git branch in the run's repo. PRD §3.6."""
        return _create_implementation_branch(
            workflow_state,
            story_key,
            tracker,
            repository_path,
        )

    return mcp_server


def run_server(config: Config) -> None:
    """Start the MCP server for this run using the given configuration. R: Phase 1."""
    server = create_server(config)
    server.run()
