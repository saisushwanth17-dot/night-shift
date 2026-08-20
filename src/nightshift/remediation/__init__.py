"""Autonomous remediation and self-correction package for Night Shift."""

from nightshift.remediation.generator import PatchGenerator
from nightshift.remediation.loop import RemediationLoop
from nightshift.remediation.models import (
    PatchProposal,
    RemediationAttempt,
    RemediationResult,
    RemediationStatus,
)

__all__ = [
    "PatchGenerator",
    "PatchProposal",
    "RemediationAttempt",
    "RemediationLoop",
    "RemediationResult",
    "RemediationStatus",
]
