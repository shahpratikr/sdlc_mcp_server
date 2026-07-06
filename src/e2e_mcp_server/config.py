from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """Runtime configuration for the server, sourced from environment variables only."""

    jira_mcp_url: str
    github_mcp_url: str
    jira_api_token: str
    github_token: str


def _require_env(name: str) -> str:
    """Read a required environment variable or raise ConfigError."""
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Required environment variable '{name}' is not set")
    return value


def load_config() -> Config:
    """Load server configuration from environment variables."""
    return Config(
        jira_mcp_url=_require_env("JIRA_MCP_URL"),
        github_mcp_url=_require_env("GITHUB_MCP_URL"),
        jira_api_token=_require_env("JIRA_API_TOKEN"),
        github_token=_require_env("GITHUB_TOKEN"),
    )
