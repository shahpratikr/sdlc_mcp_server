"""In-process approval-gate state. PRD §3.2, §3.3, §3.4, §3.5 (Phases 3-6, 8)."""

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
    """Tracks per-feature and per-story approval-gate flags, tagged by tracker, in memory. PRD §8."""

    # Keys are (tracker, identifier) tuples so identifiers are never compared across trackers. PRD §8.
    _approved_features: set[tuple[str, str]] = field(default_factory=set)
    _approved_story_sets: set[tuple[str, str]] = field(default_factory=set)
    _proceeded_stories: set[tuple[str, str]] = field(default_factory=set)
    _feature_by_story: dict[tuple[str, str], str] = field(default_factory=dict)

    def approve_feature(self, feature_key: str, tracker: str) -> None:
        """Mark a feature's Stage 1 acceptance criteria as approved. PRD §3.2/§8."""
        self._approved_features.add((tracker, feature_key))

    def is_feature_approved(self, feature_key: str, tracker: str) -> bool:
        """Return whether Stage 2 may start for this feature. PRD §3.2/§8."""
        return (tracker, feature_key) in self._approved_features

    def approve_story_set(self, feature_key: str, tracker: str) -> None:
        """Mark a feature's Stage 2 generated story set as approved. PRD §3.4/§8."""
        self._approved_story_sets.add((tracker, feature_key))

    def reject_story_set(self, feature_key: str, tracker: str) -> None:
        """Clear a feature's Stage 2 story-set approval on regenerate. PRD §3.4/§8."""
        self._approved_story_sets.discard((tracker, feature_key))

    def is_story_set_approved(self, feature_key: str, tracker: str) -> bool:
        """Return whether Stage 3 coding may start for this feature. PRD §3.4/§8."""
        return (tracker, feature_key) in self._approved_story_sets

    def register_story(self, story_key: str, feature_key: str, tracker: str) -> None:
        """Record which tracker and feature a generated story belongs to. PRD §3.3/§3.4/§8."""
        self._feature_by_story[(tracker, story_key)] = feature_key

    def proceed(self, story_key: str, tracker: str) -> None:
        """Mark a user story as cleared to enter the coding stage. PRD §3.5/§8.

        Requires the story's feature to have passed the Stage 2 story-set
        approval gate (PRD §3.4); raises StorySetNotApprovedError otherwise.
        """
        feature_key = self._feature_by_story.get((tracker, story_key))
        if feature_key is not None and not self.is_story_set_approved(
            feature_key,
            tracker,
        ):
            msg = f"Story '{story_key}' belongs to a feature whose story set has not been approved"
            raise StorySetNotApprovedError(msg)
        self._proceeded_stories.add((tracker, story_key))

    def has_proceeded(self, story_key: str, tracker: str) -> bool:
        """Return whether the coding stage may start for this user story. PRD §3.5/§8."""
        return (tracker, story_key) in self._proceeded_stories
