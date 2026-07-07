"""Tests for the Phase 3/5/6 workflow state gates. docs/ARCHITECTURE.md Phase 3/5/6."""

from e2e_mcp_server.workflow_state import WorkflowState


def test_feature_is_not_approved_by_default():
    state = WorkflowState()
    assert state.is_feature_approved("PROJ-1") is False


def test_approve_feature_marks_it_approved():
    state = WorkflowState()
    state.approve_feature("PROJ-1")
    assert state.is_feature_approved("PROJ-1") is True


def test_approving_one_feature_does_not_approve_another():
    state = WorkflowState()
    state.approve_feature("PROJ-1")
    assert state.is_feature_approved("PROJ-2") is False


def test_story_set_is_not_approved_by_default():
    state = WorkflowState()
    assert state.is_story_set_approved("PROJ-1") is False


def test_approve_story_set_marks_it_approved():
    state = WorkflowState()
    state.approve_story_set("PROJ-1")
    assert state.is_story_set_approved("PROJ-1") is True


def test_reject_story_set_clears_approval():
    state = WorkflowState()
    state.approve_story_set("PROJ-1")
    state.reject_story_set("PROJ-1")
    assert state.is_story_set_approved("PROJ-1") is False


def test_reject_story_set_is_safe_when_not_previously_approved():
    state = WorkflowState()
    state.reject_story_set("PROJ-1")
    assert state.is_story_set_approved("PROJ-1") is False


def test_approving_one_feature_story_set_does_not_approve_another():
    state = WorkflowState()
    state.approve_story_set("PROJ-1")
    assert state.is_story_set_approved("PROJ-2") is False


def test_story_has_not_proceeded_by_default():
    state = WorkflowState()
    assert state.has_proceeded("PROJ-1") is False


def test_proceed_marks_story_as_proceeded():
    state = WorkflowState()
    state.proceed("PROJ-1")
    assert state.has_proceeded("PROJ-1") is True


def test_proceeding_one_story_does_not_proceed_another():
    state = WorkflowState()
    state.proceed("PROJ-1")
    assert state.has_proceeded("PROJ-2") is False
