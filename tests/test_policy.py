"""Unit tests for the Deterministic Autonomy Policy Engine."""

import pytest
from nightshift.policy.engine import AutonomyLevel, PolicyEngine


@pytest.fixture
def policy_engine():
    return PolicyEngine()


def test_blocked_secret_paths(policy_engine):
    blocked_cases = [
        ".env",
        ".env.production",
        "config/secrets.json",
        ".aws/credentials",
        "certs/server.key",
        "certs/cert.pem",
        "migrations/001_initial.sql",
        "alembic/versions/123_migration.py",
        ".github/workflows/deploy.yml",
        ".github/workflows/release-prod.yaml",
    ]
    for path in blocked_cases:
        decision = policy_engine.evaluate_file_mutation(path)
        assert decision.level == AutonomyLevel.BLOCK, f"Expected BLOCK for {path}, got {decision.level}"
        assert decision.allowed is False
        assert decision.risk_score == 1.0


def test_approval_required_manifest_paths(policy_engine):
    approval_cases = [
        "pyproject.toml",
        "package.json",
        "requirements.txt",
        "requirements-prod.txt",
        "Dockerfile",
        "docker-compose.yml",
        ".github/workflows/ci.yml",
    ]
    for path in approval_cases:
        decision = policy_engine.evaluate_file_mutation(path)
        assert decision.level == AutonomyLevel.REQUIRE_APPROVAL, f"Expected REQUIRE_APPROVAL for {path}, got {decision.level}"
        assert decision.allowed is False
        assert decision.requires_human is True


def test_auto_allow_low_risk_paths(policy_engine):
    allowed_cases = [
        "README.md",
        "docs/index.md",
        "tests/test_pipeline.py",
        "src/nightshift/utils.py",
        "app/handlers/event.py",
    ]
    for path in allowed_cases:
        decision = policy_engine.evaluate_file_mutation(path, diff_lines_count=20)
        assert decision.level == AutonomyLevel.AUTO_ALLOW, f"Expected AUTO_ALLOW for {path}, got {decision.level}"
        assert decision.allowed is True
        assert decision.requires_human is False


def test_diff_size_exceeds_threshold(policy_engine):
    decision = policy_engine.evaluate_file_mutation("src/module.py", diff_lines_count=250)
    assert decision.level == AutonomyLevel.REQUIRE_APPROVAL
    assert decision.allowed is False
    assert decision.requires_human is True


def test_blocked_command_sanitization(policy_engine):
    blocked_cmds = [
        "rm -rf /",
        "sudo apt-get update",
        "eval $(bad_code)",
        "chmod -R 777 /var/data",
    ]
    for cmd in blocked_cmds:
        decision = policy_engine.evaluate_command(cmd)
        assert decision.level == AutonomyLevel.BLOCK
        assert decision.allowed is False


def test_allowed_test_commands(policy_engine):
    allowed_cmds = [
        "pytest tests/",
        "python -m pytest test_data_pipeline.py",
        "ruff check .",
    ]
    for cmd in allowed_cmds:
        decision = policy_engine.evaluate_command(cmd)
        assert decision.level == AutonomyLevel.AUTO_ALLOW
        assert decision.allowed is True
