import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from e2e_mcp_server.config import Config
from e2e_mcp_server.jira_client import jira_session

TEST_CONFIG = Config(
    jira_mcp_url="http://localhost:9001/mcp",
    github_mcp_url="http://localhost:9002/mcp",
    jira_api_token="jira-token",  # noqa: S106
    github_token="github-token",  # noqa: S106
)


def test_jira_session_authenticates_with_bearer_token_and_initializes():
    fake_session = AsyncMock()

    @asynccontextmanager
    async def _fake_streamablehttp_client(url, headers=None):
        assert url == TEST_CONFIG.jira_mcp_url
        assert headers == {
            "Authorization": f"Bearer {TEST_CONFIG.jira_api_token}",
        }
        yield ("read_stream", "write_stream", "get_session_id")

    @asynccontextmanager
    async def _fake_client_session(read_stream, write_stream):
        yield fake_session

    async def _run():
        with (
            patch(
                "e2e_mcp_server.jira_client.streamablehttp_client",
                _fake_streamablehttp_client,
            ),
            patch("e2e_mcp_server.jira_client.ClientSession", _fake_client_session),
        ):
            async with jira_session(TEST_CONFIG) as session:
                assert session is fake_session

    asyncio.run(_run())
    fake_session.initialize.assert_awaited_once_with()
