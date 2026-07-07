"""In-process approval-gate state. PRD §3.2, §3.3, §3.4, §3.5 (Phases 3-6)."""

from __future__ import annotations

from dataclasses import dataclass, field


class FeatureNotApprovedError(Exception):
    """Raised when Stage 2 is attempted before the Stage 1 gate is passed. PRD §3.3."""


class StorySetNotApprovedError(Exception):
    """Raised when Stage 3 starts before the Stage 2 gate is passed. PRD §3.4."""


class StoryNotProceededError(Exception):
    """Raised when coding starts before "proceed" is called for a story. PRD §3.5."""


@dataclass
class WorkflowState:
    """Tracks per-feature and per-story approval-gate flags in memory. PRD §3.2/3.4."""

    _approved_features: set[str] = field(default_factory=set)
    _approved_story_sets: set[str] = field(default_factory=set)
    _proceeded_stories: set[str] = field(default_factory=set)

    def approve_feature(self, feature_key: str) -> None:
        """Mark a feature's Stage 1 acceptance criteria as approved. PRD §3.2."""
        self._approved_features.add(feature_key)

    def is_feature_approved(self, feature_key: str) -> bool:
        """Return whether Stage 2 may start for this feature. PRD §3.2."""
        return feature_key in self._approved_features

    def approve_story_set(self, feature_key: str) -> None:
        """Mark a feature's Stage 2 generated story set as approved. PRD §3.4."""
        self._approved_story_sets.add(feature_key)

    def reject_story_set(self, feature_key: str) -> None:
        """Clear a feature's Stage 2 story-set approval on regenerate. PRD §3.4."""
        self._approved_story_sets.discard(feature_key)

    def is_story_set_approved(self, feature_key: str) -> bool:
        """Return whether Stage 3 coding may start for this feature. PRD §3.4."""
        return feature_key in self._approved_story_sets

    def proceed(self, story_key: str) -> None:
        """Mark a user story as cleared to enter the coding stage. PRD §3.5."""
        self._proceeded_stories.add(story_key)

    def has_proceeded(self, story_key: str) -> bool:
        """Return whether the coding stage may start for this user story. PRD §3.5."""
        return story_key in self._proceeded_stories
