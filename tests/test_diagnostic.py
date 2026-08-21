"""Integration test for repository diagnostic investigation."""

from pathlib import Path
from nightshift.agent.diagnose import DiagnosticEngine


def test_diagnose_demo_repo_failing_test():
    repo_path = Path(__file__).resolve().parents[1] / "nightshift-demo"
    assert repo_path.exists()

    engine = DiagnosticEngine()
    report = engine.run_diagnostic(str(repo_path), test_command="pytest test_data_pipeline.py")

    # Verification: The test in nightshift-demo is expected to fail
    assert report.tests_passed is False
    assert report.exit_code != 0
    assert report.failing_test_name is not None
    assert "test_process_event_with_missing_or_null_metadata" in report.failing_test_name
    assert report.exception_type is not None
    assert "TypeError" in report.exception_type or "NoneType" in report.exception_type
    assert report.suspect_file is not None
    assert "data_pipeline.py" in report.suspect_file
    assert report.policy_check is not None
    assert report.policy_check.allowed is True
