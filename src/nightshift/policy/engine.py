"""Deterministic Autonomy Policy Engine for Night Shift."""

import re
from enum import Enum
from pathlib import Path
from pydantic import BaseModel

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


class AutonomyDecision(BaseModel):
    """Result of a policy evaluation."""

    level: AutonomyLevel
    risk_score: float  # 0.0 (safest) to 1.0 (most dangerous)
    allowed: bool
    requires_human: bool
    reason: str
    target: str


class PolicyEngine:
    """Deterministic policy validator.
    
    Ensures the LLM cannot self-authorize unsafe operations.
    """

    def normalize_path(self, file_path: str) -> str:
        """Clean path without stripping leading dot from dotfiles."""
        posix = Path(file_path).as_posix()
        # Remove leading './'
        return re.sub(r"^\./+", "", posix)

    def evaluate_file_mutation(
        self,
        file_path: str,
        diff_lines_count: int = 0,
    ) -> AutonomyDecision:
        """Evaluate whether a proposed file edit or creation is permissible."""
        norm_path = self.normalize_path(file_path)

        # 1. Check strict blacklist (secrets, migrations, infra, deploy workflows)
        for pattern in BLOCKED_PATH_PATTERNS:
            if pattern.search(norm_path):
                return AutonomyDecision(
                    level=AutonomyLevel.BLOCK,
                    risk_score=1.0,
                    allowed=False,
                    requires_human=False,
                    reason=f"File path '{norm_path}' matches critical security/secret blacklist pattern '{pattern.pattern}'.",
                    target=norm_path,
                )

        # 2. Check approval-required patterns (manifests, workflows, configs)
        for pattern in APPROVAL_REQUIRED_PATH_PATTERNS:
            if pattern.search(norm_path):
                return AutonomyDecision(
                    level=AutonomyLevel.REQUIRE_APPROVAL,
                    risk_score=0.7,
                    allowed=False,
                    requires_human=True,
                    reason=f"File path '{norm_path}' is an infrastructure or dependency manifest requiring human approval.",
                    target=norm_path,
                )

        # 3. Check diff size limit
        if diff_lines_count > MAX_AUTO_DIFF_LINES:
            return AutonomyDecision(
                level=AutonomyLevel.REQUIRE_APPROVAL,
                risk_score=0.6,
                allowed=False,
                requires_human=True,
                reason=f"Proposed diff size ({diff_lines_count} lines) exceeds autonomous threshold ({MAX_AUTO_DIFF_LINES} lines).",
                target=norm_path,
            )

        # 4. Check auto-allow patterns
        for pattern in AUTO_ALLOW_PATH_PATTERNS:
            if pattern.search(norm_path):
                # Low risk for docs/tests, moderate for src code
                risk = 0.1 if ("doc" in norm_path.lower() or "readme" in norm_path.lower() or "test" in norm_path.lower()) else 0.3
                return AutonomyDecision(
                    level=AutonomyLevel.AUTO_ALLOW,
                    risk_score=risk,
                    allowed=True,
                    requires_human=False,
                    reason=f"File path '{norm_path}' is classified under low-risk autonomous maintenance whitelist.",
                    target=norm_path,
                )

        # 5. Default fallback for unclassified paths
        return AutonomyDecision(
            level=AutonomyLevel.REQUIRE_APPROVAL,
            risk_score=0.5,
            allowed=False,
            requires_human=True,
            reason=f"File path '{norm_path}' is not explicitly whitelisted for auto-mutation.",
            target=norm_path,
        )

    def evaluate_command(self, command: str) -> AutonomyDecision:
        """Evaluate whether a shell/sandbox command is safe to execute."""
        clean_cmd = command.strip().lower()

        # Check blacklist substrings
        for blocked in BLOCKED_COMMAND_SUBSTRINGS:
            if blocked in clean_cmd:
                return AutonomyDecision(
                    level=AutonomyLevel.BLOCK,
                    risk_score=1.0,
                    allowed=False,
                    requires_human=False,
                    reason=f"Command contains forbidden substring '{blocked}'.",
                    target=command,
                )

        # Test and lint commands are low risk
        if any(clean_cmd.startswith(prefix) for prefix in ["pytest", "python -m pytest", "ruff", "flake8", "npm test", "pnpm test"]):
            return AutonomyDecision(
                level=AutonomyLevel.AUTO_ALLOW,
                risk_score=0.1,
                allowed=True,
                requires_human=False,
                reason="Command is a standard test or linter invocation.",
                target=command,
            )

        # Default for other commands
        return AutonomyDecision(
            level=AutonomyLevel.AUTO_ALLOW,
            risk_score=0.3,
            allowed=True,
            requires_human=False,
            reason="Command allowed within isolated execution sandbox.",
            target=command,
        )
