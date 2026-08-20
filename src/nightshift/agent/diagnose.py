"""Diagnostic workflow engine for safe, autonomous repository inspection."""

import re
from pathlib import Path
from pydantic import BaseModel

from nightshift.policy.engine import AutonomyDecision, PolicyEngine
from nightshift.sandbox.runner import CommandResult, create_sandbox


class DiagnosticReport(BaseModel):
    """Structured diagnostic result generated from repository analysis."""

    repo_path: str
    test_command: str
    tests_passed: bool
    exit_code: int
    duration_ms: float
    error_summary: str | None
    failing_test_name: str | None
    suspect_file: str | None
    suspect_line_number: int | None
    exception_type: str | None
    policy_check: AutonomyDecision | None
    stdout_sample: str
    stderr_sample: str


class DiagnosticEngine:
    """Performs read-only safe diagnostic runs on a target repository."""

    def __init__(self, policy_engine: PolicyEngine | None = None):
        self.policy_engine = policy_engine or PolicyEngine()

    def run_diagnostic(
        self,
        repo_path: str,
        test_command: str = "pytest",
    ) -> DiagnosticReport:
        """Run safe sandboxed test execution and parse diagnostic signals."""
        target_path = Path(repo_path).resolve()
        if not target_path.exists():
            raise FileNotFoundError(f"Repository path '{repo_path}' does not exist.")

        # 1. Execute tests inside isolated sandbox
        sandbox = create_sandbox()
        try:
            sandbox.setup_workspace(target_path)
            cmd_result: CommandResult = sandbox.run_command(test_command)
        finally:
            sandbox.cleanup()

        # 2. Parse results
        tests_passed = cmd_result.success
        error_summary = None
        failing_test = None
        suspect_file = None
        suspect_line = None
        exception_type = None
        policy_decision = None

        if not tests_passed:
            combined = f"{cmd_result.stdout}\n{cmd_result.stderr}"

            # Extract failing test name (e.g. FAILED test_data_pipeline.py::test_process_event_with_missing_or_null_metadata)
            match_test = re.search(r"FAILED\s+([^\s:]+)::([^\s]+)", combined)
            if match_test:
                failing_test = f"{match_test.group(1)}::{match_test.group(2)}"

            # Extract exception type (e.g. TypeError: 'NoneType' object is not subscriptable)
            match_exc = re.findall(r"([A-Za-z]+Error:[^\n]+)", combined)
            if match_exc:
                exception_type = match_exc[-1].strip()
                error_summary = exception_type

            # Extract all file:line occurrences in the traceback and pick the innermost location
            # Pytest format: "data_pipeline.py:17: TypeError" or "test_data_pipeline.py:26: ..."
            loc_matches = re.findall(r"([a-zA-Z0-9_\-\./]+\.py):(\d+):", combined)
            if loc_matches:
                # Find the frame right before the final exception
                suspect_file = loc_matches[-1][0]
                suspect_line = int(loc_matches[-1][1])

            # Evaluate policy check on suspect file
            if suspect_file:
                policy_decision = self.policy_engine.evaluate_file_mutation(suspect_file)

        return DiagnosticReport(
            repo_path=str(target_path),
            test_command=test_command,
            tests_passed=tests_passed,
            exit_code=cmd_result.exit_code,
            duration_ms=cmd_result.duration_ms,
            error_summary=error_summary,
            failing_test_name=failing_test,
            suspect_file=suspect_file,
            suspect_line_number=suspect_line,
            exception_type=exception_type,
            policy_check=policy_decision,
            stdout_sample=cmd_result.stdout[-1500:],
            stderr_sample=cmd_result.stderr[-1500:],
        )
