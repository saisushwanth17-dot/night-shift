"""Data models for engineering memory and maintenance sessions."""

from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field


class RepoProfile(BaseModel):
    """Repository engineering profile conventions and commands."""

    repo_name: str
    language: str = "python"
    package_manager: str = "pip"
    test_command: str = "pytest"
    lint_command: str = "ruff check"
    default_branch: str = "main"
    updated_at: datetime = Field(default_factory=datetime.now)


class IncidentRecord(BaseModel):
    """Episodic record of a resolved or blocked CI maintenance incident."""

    incident_id: str
    repo_name: str
    failure_signature: str
    hypothesis: str
    suspect_file: str
    patch_diff: str = ""
    attempts_count: int = 1
    status: str  # RESOLVED, BLOCKED_BY_POLICY, REQUIRES_HUMAN_APPROVAL, FAILED_MAX_ATTEMPTS
    pr_url: str | None = None
    pr_branch: str | None = None
    duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)


class MaintenanceSession(BaseModel):
    """Record of an after-hours Night Shift operational session."""

    session_id: str
    repo_name: str
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: datetime | None = None
    incidents_handled: int = 0
    prs_opened: int = 0
    blocked_count: int = 0
    duration_minutes: float = 0.0
