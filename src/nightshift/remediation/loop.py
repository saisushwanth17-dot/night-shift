"""Bounded remediation and self-correction loop for Night Shift."""

import time
import uuid
from pathlib import Path

from nightshift.agent.diagnose import DiagnosticEngine, DiagnosticReport
from nightshift.config import settings
from nightshift.policy.engine import AutonomyLevel, PolicyEngine
from nightshift.remediation.generator import PatchGenerator
from nightshift.remediation.models import (
    PatchProposal,
    RemediationAttempt,
    RemediationResult,
    RemediationStatus,
)
from nightshift.sandbox.runner import CommandResult, create_sandbox


class RemediationLoop:
    """Orchestrates the autonomous Cause -> Change -> Verification self-correction cycle."""

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        patch_generator: PatchGenerator | None = None,
        diagnostic_engine: DiagnosticEngine | None = None,
    ):
        self.policy_engine = policy_engine or PolicyEngine()
        self.patch_generator = patch_generator or PatchGenerator()
        self.diagnostic_engine = diagnostic_engine or DiagnosticEngine(policy_engine=self.policy_engine)

    def run(
        self,
        repo_path: str,
        test_command: str = "pytest",
        max_attempts: int | None = None,
        incident_id: str | None = None,
    ) -> RemediationResult:
        """Execute the bounded self-correction loop on a target repository."""
        start_time = time.perf_counter()
        target_path = Path(repo_path).resolve()
        inc_id = incident_id or f"inc-{uuid.uuid4().hex[:8]}"
        limit = max_attempts or settings.max_fix_attempts

        # 1. Baseline Diagnostic
        baseline_diag: DiagnosticReport = self.diagnostic_engine.run_diagnostic(
            str(target_path),
            test_command=test_command,
        )

        if baseline_diag.tests_passed:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return RemediationResult(
                incident_id=inc_id,
                repo_path=str(target_path),
                status=RemediationStatus.ALREADY_PASSING,
                total_attempts=0,
                total_duration_ms=round(duration_ms, 2),
                summary="Repository test suite is already passing cleanly. No maintenance required.",
            )

        if not baseline_diag.suspect_file:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return RemediationResult(
                incident_id=inc_id,
                repo_path=str(target_path),
                status=RemediationStatus.FAILED_MAX_ATTEMPTS,
                total_attempts=0,
                total_duration_ms=round(duration_ms, 2),
                summary="Unable to isolate suspect file from test failure logs.",
            )

        # 2. Bounded Iteration Loop (Max attempts)
        attempts: list[RemediationAttempt] = []
        feedback_history: list[str] = []
        current_diag = baseline_diag

        for attempt_idx in range(1, limit + 1):
            # A. Generate Candidate Patch
            patch: PatchProposal = self.patch_generator.generate_candidate_patch(
                repo_path=target_path,
                diagnostic=current_diag,
                previous_feedback=feedback_history,
                attempt=attempt_idx,
            )

            # B. Deterministic Policy Gate
            policy_decision = self.policy_engine.evaluate_file_mutation(
                patch.file_path,
                diff_lines_count=patch.diff_lines_count,
            )

            if policy_decision.level == AutonomyLevel.BLOCK:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return RemediationResult(
                    incident_id=inc_id,
                    repo_path=str(target_path),
                    status=RemediationStatus.BLOCKED_BY_POLICY,
                    total_attempts=attempt_idx,
                    attempts=attempts,
                    final_policy_decision=policy_decision,
                    total_duration_ms=round(duration_ms, 2),
                    summary=f"Patch for '{patch.file_path}' was strictly blocked by security policy: {policy_decision.reason}",
                )

            if policy_decision.level == AutonomyLevel.REQUIRE_APPROVAL:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return RemediationResult(
                    incident_id=inc_id,
                    repo_path=str(target_path),
                    status=RemediationStatus.REQUIRES_HUMAN_APPROVAL,
                    total_attempts=attempt_idx,
                    attempts=attempts,
                    final_policy_decision=policy_decision,
                    total_duration_ms=round(duration_ms, 2),
                    summary=f"Patch for '{patch.file_path}' requires human approval before proceeding: {policy_decision.reason}",
                )

            # C. Sandbox Execution & Verification
            sandbox = create_sandbox()
            try:
                sandbox.setup_workspace(target_path)
                # Apply patch inside the isolated sandbox
                sandbox.write_file(patch.file_path, patch.proposed_content)
                # Re-run test suite
                sandbox_result: CommandResult = sandbox.run_command(test_command)
            finally:
                sandbox.cleanup()

            is_passed = sandbox_result.success
            attempt_record = RemediationAttempt(
                attempt_number=attempt_idx,
                hypothesis=patch.hypothesis,
                patch=patch,
                policy_decision=policy_decision,
                sandbox_result=sandbox_result,
                passed=is_passed,
                error_feedback=None if is_passed else (sandbox_result.stderr or sandbox_result.stdout),
            )
            attempts.append(attempt_record)

            if is_passed:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return RemediationResult(
                    incident_id=inc_id,
                    repo_path=str(target_path),
                    status=RemediationStatus.RESOLVED,
                    total_attempts=attempt_idx,
                    attempts=attempts,
                    successful_patch=patch,
                    final_policy_decision=policy_decision,
                    total_duration_ms=round(duration_ms, 2),
                    summary=f"Incident resolved and verified in sandbox on attempt {attempt_idx}. All tests passed.",
                )

            # If failed, feed new error trace into history for next attempt
            feedback_history.append(sandbox_result.stderr or sandbox_result.stdout)

        # 3. Exhausted Attempts
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return RemediationResult(
            incident_id=inc_id,
            repo_path=str(target_path),
            status=RemediationStatus.FAILED_MAX_ATTEMPTS,
            total_attempts=len(attempts),
            attempts=attempts,
            total_duration_ms=round(duration_ms, 2),
            summary=f"Exhausted maximum retry limit ({limit} attempts) without passing sandbox test verification.",
        )
