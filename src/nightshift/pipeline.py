"""End-to-end pipeline coordinating diagnostics, sandbox remediation, and GitHub PR delivery."""

import time
from pathlib import Path
from pydantic import BaseModel

from nightshift.adapters.github import GitHubAdapter, PullRequestInfo
from nightshift.remediation.loop import RemediationLoop
from nightshift.remediation.models import RemediationResult, RemediationStatus
from nightshift.reporting.templates import generate_pr_markdown_body


class PipelineOutcome(BaseModel):
    """Final result of the end-to-end Night Shift CI recovery workflow."""

    remediation: RemediationResult
    pull_request: PullRequestInfo | None = None
    pr_markdown: str | None = None
    duration_ms: float = 0.0


class NightShiftPipeline:
    """Orchestrates end-to-end autonomous maintenance from detection to PR creation."""

    def __init__(
        self,
        remediation_loop: RemediationLoop | None = None,
        github_adapter: GitHubAdapter | None = None,
    ):
        self.remediation_loop = remediation_loop or RemediationLoop()
        self.github_adapter = github_adapter or GitHubAdapter()

    def execute_recovery(
        self,
        repo_path: str,
        test_command: str = "pytest",
        create_pr: bool = False,
        base_branch: str = "main",
    ) -> PipelineOutcome:
        """Run full autonomous recovery pipeline on target repository."""
        start_time = time.perf_counter()
        target_path = Path(repo_path).resolve()

        # 1. Run Bounded Sandbox Remediation Loop
        remediation_res: RemediationResult = self.remediation_loop.run(
            str(target_path),
            test_command=test_command,
        )

        pr_info = None
        pr_markdown = None

        # 2. If resolved and PR creation requested, deliver Pull Request
        if remediation_res.status == RemediationStatus.RESOLVED and remediation_res.successful_patch:
            pr_markdown = generate_pr_markdown_body(remediation_res)

            if create_pr:
                branch_name = f"nightshift/fix-ci-{remediation_res.incident_id}"
                commit_title = f"fix(ci): remediate {remediation_res.successful_patch.file_path} failure"

                # Create branch, commit patch, push and open PR
                self.github_adapter.create_remediation_branch(
                    target_path,
                    branch_name=branch_name,
                    base_branch=base_branch,
                )
                self.github_adapter.apply_and_commit_patch(
                    target_path,
                    patch=remediation_res.successful_patch,
                    commit_message=f"{commit_title}\n\nIncident: {remediation_res.incident_id}\nVerified in isolated sandbox.",
                )
                self.github_adapter.push_branch(target_path, branch_name=branch_name)
                pr_info = self.github_adapter.create_pull_request(
                    target_path,
                    title=f"fix(ci): remediate {remediation_res.successful_patch.file_path} [{remediation_res.incident_id}]",
                    body=pr_markdown,
                    head_branch=branch_name,
                    base_branch=base_branch,
                )

        total_duration = (time.perf_counter() - start_time) * 1000.0
        return PipelineOutcome(
            remediation=remediation_res,
            pull_request=pr_info,
            pr_markdown=pr_markdown,
            duration_ms=round(total_duration, 2),
        )
