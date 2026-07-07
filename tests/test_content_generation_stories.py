"""Tests for the Phase 4 sampling-based story generation helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.types import ImageContent, TextContent

from e2e_mcp_server.content_generation import (
    SamplingError,
    generate_story_acceptance_criteria_and_estimate,
    generate_user_stories,
)

_EXPECTED_STORY_POINTS = 3


def _fake_ctx(content):
    ctx = MagicMock()
    result = MagicMock()
    result.content = content
    ctx.session.create_message = AsyncMock(return_value=result)
    return ctx


def test_generate_user_stories_parses_bulleted_list():
    ctx = _fake_ctx(TextContent(type="text", text="- Story one\n- Story two\n"))

    stories = asyncio.run(generate_user_stories(ctx, "- feature AC one"))

    assert stories == ["Story one", "Story two"]
    ctx.session.create_message.assert_awaited_once()
    _, kwargs = ctx.session.create_message.call_args
    assert "feature AC one" in kwargs["messages"][0].content.text


def test_generate_user_stories_rejects_non_text_content():
    ctx = _fake_ctx(ImageContent(type="image", data="abc", mimeType="image/png"))

    with pytest.raises(SamplingError):
        asyncio.run(generate_user_stories(ctx, "- feature AC one"))


def test_generate_user_stories_rejects_empty_result():
    ctx = _fake_ctx(TextContent(type="text", text="   \n  "))

    with pytest.raises(SamplingError):
        asyncio.run(generate_user_stories(ctx, "- feature AC one"))


def test_generate_story_acceptance_criteria_and_estimate_parses_response():
    ctx = _fake_ctx(
        TextContent(type="text", text="AC: - story AC one\n- story AC two\nPOINTS: 3"),
    )

    acceptance_criteria, story_points = asyncio.run(
        generate_story_acceptance_criteria_and_estimate(ctx, "As a user, I want X"),
    )

    assert acceptance_criteria == "- story AC one\n- story AC two"
    assert story_points == _EXPECTED_STORY_POINTS
    ctx.session.create_message.assert_awaited_once()
    _, kwargs = ctx.session.create_message.call_args
    assert "As a user, I want X" in kwargs["messages"][0].content.text


def test_generate_story_acceptance_criteria_and_estimate_defaults_when_unparsed():
    ctx = _fake_ctx(TextContent(type="text", text="freeform response with no markers"))

    acceptance_criteria, story_points = asyncio.run(
        generate_story_acceptance_criteria_and_estimate(ctx, "As a user, I want X"),
    )

    assert acceptance_criteria == "freeform response with no markers"
    assert story_points == 1
