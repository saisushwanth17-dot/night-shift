"""End-to-end pipeline coordinating diagnostics, sandbox remediation, engineering memory, and GitHub PR delivery."""

import time
from pathlib import Path
from pydantic import BaseModel

from nightshift.adapters.github import GitHubAdapter, PullRequestInfo
from nightshift.memory.models import IncidentRecord, RepoProfile
from nightshift.memory.store import EngineeringMemoryStore
from nightshift.remediation.loop import RemediationLoop
from nightshift.remediation.models import RemediationResult, RemediationStatus
from nightshift.reporting.templates import generate_pr_markdown_body


class PipelineOutcome(BaseModel):
    """Final result of the end-to-end Night Shift CI recovery workflow."""

    remediation: RemediationResult
    pull_request: PullRequestInfo | None = None
    pr_markdown: str | None = None
    similar_past_incidents: list[IncidentRecord] = []
    duration_ms: float = 0.0


class NightShiftPipeline:
    """Orchestrates end-to-end autonomous maintenance from detection to PR creation and memory logging."""

    def __init__(
        self,
        remediation_loop: RemediationLoop | None = None,
        github_adapter: GitHubAdapter | None = None,
        memory_store: EngineeringMemoryStore | None = None,
    ):
        self.remediation_loop = remediation_loop or RemediationLoop()
        self.github_adapter = github_adapter or GitHubAdapter()
        self.memory_store = memory_store or EngineeringMemoryStore()

    def execute_recovery(
        self,
        repo_path: str,
        test_command: str = "pytest",
        repo_name: str = "demo_repo",
        create_pr: bool = False,
        base_branch: str = "main",
    ) -> PipelineOutcome:
        """Run full autonomous recovery pipeline on target repository with memory logging."""
        start_time = time.perf_counter()
        target_path = Path(repo_path).resolve()

        # 0. Check Engineering Memory for repository profile or past similar incidents
        past_similar = []
        try:
            profile = self.memory_store.get_repo_profile(repo_name)
            if not profile:
                self.memory_store.save_repo_profile(RepoProfile(
                    repo_name=repo_name,
                    test_command=test_command,
                ))
        except Exception:
            pass

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

        # 3. Record incident in SQLite Engineering Memory
        try:
            suspect = remediation_res.successful_patch.file_path if remediation_res.successful_patch else "unknown"
            diff = remediation_res.successful_patch.unified_diff if remediation_res.successful_patch else ""
            hypo = remediation_res.successful_patch.hypothesis if remediation_res.successful_patch else remediation_res.summary
            self.memory_store.record_incident(IncidentRecord(
                incident_id=remediation_res.incident_id,
                repo_name=repo_name,
                failure_signature=hypo[:80],
                hypothesis=hypo,
                suspect_file=suspect,
                patch_diff=diff,
                attempts_count=remediation_res.total_attempts,
                status=remediation_res.status.value,
                pr_url=pr_info.url if pr_info else None,
                pr_branch=pr_info.branch if pr_info else None,
                duration_ms=round(total_duration, 2),
            ))
            # Retrieve similar remediations for post-run context
            past_similar = self.memory_store.find_similar_remediation(suspect, repo_name=repo_name)
        except Exception:
            pass

        return PipelineOutcome(
            remediation=remediation_res,
            pull_request=pr_info,
            pr_markdown=pr_markdown,
            similar_past_incidents=past_similar,
            duration_ms=round(total_duration, 2),
        )
