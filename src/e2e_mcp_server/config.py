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
    # GitHub fields are optional until a call uses tracker: github. PRD §4/§7, ARCHITECTURE Phase 8.
    github_mcp_url: str | None = None
    github_api_token: str | None = None


def _require_env(name: str) -> str:
    """Read a required environment variable or raise ConfigError."""
    value = os.environ.get(name)
    if not value:
        msg = f"Required environment variable '{name}' is not set"
        raise ConfigError(msg)
    return value


def _optional_env(name: str) -> str | None:
    """Read an optional environment variable, returning None if unset. ARCHITECTURE Phase 8."""
    return os.environ.get(name) or None


def load_config() -> Config:
    """Load server configuration from environment variables. R: Phase 1."""
    return Config(
        jira_mcp_url=_require_env("JIRA_MCP_URL"),
        jira_api_token=_require_env("JIRA_API_TOKEN"),
        github_mcp_url=_optional_env("GITHUB_MCP_URL"),
        github_api_token=_optional_env("GITHUB_API_TOKEN"),
    )
