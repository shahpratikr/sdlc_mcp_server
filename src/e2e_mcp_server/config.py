from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """Runtime configuration for the server, sourced from environment variables only."""

    jira_mcp_url: str
    jira_api_token: str


def _require_env(name: str) -> str:
    """Read a required environment variable or raise ConfigError."""
    value = os.environ.get(name)
    if not value:
        msg = f"Required environment variable '{name}' is not set"
        raise ConfigError(msg)
    return value


def load_config() -> Config:
    """Load server configuration from environment variables. R: Phase 1."""
    return Config(
        jira_mcp_url=_require_env("JIRA_MCP_URL"),
        jira_api_token=_require_env("JIRA_API_TOKEN"),
    )
