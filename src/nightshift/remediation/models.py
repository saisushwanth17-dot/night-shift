"""Data models for remediation and self-correction workflows."""

from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field

from nightshift.policy.engine import AutonomyDecision
from nightshift.sandbox.runner import CommandResult


class RemediationStatus(str, Enum):
    RESOLVED = "RESOLVED"
    FAILED_MAX_ATTEMPTS = "FAILED_MAX_ATTEMPTS"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"
    REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"
    ALREADY_PASSING = "ALREADY_PASSING"


class PatchProposal(BaseModel):
    """A proposed file modification to fix an incident."""

    file_path: str
    original_content: str
    proposed_content: str
    explanation: str
    hypothesis: str
    unified_diff: str = ""
    diff_lines_count: int = 0


class RemediationAttempt(BaseModel):
    """Record of a single remediation attempt in the bounded loop."""

    attempt_number: int
    hypothesis: str
    patch: PatchProposal
    policy_decision: AutonomyDecision
    sandbox_result: CommandResult
    passed: bool
    error_feedback: str | None = None


class RemediationResult(BaseModel):
    """Final outcome of an autonomous remediation workflow."""

    incident_id: str
    repo_path: str
    status: RemediationStatus
    total_attempts: int
    attempts: list[RemediationAttempt] = Field(default_factory=list)
    successful_patch: PatchProposal | None = None
    final_policy_decision: AutonomyDecision | None = None
    total_duration_ms: float = 0.0
    summary: str = ""
