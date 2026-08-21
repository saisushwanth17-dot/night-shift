"""Unit tests for SQLite Engineering Memory Store."""

from datetime import datetime
from pathlib import Path
import pytest

from nightshift.memory.models import IncidentRecord, RepoProfile
from nightshift.memory.store import EngineeringMemoryStore


@pytest.fixture
def memory_store(tmp_path):
    db_file = tmp_path / "test_memory.db"
    return EngineeringMemoryStore(db_path=db_file)


def test_repo_profile_save_and_retrieve(memory_store):
    profile = RepoProfile(
        repo_name="org/test-repo",
        language="python",
        package_manager="uv",
        test_command="pytest tests/",
        lint_command="ruff check .",
        default_branch="main",
    )
    memory_store.save_repo_profile(profile)

    retrieved = memory_store.get_repo_profile("org/test-repo")
    assert retrieved is not None
    assert retrieved.repo_name == "org/test-repo"
    assert retrieved.package_manager == "uv"
    assert retrieved.test_command == "pytest tests/"


def test_incident_recording_and_recall(memory_store):
    incident = IncidentRecord(
        incident_id="inc-abc12345",
        repo_name="org/test-repo",
        failure_signature="TypeError: 'NoneType' object is not subscriptable",
        hypothesis="Safely handle null metadata dictionary",
        suspect_file="data_pipeline.py",
        patch_diff="--- a/data_pipeline.py\n+++ b/data_pipeline.py",
        attempts_count=1,
        status="RESOLVED",
        pr_url="https://github.com/org/test-repo/pull/42",
        pr_branch="nightshift/fix-ci-abc12345",
        duration_ms=2500.0,
    )
    memory_store.record_incident(incident)

    # Search for similar remediation
    similar = memory_store.find_similar_remediation("TypeError")
    assert len(similar) == 1
    assert similar[0].incident_id == "inc-abc12345"
    assert similar[0].pr_url == "https://github.com/org/test-repo/pull/42"


def test_maintenance_session_lifecycle(memory_store):
    session = memory_store.start_session("org/test-repo")
    assert session.session_id.startswith("shift-")
    assert session.repo_name == "org/test-repo"

    closed = memory_store.close_session(
        session_id=session.session_id,
        incidents_handled=3,
        prs_opened=2,
        blocked_count=1,
    )
    assert closed.end_time is not None
    assert closed.incidents_handled == 3
    assert closed.prs_opened == 2
    assert closed.blocked_count == 1
    assert closed.duration_minutes >= 0.0
