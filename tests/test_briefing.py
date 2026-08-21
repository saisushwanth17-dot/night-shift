"""Unit tests for Morning Briefing generator."""

from datetime import datetime
import pytest

from nightshift.memory.models import IncidentRecord, MaintenanceSession
from nightshift.reporting.briefing import MorningBriefingGenerator


def test_briefing_generation_and_markdown():
    session = MaintenanceSession(
        session_id="shift-101",
        repo_name="saisushwanth17-dot/night-shift",
        duration_minutes=245.5,
    )
    incidents = [
        IncidentRecord(
            incident_id="inc-1",
            repo_name="saisushwanth17-dot/night-shift",
            failure_signature="TypeError: 'NoneType' object is not subscriptable",
            hypothesis="Add null check on metadata",
            suspect_file="data_pipeline.py",
            patch_diff="- a\n+ b",
            attempts_count=1,
            status="RESOLVED",
            pr_url="https://github.com/saisushwanth17-dot/night-shift/pull/1",
            pr_branch="nightshift/fix-ci-1",
            duration_ms=1200.0,
        ),
        IncidentRecord(
            incident_id="inc-2",
            repo_name="saisushwanth17-dot/night-shift",
            failure_signature="Alembic migration failed",
            hypothesis="Database schema migration requested",
            suspect_file="migrations/002_add_users.sql",
            patch_diff="",
            attempts_count=1,
            status="BLOCKED_BY_POLICY",
            duration_ms=50.0,
        ),
    ]

    generator = MorningBriefingGenerator()
    briefing = generator.generate(session, incidents)

    assert len(briefing.completed_chores) == 1
    assert len(briefing.ready_for_review_prs) == 1
    assert len(briefing.blocked_tasks) == 1
    assert len(briefing.decisions_required) == 1

    md = generator.format_markdown(briefing)
    assert "Good Morning" in md
    assert "data_pipeline.py" in md
    assert "migrations/002_add_users.sql" in md
    assert "Your Decisions Today" in md
