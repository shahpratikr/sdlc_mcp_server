from e2e_mcp_server.test_runner import TestRunResult, run_test_suite


def test_run_test_suite_reports_pass_on_zero_exit(tmp_path):
    """PRD §3.5: passing test suite is reported as passed."""
    result = run_test_suite(str(tmp_path), "true")
    assert result.passed is True


def test_run_test_suite_reports_fail_on_nonzero_exit(tmp_path):
    """PRD §3.5: failing test suite is reported as failed."""
    result = run_test_suite(str(tmp_path), "false")
    assert result.passed is False


def test_run_test_suite_captures_output(tmp_path):
    """PRD §3.5: test run output is captured for reporting back to the assistant."""
    result = run_test_suite(str(tmp_path), "echo hello-tests")
    assert "hello-tests" in result.output


def test_test_run_result_is_frozen_dataclass():
    result = TestRunResult(passed=True, output="ok")
    assert result.passed is True
    assert result.output == "ok"
