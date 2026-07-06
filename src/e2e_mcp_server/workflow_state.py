"""In-process tracking of per-story approval-gate ('proceed') flags."""

from __future__ import annotations


class ApprovalGateError(Exception):
    """Raised when a coding-stage action is attempted before 'proceed' was called."""


class TestGateError(Exception):
    """Raised when PR creation is attempted after a failed, non-overridden test run."""


class WorkflowState:
    """Tracks per-story proceed flags in memory for the duration of a run."""

    def __init__(self) -> None:
        """Initialize with no stories approved yet."""
        self._approved_story_keys: set[str] = set()
        self._test_passed: dict[str, bool] = {}  #: last test run result per story
        self._test_override: set[str] = set()  #: developer override of a failed run

    def mark_proceed(self, issue_key: str) -> None:
        """Record that the developer has approved coding for a story."""
        self._approved_story_keys.add(issue_key)

    def is_approved(self, issue_key: str) -> bool:
        """Return whether 'proceed' has been called for the given story."""
        return issue_key in self._approved_story_keys

    def require_approval(self, issue_key: str) -> None:
        """Block coding-stage actions for a story until approved."""
        if not self.is_approved(issue_key):
            msg = f"Coding stage for '{issue_key}' is blocked until 'proceed' is called"
            raise ApprovalGateError(msg)

    def record_test_result(self, issue_key: str, *, passed: bool) -> None:
        """Record a story's test run outcome, resetting any prior override."""
        self._test_passed[issue_key] = passed
        self._test_override.discard(issue_key)

    def mark_test_override(self, issue_key: str) -> None:
        """Record the developer's explicit override of a failed test run."""
        self._test_override.add(issue_key)

    def require_tests_passed(self, issue_key: str) -> None:
        """Block PR creation for a story on a failed, non-overridden run."""
        if (
            self._test_passed.get(issue_key) is False
            and issue_key not in self._test_override
        ):
            msg = f"PR creation for '{issue_key}' is blocked: tests failed"
            raise TestGateError(msg)
