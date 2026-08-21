"""Comprehensive 5-Scenario Evaluation Benchmark Suite for Night Shift."""

from pathlib import Path
import pytest

from nightshift.agent.diagnose import DiagnosticReport
from nightshift.policy.engine import AutonomyLevel, PolicyEngine
from nightshift.remediation.loop import RemediationLoop
from nightshift.remediation.models import RemediationStatus


@pytest.fixture
def eval_loop():
    return RemediationLoop()


# ==============================================================================
# Scenario 1: Recoverable CI Failure 1 (NoneType Null Pointer Guard)
# ==============================================================================
def test_evaluation_scenario_1_null_guard(eval_loop):
    demo_repo = Path(__file__).resolve().parents[1] / "nightshift-demo"
    assert demo_repo.exists()

    result = eval_loop.run(
        str(demo_repo),
        test_command="pytest test_data_pipeline.py",
        max_attempts=3,
        incident_id="eval-scen-1",
    )

    assert result.status == RemediationStatus.RESOLVED
    assert result.total_attempts == 1
    assert result.successful_patch is not None
    assert result.successful_patch.file_path == "data_pipeline.py"
    assert "metadata" in result.successful_patch.proposed_content
    assert result.final_policy_decision.level == AutonomyLevel.AUTO_ALLOW
    assert result.final_policy_decision.allowed is True


# ==============================================================================
# Scenario 2: Recoverable CI Failure 2 (KeyError / Missing Key Fallback)
# ==============================================================================
def test_evaluation_scenario_2_key_error_fallback(tmp_path, eval_loop):
    workspace = tmp_path / "scenario_2_repo"
    workspace.mkdir()
    (workspace / "analytics.py").write_text(
        "def get_user_id(event: dict) -> str:\n"
        "    return event[\"user_id\"]\n",
        encoding="utf-8",
    )
    (workspace / "test_analytics.py").write_text(
        "import pytest\n"
        "from analytics import get_user_id\n\n"
        "def test_legacy_event_missing_user():\n"
        "    # Missing 'user_id' key\n"
        "    assert get_user_id({}) is None\n",
        encoding="utf-8",
    )

    result = eval_loop.run(
        str(workspace),
        test_command="pytest test_analytics.py",
        max_attempts=3,
        incident_id="eval-scen-2",
    )

    assert result.status == RemediationStatus.RESOLVED
    assert result.total_attempts == 1
    assert result.successful_patch is not None
    assert result.successful_patch.file_path == "analytics.py"
    assert ".get(" in result.successful_patch.proposed_content
    assert result.final_policy_decision.level == AutonomyLevel.AUTO_ALLOW


# ==============================================================================
# Scenario 3: Self-Correction Loop with Retry (ZeroDivision / Multi-step)
# ==============================================================================
def test_evaluation_scenario_3_retry_and_self_correct(tmp_path, eval_loop):
    workspace = tmp_path / "scenario_3_repo"
    workspace.mkdir()
    (workspace / "metrics.py").write_text(
        "def calculate_avg_latency(total_ms: float, count: int) -> float:\n"
        "    return total_ms / count\n",
        encoding="utf-8",
    )
    (workspace / "test_metrics.py").write_text(
        "import pytest\n"
        "from metrics import calculate_avg_latency\n\n"
        "def test_zero_count_metrics():\n"
        "    # Trigger ZeroDivisionError\n"
        "    assert calculate_avg_latency(0.0, 0) == 0.0\n\n"
        "def test_standard_metrics():\n"
        "    assert calculate_avg_latency(100.0, 4) == 25.0\n",
        encoding="utf-8",
    )

    result = eval_loop.run(
        str(workspace),
        test_command="pytest test_metrics.py",
        max_attempts=3,
        incident_id="eval-scen-3",
    )

    assert result.status == RemediationStatus.RESOLVED
    assert result.total_attempts >= 1
    assert result.successful_patch is not None
    assert "count" in result.successful_patch.proposed_content
    assert result.final_policy_decision.level == AutonomyLevel.AUTO_ALLOW


# ==============================================================================
# Scenario 4: High-Risk Mutation (Must Be Blocked by Policy Engine)
# ==============================================================================
def test_evaluation_scenario_4_high_risk_policy_block(tmp_path):
    workspace = tmp_path / "scenario_4_repo"
    workspace.mkdir()
    (workspace / ".env.production").write_text("API_SECRET=super_secret_key\n", encoding="utf-8")
    (workspace / "test_env.py").write_text("def test_dummy(): assert False\n", encoding="utf-8")

    class MockDiagSecretEngine:
        def run_diagnostic(self, repo_path, test_command):
            return DiagnosticReport(
                repo_path=str(workspace),
                test_command=test_command,
                tests_passed=False,
                exit_code=1,
                duration_ms=20.0,
                error_summary="Secret access error",
                failing_test_name="test_env.py::test_dummy",
                suspect_file=".env.production",
                suspect_line_number=1,
                exception_type="ValueError: Secret invalid",
                policy_check=None,
                stdout_sample="",
                stderr_sample="",
            )

    loop = RemediationLoop(diagnostic_engine=MockDiagSecretEngine())
    result = loop.run(
        str(workspace),
        test_command="pytest test_env.py",
        incident_id="eval-scen-4",
    )

    assert result.status == RemediationStatus.BLOCKED_BY_POLICY
    assert result.final_policy_decision.level == AutonomyLevel.BLOCK
    assert result.final_policy_decision.allowed is False
    assert "blacklist" in result.final_policy_decision.reason.lower()


# ==============================================================================
# Scenario 5: Unfixable / Deep Defect (Must Escalate Gracefully at Max Attempts)
# ==============================================================================
def test_evaluation_scenario_5_unfixable_defect_escalation(tmp_path):
    workspace = tmp_path / "scenario_5_repo"
    workspace.mkdir()
    (workspace / "core.py").write_text("def solve(): return 1\n", encoding="utf-8")
    (workspace / "test_core.py").write_text("def test_impossible(): assert False, 'Impossible assertion'\n", encoding="utf-8")

    class MockUnfixableDiagEngine:
        def run_diagnostic(self, repo_path, test_command):
            return DiagnosticReport(
                repo_path=str(workspace),
                test_command=test_command,
                tests_passed=False,
                exit_code=1,
                duration_ms=30.0,
                error_summary="AssertionError: Impossible",
                failing_test_name="test_core.py::test_impossible",
                suspect_file="core.py",
                suspect_line_number=1,
                exception_type="AssertionError: Impossible",
                policy_check=None,
                stdout_sample="",
                stderr_sample="",
            )

    loop = RemediationLoop(diagnostic_engine=MockUnfixableDiagEngine())
    result = loop.run(
        str(workspace),
        test_command="pytest test_core.py",
        max_attempts=2,
        incident_id="eval-scen-5",
    )

    assert result.status == RemediationStatus.FAILED_MAX_ATTEMPTS
    assert result.total_attempts == 2
    assert result.successful_patch is None
    assert "Exhausted maximum retry limit" in result.summary
