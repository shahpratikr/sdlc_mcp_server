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


def _approve_story_set(
    workflow_state: WorkflowState,
    feature_key: str,
    *,
    regenerate: bool,
) -> dict[str, str]:
    """Stage 2 approval gate: approve or request regeneration of stories. PRD §3.4."""
    if regenerate:
        workflow_state.reject_story_set(feature_key)
        return {"feature_key": feature_key, "status": "regeneration_requested"}
    workflow_state.approve_story_set(feature_key)
    return {"feature_key": feature_key, "status": "approved"}


def _proceed(workflow_state: WorkflowState, story_key: str) -> dict[str, str]:
    """Pre-coding approval gate: clears a story for coding. PRD §3.5."""
    workflow_state.proceed(story_key)
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
    repository_path: str,
) -> dict[str, str]:
    """Create the implementation branch for a proceeded user story. PRD §3.6."""
    if not workflow_state.has_proceeded(story_key):
        msg = f"Story '{story_key}' has not passed the pre-coding approval gate"
        raise StoryNotProceededError(msg)
    branch_name = _branch_name_for_story(story_key)
    _create_git_branch(repository_path, branch_name)
    return {"story_key": story_key, "branch_name": branch_name, "status": "created"}


def create_server(config: Config) -> FastMCP:  # noqa: C901
    """Build and return the MCP server instance for this run. R: Phase 1."""
    mcp_server = FastMCP("e2e-developer-workflow")
    workflow_state = WorkflowState()

    @mcp_server.tool()
    def ping() -> str:
        """Health-check tool confirming the server is running and connectable."""
        return "pong"

    @mcp_server.tool()
    async def start_feature(
        problem_statement: str,
        project_key: str,
        ctx: Context,
    ) -> dict[str, str]:
        """Stage 1: generate AC via sampling, create the Jira Feature. PRD §3.1."""
        acceptance_criteria = await generate_feature_acceptance_criteria(
            ctx,
            problem_statement,
        )
        async with jira_session(config) as session:
            feature_key = await create_feature(
                session,
                project_key,
                problem_statement,
                acceptance_criteria,
            )
        return {"feature_key": feature_key, "acceptance_criteria": acceptance_criteria}

    @mcp_server.tool()
    async def approve_feature_acceptance_criteria(
        feature_key: str,
        edited_acceptance_criteria: str | None = None,
    ) -> dict[str, str]:
        """Stage 1 approval gate: approve or edit feature AC. PRD §3.2."""
        if edited_acceptance_criteria is not None:
            async with jira_session(config) as session:
                await update_feature_acceptance_criteria(
                    session,
                    feature_key,
                    edited_acceptance_criteria,
                )
        workflow_state.approve_feature(feature_key)
        return {"feature_key": feature_key, "status": "approved"}

    @mcp_server.tool()
    async def generate_stories_for_feature(
        feature_key: str,
        board: str,
        sprint: str,
        ctx: Context,
        assignee: str | None = None,
    ) -> dict[str, object]:
        """Stage 2: generate, create, estimate, and schedule stories. PRD §3.3."""
        if not workflow_state.is_feature_approved(feature_key):
            msg = f"Feature '{feature_key}' has not passed the Stage 1 approval gate"
            raise FeatureNotApprovedError(msg)
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
                    await generate_story_acceptance_criteria_and_estimate(ctx, summary)
                )
                story_key = await create_story(session, project_key, summary)
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
        return {"feature_key": feature_key, "stories": created_stories}

    @mcp_server.tool()
    def approve_story_set(
        feature_key: str,
        *,
        regenerate: bool = False,
    ) -> dict[str, str]:
        """Stage 2 approval gate tool wrapper. PRD §3.4."""
        return _approve_story_set(workflow_state, feature_key, regenerate=regenerate)

    @mcp_server.tool()
    def proceed(story_key: str) -> dict[str, str]:
        """Pre-coding approval gate tool wrapper. PRD §3.5."""
        return _proceed(workflow_state, story_key)

    @mcp_server.tool()
    def create_implementation_branch(
        story_key: str,
        repository_path: str,
    ) -> dict[str, str]:
        """Coding stage: create the story's git branch in the run's repo. PRD §3.6."""
        return _create_implementation_branch(workflow_state, story_key, repository_path)

    return mcp_server


def run_server(config: Config) -> None:
    """Start the MCP server for this run using the given configuration. R: Phase 1."""
    server = create_server(config)
    server.run()
