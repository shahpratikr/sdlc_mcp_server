import pytest

from e2e_mcp_server.workflow_state import (
    ApprovalGateError,
    TestGateError,
    WorkflowState,
)


def test_story_is_not_approved_by_default():
    """Coding must not start until 'proceed' has been called."""
    state = WorkflowState()
    assert state.is_approved("PROJ-1") is False


def test_mark_proceed_approves_the_story():
    """'proceed' explicitly approves coding for a story."""
    state = WorkflowState()
    state.mark_proceed("PROJ-1")
    assert state.is_approved("PROJ-1") is True


def test_mark_proceed_does_not_approve_other_stories():
    """Approval gate is tracked per user story."""
    state = WorkflowState()
    state.mark_proceed("PROJ-1")
    assert state.is_approved("PROJ-2") is False


def test_require_approval_raises_when_not_approved():
    """coding-stage tools are blocked until 'proceed' is called."""
    state = WorkflowState()
    with pytest.raises(ApprovalGateError):
        state.require_approval("PROJ-1")


def test_require_approval_passes_once_approved():
    """Once approved, coding-stage actions are unblocked."""
    state = WorkflowState()
    state.mark_proceed("PROJ-1")
    state.require_approval("PROJ-1")


def test_require_tests_passed_allows_when_no_run_recorded():
    """PR gate is only enforced once a test result is on record."""
    state = WorkflowState()
    state.require_tests_passed("PROJ-1")


def test_require_tests_passed_allows_when_tests_passed():
    """PR creation proceeds once tests pass."""
    state = WorkflowState()
    state.record_test_result("PROJ-1", passed=True)
    state.require_tests_passed("PROJ-1")


def test_require_tests_passed_blocks_when_tests_failed():
    """PR creation is blocked on a failed test run."""
    state = WorkflowState()
    state.record_test_result("PROJ-1", passed=False)
    with pytest.raises(TestGateError):
        state.require_tests_passed("PROJ-1")


def test_require_tests_passed_allows_when_override_recorded():
    """An explicit developer override unblocks PR creation."""
    state = WorkflowState()
    state.record_test_result("PROJ-1", passed=False)
    state.mark_test_override("PROJ-1")
    state.require_tests_passed("PROJ-1")


def test_recording_new_test_result_clears_prior_override():
    """A fresh test run resets any previous override."""
    state = WorkflowState()
    state.record_test_result("PROJ-1", passed=False)
    state.mark_test_override("PROJ-1")
    state.record_test_result("PROJ-1", passed=False)
    with pytest.raises(TestGateError):
        state.require_tests_passed("PROJ-1")
