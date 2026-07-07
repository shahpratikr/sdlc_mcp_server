"""Tests for config.py env-var loading."""

import pytest

from e2e_mcp_server.config import Config, ConfigError, load_config

REQUIRED_VARS = {
    "JIRA_MCP_URL": "http://localhost:9001/mcp",
    "JIRA_API_TOKEN": "jira-token",
}


def _clear_env(monkeypatch):
    for key in REQUIRED_VARS:
        monkeypatch.delenv(key, raising=False)


def test_load_config_success(monkeypatch):
    _clear_env(monkeypatch)
    for key, value in REQUIRED_VARS.items():
        monkeypatch.setenv(key, value)

    config = load_config()

    assert isinstance(config, Config)
    assert config.jira_mcp_url == REQUIRED_VARS["JIRA_MCP_URL"]
    assert config.jira_api_token == REQUIRED_VARS["JIRA_API_TOKEN"]


@pytest.mark.parametrize("missing_var", list(REQUIRED_VARS))
def test_load_config_missing_var_raises(monkeypatch, missing_var):
    _clear_env(monkeypatch)
    for key, value in REQUIRED_VARS.items():
        if key != missing_var:
            monkeypatch.setenv(key, value)

    with pytest.raises(ConfigError):
        load_config()
