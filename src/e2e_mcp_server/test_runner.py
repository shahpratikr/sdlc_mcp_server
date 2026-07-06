"""Executes the project's test suite locally and reports pass/fail."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class TestRunResult:
    """Outcome of a local test suite execution."""

    passed: bool
    output: str


def run_test_suite(repository_path: str, test_command: str) -> TestRunResult:
    """Run the project's test suite unsandboxed in the local environment."""
    result = subprocess.run(  # noqa: S603
        shlex.split(test_command),
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_output = result.stdout + result.stderr
    return TestRunResult(passed=result.returncode == 0, output=combined_output)
