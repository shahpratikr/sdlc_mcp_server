"""In-process tracking of per-story approval-gate ('proceed') flags. PRD 3.3."""

from __future__ import annotations


class ApprovalGateError(Exception):
    """Raised when a coding-stage action is attempted before 'proceed' was called."""


class WorkflowState:
    """Tracks per-story proceed flags in memory for the duration of a run."""

    def __init__(self) -> None:
        """Initialize with no stories approved yet. PRD 3.3."""
        self._approved_story_keys: set[str] = set()

    def mark_proceed(self, issue_key: str) -> None:
        """Record that the developer has approved coding for a story. PRD 3.3."""
        self._approved_story_keys.add(issue_key)

    def is_approved(self, issue_key: str) -> bool:
        """Return whether 'proceed' has been called for the given story. PRD 3.3."""
        return issue_key in self._approved_story_keys

    def require_approval(self, issue_key: str) -> None:
        """Block coding-stage actions for a story until approved. PRD 3.3."""
        if not self.is_approved(issue_key):
            msg = f"Coding stage for '{issue_key}' is blocked until 'proceed' is called"
            raise ApprovalGateError(msg)
