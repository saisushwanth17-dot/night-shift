"""Unit tests for the end-to-end Night Shift pipeline and PR generation."""

from pathlib import Path
import pytest

from nightshift.adapters.github import GitHubAdapter, PullRequestInfo
from nightshift.pipeline import NightShiftPipeline
from nightshift.remediation.models import RemediationStatus
from nightshift.reporting.templates import generate_pr_markdown_body


def test_pr_markdown_formatting():
    from nightshift.policy.engine import AutonomyDecision, AutonomyLevel
    from nightshift.remediation.models import PatchProposal, RemediationResult

    patch = PatchProposal(
        file_path="app/pipeline.py",
        original_content="x = None\n",
        proposed_content="x = {}\n",
        explanation="Safe initialization",
        hypothesis="Null pointer fix",
        unified_diff="-x = None\n+x = {}\n",
        diff_lines_count=2,
    )
    result = RemediationResult(
        incident_id="inc-test99",
        repo_path="/mock/repo",
        status=RemediationStatus.RESOLVED,
        total_attempts=1,
        successful_patch=patch,
        final_policy_decision=AutonomyDecision(
            level=AutonomyLevel.AUTO_ALLOW,
            risk_score=0.2,
            allowed=True,
            requires_human=False,
            reason="Low risk",
            target="app/pipeline.py",
        ),
        total_duration_ms=1200.0,
        summary="Resolved cleanly.",
    )

    md = generate_pr_markdown_body(result)
    assert "inc-test99" in md
    assert "AUTO_ALLOW" in md
    assert "Safe initialization" in md
    assert "EXIT CODE 0 (PASSED)" in md


def test_pipeline_execution_on_demo_repo():
    repo_path = Path(__file__).resolve().parents[1] / "demo_repo"
    pipeline = NightShiftPipeline()

    outcome = pipeline.execute_recovery(
        repo_path=str(repo_path),
        test_command="pytest test_data_pipeline.py",
        create_pr=False,
    )

    assert outcome.remediation.status == RemediationStatus.RESOLVED
    assert outcome.pr_markdown is not None
    assert "data_pipeline.py" in outcome.pr_markdown
    assert outcome.pull_request is None  # create_pr was False
