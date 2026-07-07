"""Tests for the Phase 2 sampling-based AC generation helper."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.types import ImageContent, TextContent

from e2e_mcp_server.content_generation import (
    SamplingError,
    generate_feature_acceptance_criteria,
)


def _fake_ctx(content):
    ctx = MagicMock()
    result = MagicMock()
    result.content = content
    ctx.session.create_message = AsyncMock(return_value=result)
    return ctx


def test_generate_feature_acceptance_criteria_returns_sampled_text():
    ctx = _fake_ctx(TextContent(type="text", text="  - AC one\n- AC two  "))

    text = asyncio.run(
        generate_feature_acceptance_criteria(ctx, "Users need faster checkout"),
    )

    assert text == "- AC one\n- AC two"
    ctx.session.create_message.assert_awaited_once()
    _, kwargs = ctx.session.create_message.call_args
    assert kwargs["max_tokens"] > 0
    assert "Users need faster checkout" in kwargs["messages"][0].content.text


def test_generate_feature_acceptance_criteria_rejects_non_text_content():
    ctx = _fake_ctx(ImageContent(type="image", data="abc", mimeType="image/png"))

    with pytest.raises(SamplingError):
        asyncio.run(
            generate_feature_acceptance_criteria(ctx, "Users need faster checkout"),
        )
