"""Deterministic Autonomy Policy Engine for Night Shift."""

import re
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field

from nightshift.policy.rules import (
    APPROVAL_REQUIRED_PATH_PATTERNS,
    AUTO_ALLOW_PATH_PATTERNS,
    BLOCKED_COMMAND_SUBSTRINGS,
    BLOCKED_PATH_PATTERNS,
    MAX_AUTO_DIFF_LINES,
)


class AutonomyLevel(str, Enum):
    AUTO_ALLOW = "AUTO_ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


class PolicyAuditEvidence(BaseModel):
    """Structured, explainable policy evidence for auditability."""

    target_scope: str
    secrets_and_credentials_check: str
    infrastructure_and_deploy_check: str
    diff_boundary_check: str
    sandbox_verification: str
    verdict: str


class AutonomyDecision(BaseModel):
    """Result of a deterministic policy evaluation."""

    level: AutonomyLevel
    allowed: bool
    requires_human: bool
    reason: str
    target: str
    evidence: PolicyAuditEvidence


class PolicyEngine:
    """Deterministic policy validator.
    
    Ensures zero LLM discretion over action permissions.
    """

    def normalize_path(self, file_path: str) -> str:
        """Clean path without stripping leading dot from dotfiles."""
        posix = Path(file_path).as_posix()
        return re.sub(r"^\./+", "", posix)

    def evaluate_file_mutation(
        self,
        file_path: str,
        diff_lines_count: int = 0,
    ) -> AutonomyDecision:
        """Evaluate whether a proposed file edit or creation is permissible with explainable evidence."""
        norm_path = self.normalize_path(file_path)

        # 1. Check strict blacklist (secrets, migrations, infra, deploy workflows)
        for pattern in BLOCKED_PATH_PATTERNS:
            if pattern.search(norm_path):
                return AutonomyDecision(
                    level=AutonomyLevel.BLOCK,
                    allowed=False,
                    requires_human=False,
                    reason=f"File path '{norm_path}' matches critical security/secret blacklist pattern '{pattern.pattern}'.",
                    target=norm_path,
                    evidence=PolicyAuditEvidence(
                        target_scope=f"BLOCKED_PATH ({norm_path})",
                        secrets_and_credentials_check=f"FAILED (Matches blacklist '{pattern.pattern}')",
                        infrastructure_and_deploy_check="REJECTED",
                        diff_boundary_check=f"{diff_lines_count} lines",
                        sandbox_verification="BLOCKED (0 sandbox mutations allowed)",
                        verdict="STRICTLY_BLOCKED",
                    ),
                )

        # 2. Check approval-required patterns (manifests, workflows, configs)
        for pattern in APPROVAL_REQUIRED_PATH_PATTERNS:
            if pattern.search(norm_path):
                return AutonomyDecision(
                    level=AutonomyLevel.REQUIRE_APPROVAL,
                    allowed=False,
                    requires_human=True,
                    reason=f"File path '{norm_path}' is an infrastructure or dependency manifest requiring human approval.",
                    target=norm_path,
                    evidence=PolicyAuditEvidence(
                        target_scope=f"MANIFEST_OR_WORKFLOW ({norm_path})",
                        secrets_and_credentials_check="PASSED (No secrets detected)",
                        infrastructure_and_deploy_check=f"FLAGGED (Requires human approval for '{pattern.pattern}')",
                        diff_boundary_check=f"{diff_lines_count} lines",
                        sandbox_verification="PAUSED_PENDING_APPROVAL",
                        verdict="REQUIRE_HUMAN_APPROVAL",
                    ),
                )

        # 3. Check diff size limit
        if diff_lines_count > MAX_AUTO_DIFF_LINES:
            return AutonomyDecision(
                level=AutonomyLevel.REQUIRE_APPROVAL,
                allowed=False,
                requires_human=True,
                reason=f"Proposed diff size ({diff_lines_count} lines) exceeds autonomous threshold ({MAX_AUTO_DIFF_LINES} lines).",
                target=norm_path,
                evidence=PolicyAuditEvidence(
                    target_scope=f"SOURCE_OR_TEST ({norm_path})",
                    secrets_and_credentials_check="PASSED",
                    infrastructure_and_deploy_check="PASSED",
                    diff_boundary_check=f"FAILED ({diff_lines_count} lines > {MAX_AUTO_DIFF_LINES} lines ceiling)",
                    sandbox_verification="PAUSED_PENDING_APPROVAL",
                    verdict="REQUIRE_HUMAN_APPROVAL",
                ),
            )

        # 4. Check auto-allow patterns
        for pattern in AUTO_ALLOW_PATH_PATTERNS:
            if pattern.search(norm_path):
                scope_type = "DOCS_ONLY" if ("doc" in norm_path.lower() or "readme" in norm_path.lower()) else "SOURCE_OR_TEST"
                return AutonomyDecision(
                    level=AutonomyLevel.AUTO_ALLOW,
                    allowed=True,
                    requires_human=False,
                    reason=f"File path '{norm_path}' is classified under low-risk autonomous maintenance whitelist.",
                    target=norm_path,
                    evidence=PolicyAuditEvidence(
                        target_scope=f"{scope_type} ({norm_path})",
                        secrets_and_credentials_check="PASSED (0 blacklist patterns matched)",
                        infrastructure_and_deploy_check="PASSED (No deploy workflows, dockerfiles, or migrations modified)",
                        diff_boundary_check=f"PASSED ({diff_lines_count} lines <= {MAX_AUTO_DIFF_LINES} lines ceiling)",
                        sandbox_verification="MANDATORY (Must exit code 0 before PR creation)",
                        verdict="PERMITTED_UNDER_AUTONOMOUS_POLICY",
                    ),
                )

        # 5. Default fallback for unclassified paths
        return AutonomyDecision(
            level=AutonomyLevel.REQUIRE_APPROVAL,
            allowed=False,
            requires_human=True,
            reason=f"File path '{norm_path}' is not explicitly whitelisted for auto-mutation.",
            target=norm_path,
            evidence=PolicyAuditEvidence(
                target_scope=f"UNCLASSIFIED ({norm_path})",
                secrets_and_credentials_check="PASSED",
                infrastructure_and_deploy_check="UNVERIFIED",
                diff_boundary_check=f"{diff_lines_count} lines",
                sandbox_verification="PAUSED_PENDING_APPROVAL",
                verdict="REQUIRE_HUMAN_APPROVAL",
            ),
        )

    def evaluate_command(self, command: str) -> AutonomyDecision:
        """Evaluate whether a shell/sandbox command is safe to execute."""
        clean_cmd = command.strip().lower()

        for blocked in BLOCKED_COMMAND_SUBSTRINGS:
            if blocked in clean_cmd:
                return AutonomyDecision(
                    level=AutonomyLevel.BLOCK,
                    allowed=False,
                    requires_human=False,
                    reason=f"Command contains forbidden substring '{blocked}'.",
                    target=command,
                    evidence=PolicyAuditEvidence(
                        target_scope=f"COMMAND ({command})",
                        secrets_and_credentials_check="REJECTED",
                        infrastructure_and_deploy_check="REJECTED",
                        diff_boundary_check="N/A",
                        sandbox_verification="BLOCKED",
                        verdict="FORBIDDEN_COMMAND",
                    ),
                )

        if any(clean_cmd.startswith(prefix) for prefix in ["pytest", "python -m pytest", "ruff", "flake8", "npm test", "pnpm test"]):
            return AutonomyDecision(
                level=AutonomyLevel.AUTO_ALLOW,
                allowed=True,
                requires_human=False,
                reason="Command is a standard test or linter invocation.",
                target=command,
                evidence=PolicyAuditEvidence(
                    target_scope=f"TEST_COMMAND ({command})",
                    secrets_and_credentials_check="PASSED",
                    infrastructure_and_deploy_check="PASSED",
                    diff_boundary_check="N/A",
                    sandbox_verification="ALLOWED",
                    verdict="PERMITTED_TEST_INVOCATION",
                ),
            )

        return AutonomyDecision(
            level=AutonomyLevel.AUTO_ALLOW,
            allowed=True,
            requires_human=False,
            reason="Command allowed within isolated execution sandbox.",
            target=command,
            evidence=PolicyAuditEvidence(
                target_scope=f"SANDBOX_COMMAND ({command})",
                secrets_and_credentials_check="PASSED",
                infrastructure_and_deploy_check="PASSED",
                diff_boundary_check="N/A",
                sandbox_verification="ALLOWED",
                verdict="PERMITTED_SANDBOX_COMMAND",
            ),
        )
