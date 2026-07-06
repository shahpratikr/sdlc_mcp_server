import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from e2e_mcp_server.config import Config
from e2e_mcp_server.github_client import (
    create_pull_request,
    create_release,
    github_session,
)

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    github_mcp_url="http://localhost:9002/mcp",
    jira_api_token="jira-token",  # noqa: S106
    github_token="github-token",  # noqa: S106
)


def test_github_session_authenticates_with_bearer_token_and_initializes():
    fake_session = AsyncMock()

    @asynccontextmanager
    async def _fake_streamablehttp_client(url, headers=None):
        assert url == TEST_CONFIG.github_mcp_url
        assert headers == {
            "Authorization": f"Bearer {TEST_CONFIG.github_token}",
        }
        yield ("read_stream", "write_stream", "get_session_id")

    @asynccontextmanager
    async def _fake_client_session(read_stream, write_stream):
        yield fake_session

    async def _run():
        with (
            patch(
                "e2e_mcp_server.github_client.streamablehttp_client",
                _fake_streamablehttp_client,
            ),
            patch("e2e_mcp_server.github_client.ClientSession", _fake_client_session),
        ):
            async with github_session(TEST_CONFIG) as session:
                assert session is fake_session

    asyncio.run(_run())
    fake_session.initialize.assert_awaited_once_with()


def test_create_pull_request_calls_github_mcp_tool_and_links_jira_story():
    fake_session = AsyncMock()
    fake_content = AsyncMock()
    fake_content.text = "PR created: #42"
    fake_result = AsyncMock()
    fake_result.content = [fake_content]
    fake_session.call_tool.return_value = fake_result

    async def _run():
        return await create_pull_request(
            fake_session,
            "org/repo",
            "feature/proj-2",
            "main",
            "PROJ-2",
            "Implement PROJ-2",
        )

    text = asyncio.run(_run())

    assert text == "PR created: #42"
    fake_session.call_tool.assert_awaited_once_with(
        "createPullRequest",
        {
            "repository": "org/repo",
            "head": "feature/proj-2",
            "base": "main",
            "title": "Implement PROJ-2",
            "body": "Resolves PROJ-2\n\nLinked Jira story: PROJ-2",
        },
    )


def test_create_release_calls_github_mcp_tool():
    fake_session = AsyncMock()
    fake_content = AsyncMock()
    fake_content.text = "Release created: v1.0.0"
    fake_result = AsyncMock()
    fake_result.content = [fake_content]
    fake_session.call_tool.return_value = fake_result

    async def _run():
        return await create_release(
            fake_session,
            "org/repo",
            "v1.0.0",
            "Completed PROJ-2.",
        )

    text = asyncio.run(_run())

    assert text == "Release created: v1.0.0"
    fake_session.call_tool.assert_awaited_once_with(
        "createRelease",
        {
            "repository": "org/repo",
            "tag_name": "v1.0.0",
            "body": "Completed PROJ-2.",
        },
    )
