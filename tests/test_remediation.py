"""Unit & Integration tests for the remediation and self-correction engine."""

from pathlib import Path
import pytest

from nightshift.agent.diagnose import DiagnosticReport
from nightshift.policy.engine import AutonomyDecision, AutonomyLevel, PolicyEngine
from nightshift.remediation.diff_utils import generate_unified_diff
from nightshift.remediation.generator import PatchGenerator
from nightshift.remediation.loop import RemediationLoop
from nightshift.remediation.models import RemediationStatus


def test_unified_diff_generation():
    orig = "def foo():\n    return 1\n"
    mod = "def foo():\n    return 2\n"
    diff_str, count = generate_unified_diff(orig, mod, "foo.py")
    assert "-    return 1" in diff_str
    assert "+    return 2" in diff_str
    assert count == 2


def test_remediation_loop_resolves_demo_repo():
    """Verify autonomous remediation of the real bug in nightshift-demo inside sandbox."""
    repo_path = Path(__file__).resolve().parents[1] / "nightshift-demo"
    assert repo_path.exists()

    loop = RemediationLoop()
    result = loop.run(
        str(repo_path),
        test_command="pytest test_data_pipeline.py",
        max_attempts=3,
    )

    assert result.status == RemediationStatus.RESOLVED
    assert result.total_attempts >= 1
    assert result.successful_patch is not None
    assert result.successful_patch.file_path == "data_pipeline.py"
    assert result.successful_patch.diff_lines_count > 0
    assert "metadata" in result.successful_patch.proposed_content
    assert result.final_policy_decision.level == AutonomyLevel.AUTO_ALLOW
    assert result.final_policy_decision.allowed is True


def test_remediation_blocked_by_policy(tmp_path):
    """Verify that a failure pointing to a secret/blocked file is halted by PolicyEngine."""
    demo_dir = tmp_path / "mock_repo"
    demo_dir.mkdir()
    (demo_dir / ".env").write_text("DATABASE_URL=postgres://...", encoding="utf-8")
    (demo_dir / "test_config.py").write_text("def test_fail(): assert False\n", encoding="utf-8")

    class MockDiagEngine:
        def run_diagnostic(self, repo_path, test_command):
            return DiagnosticReport(
                repo_path=str(demo_dir),
                test_command=test_command,
                tests_passed=False,
                exit_code=1,
                duration_ms=50.0,
                error_summary="AssertionError",
                failing_test_name="test_config.py::test_fail",
                suspect_file=".env",
                suspect_line_number=1,
                exception_type="AssertionError",
                policy_check=None,
                stdout_sample="",
                stderr_sample="",
            )

    loop = RemediationLoop(diagnostic_engine=MockDiagEngine())
    result = loop.run(str(demo_dir), test_command="pytest test_config.py")

    assert result.status == RemediationStatus.BLOCKED_BY_POLICY
    assert result.final_policy_decision.level == AutonomyLevel.BLOCK
    assert result.final_policy_decision.allowed is False


def test_already_passing_repo(tmp_path):
    """Verify clean short-circuit when all tests already pass."""
    demo_dir = tmp_path / "clean_repo"
    demo_dir.mkdir()
    (demo_dir / "test_ok.py").write_text("def test_ok(): assert True\n", encoding="utf-8")

    loop = RemediationLoop()
    result = loop.run(str(demo_dir), test_command="pytest test_ok.py")

    assert result.status == RemediationStatus.ALREADY_PASSING
    assert result.total_attempts == 0
    assert result.successful_patch is None
