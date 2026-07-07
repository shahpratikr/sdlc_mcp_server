"""Sampling-based content generation (Phase 2: PRD §3.1, Phase 4: PRD §3.3)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from mcp.types import SamplingMessage, TextContent

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context

_FEATURE_AC_MAX_TOKENS = 1024
_STORY_LIST_MAX_TOKENS = 1536
_STORY_DETAIL_MAX_TOKENS = 512
_DEFAULT_STORY_POINTS = 1


class SamplingError(Exception):
    """Raised when the connected client's sampling response cannot be used."""


async def generate_feature_acceptance_criteria(
    ctx: Context,
    problem_statement: str,
) -> str:
    """Generate feature-level acceptance criteria via MCP sampling. PRD §3.1."""
    prompt = (
        "You are helping groom a Jira Feature. Draft clear, testable acceptance "
        "criteria for the feature described by the following problem statement. "
        "Return only the acceptance criteria as a concise bulleted list, with no "
        "additional commentary.\n\n"
        f"Problem statement: {problem_statement}"
    )
    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(role="user", content=TextContent(type="text", text=prompt)),
        ],
        max_tokens=_FEATURE_AC_MAX_TOKENS,
    )
    if not isinstance(result.content, TextContent):
        msg = "Sampling response did not contain text content"
        raise SamplingError(msg)
    return result.content.text.strip()


async def _sample_text(ctx: Context, prompt: str, max_tokens: int) -> str:
    """Request a text completion from the connected client via sampling. PRD §3.3."""
    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(role="user", content=TextContent(type="text", text=prompt)),
        ],
        max_tokens=max_tokens,
    )
    if not isinstance(result.content, TextContent):
        msg = "Sampling response did not contain text content"
        raise SamplingError(msg)
    return result.content.text.strip()


def _parse_story_list(raw_text: str) -> list[str]:
    """Parse a bulleted/numbered sampling response into story summaries. PRD §3.3."""
    stories = []
    for line in raw_text.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        if cleaned:
            stories.append(cleaned)
    if not stories:
        msg = "Sampling response did not contain any parsable user stories"
        raise SamplingError(msg)
    return stories


async def generate_user_stories(
    ctx: Context,
    feature_acceptance_criteria: str,
) -> list[str]:
    """Generate user story summaries satisfying the feature AC. PRD §3.3."""
    prompt = (
        "You are splitting an approved Jira Feature into user stories. Given the "
        "feature's approved acceptance criteria below, produce a set of user "
        "stories that collectively satisfy them. Return only the story summaries "
        "as a plain bulleted list, one story per line, with no additional "
        "commentary.\n\n"
        f"Feature acceptance criteria:\n{feature_acceptance_criteria}"
    )
    raw_text = await _sample_text(ctx, prompt, _STORY_LIST_MAX_TOKENS)
    return _parse_story_list(raw_text)


def _parse_story_detail(raw_text: str) -> tuple[str, int]:
    """Parse a sampled AC/POINTS response into AC text and points. PRD §3.3."""
    ac_match = re.search(r"AC:\s*(.*?)(?:\nPOINTS:|\Z)", raw_text, re.DOTALL)
    points_match = re.search(r"POINTS:\s*(\d+)", raw_text)
    acceptance_criteria = ac_match.group(1).strip() if ac_match else raw_text.strip()
    story_points = int(points_match.group(1)) if points_match else _DEFAULT_STORY_POINTS
    return acceptance_criteria, story_points


async def generate_story_acceptance_criteria_and_estimate(
    ctx: Context,
    story_summary: str,
) -> tuple[str, int]:
    """Generate a story's acceptance criteria and point estimate. PRD §3.3."""
    prompt = (
        "You are grooming a Jira user story. Given the story summary below, "
        "produce testable acceptance criteria and a story point estimate. "
        "Respond in exactly this format, with no additional commentary:\n"
        "AC: <bulleted acceptance criteria>\n"
        "POINTS: <integer story point estimate>\n\n"
        f"Story summary: {story_summary}"
    )
    raw_text = await _sample_text(ctx, prompt, _STORY_DETAIL_MAX_TOKENS)
    return _parse_story_detail(raw_text)
