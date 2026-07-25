"""Tests for the Phase 3/5/6/8 workflow state gates. docs/ARCHITECTURE.md Phase 3/5/6/8."""

import pytest

from e2e_mcp_server.workflow_state import StorySetNotApprovedError, WorkflowState


def test_feature_is_not_approved_by_default():
    state = WorkflowState()
    assert state.is_feature_approved("PROJ-1", "jira") is False


def test_approve_feature_marks_it_approved():
    state = WorkflowState()
    state.approve_feature("PROJ-1", "jira")
    assert state.is_feature_approved("PROJ-1", "jira") is True


def test_approving_one_feature_does_not_approve_another():
    state = WorkflowState()
    state.approve_feature("PROJ-1", "jira")
    assert state.is_feature_approved("PROJ-2", "jira") is False


def test_approving_a_feature_for_one_tracker_does_not_approve_it_for_another():
    state = WorkflowState()
    state.approve_feature("1", "github")
    assert state.is_feature_approved("1", "jira") is False


def test_story_set_is_not_approved_by_default():
    state = WorkflowState()
    assert state.is_story_set_approved("PROJ-1", "jira") is False


def test_approve_story_set_marks_it_approved():
    state = WorkflowState()
    state.approve_story_set("PROJ-1", "jira")
    assert state.is_story_set_approved("PROJ-1", "jira") is True


def test_reject_story_set_clears_approval():
    state = WorkflowState()
    state.approve_story_set("PROJ-1", "jira")
    state.reject_story_set("PROJ-1", "jira")
    assert state.is_story_set_approved("PROJ-1", "jira") is False


def test_reject_story_set_is_safe_when_not_previously_approved():
    state = WorkflowState()
    state.reject_story_set("PROJ-1", "jira")
    assert state.is_story_set_approved("PROJ-1", "jira") is False


def test_approving_one_feature_story_set_does_not_approve_another():
    state = WorkflowState()
    state.approve_story_set("PROJ-1", "jira")
    assert state.is_story_set_approved("PROJ-2", "jira") is False


def test_story_has_not_proceeded_by_default():
    state = WorkflowState()
    assert state.has_proceeded("PROJ-1", "jira") is False


def test_proceed_marks_story_as_proceeded():
    state = WorkflowState()
    state.proceed("PROJ-1", "jira")
    assert state.has_proceeded("PROJ-1", "jira") is True


def test_proceeding_one_story_does_not_proceed_another():
    state = WorkflowState()
    state.proceed("PROJ-1", "jira")
    assert state.has_proceeded("PROJ-2", "jira") is False


def test_proceed_allows_unregistered_story_through():
    state = WorkflowState()
    state.proceed("PROJ-1", "jira")
    assert state.has_proceeded("PROJ-1", "jira") is True


def test_proceed_blocks_registered_story_without_story_set_approval():
    state = WorkflowState()
    state.register_story("PROJ-2", "PROJ-1", "jira")

    with pytest.raises(StorySetNotApprovedError):
        state.proceed("PROJ-2", "jira")

    assert state.has_proceeded("PROJ-2", "jira") is False


def test_proceed_allows_registered_story_after_story_set_approval():
    state = WorkflowState()
    state.register_story("PROJ-2", "PROJ-1", "jira")
    state.approve_story_set("PROJ-1", "jira")

    state.proceed("PROJ-2", "jira")

    assert state.has_proceeded("PROJ-2", "jira") is True


def test_proceed_blocks_registered_story_after_story_set_rejected():
    state = WorkflowState()
    state.register_story("PROJ-2", "PROJ-1", "jira")
    state.approve_story_set("PROJ-1", "jira")
    state.reject_story_set("PROJ-1", "jira")

    with pytest.raises(StorySetNotApprovedError):
        state.proceed("PROJ-2", "jira")


def test_registered_story_is_tracker_scoped():
    state = WorkflowState()
    state.register_story("2", "1", "github")
    state.approve_story_set("1", "jira")

    with pytest.raises(StorySetNotApprovedError):
        state.proceed("2", "github")
