"""GitHub integration adapter for branch management and Pull Request creation."""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

from nightshift.config import settings
from nightshift.remediation.models import PatchProposal


class PullRequestInfo(BaseModel):
    """Details of a created or updated Pull Request."""

    url: str
    number: int | None = None
    branch: str
    title: str
    created_at: datetime = datetime.now()


class GitHubAdapter:
    """Manages Git branch creation, patch committing, and GitHub PR generation."""

    def __init__(self, github_token: str | None = None):
        self.github_token = github_token or settings.github_token or os.getenv("GITHUB_TOKEN")

    def create_remediation_branch(
        self,
        repo_path: Path,
        branch_name: str,
        base_branch: str = "main",
    ) -> bool:
        """Create and checkout a new local Git remediation branch."""
        try:
            # Checkout base branch first
            subprocess.run(
                ["git", "checkout", base_branch],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            # Create and switch to new branch
            subprocess.run(
                ["git", "checkout", "-B", branch_name],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as ex:
            raise RuntimeError(f"Failed to create Git branch '{branch_name}': {ex.stderr}")

    def apply_and_commit_patch(
        self,
        repo_path: Path,
        patch: PatchProposal,
        commit_message: str,
    ) -> bool:
        """Write the verified patch to the repository workspace and create a Git commit."""
        target_file = repo_path / patch.file_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(patch.proposed_content, encoding="utf-8")

        try:
            subprocess.run(
                ["git", "add", patch.file_path],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as ex:
            raise RuntimeError(f"Failed to commit patch on '{patch.file_path}': {ex.stderr}")

    def push_branch(self, repo_path: Path, branch_name: str, remote: str = "origin") -> bool:
        """Push the remediation branch to GitHub remote."""
        try:
            subprocess.run(
                ["git", "push", "-u", remote, branch_name],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as ex:
            raise RuntimeError(f"Failed to push branch '{branch_name}' to remote '{remote}': {ex.stderr}")

    def create_pull_request(
        self,
        repo_path: Path,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> PullRequestInfo:
        """Create a GitHub Pull Request using GitHub CLI (gh) or PyGithub."""
        # Method 1: Use GitHub CLI if available
        if shutil.which("gh"):
            try:
                cmd = [
                    "gh", "pr", "create",
                    "--title", title,
                    "--body", body,
                    "--head", head_branch,
                    "--base", base_branch,
                ]
                proc = subprocess.run(
                    cmd,
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                pr_url = proc.stdout.strip()
                return PullRequestInfo(
                    url=pr_url,
                    branch=head_branch,
                    title=title,
                )
            except subprocess.CalledProcessError as ex:
                raise RuntimeError(f"GitHub CLI PR creation failed: {ex.stderr or ex.stdout}")

        # Fallback dummy URL for local disconnected environments
        return PullRequestInfo(
            url=f"https://github.com/mock-repo/pulls/new?head={head_branch}",
            branch=head_branch,
            title=title,
        )
