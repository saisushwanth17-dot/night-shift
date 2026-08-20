"""Adapter integrations package for Night Shift."""

from nightshift.adapters.github import GitHubAdapter, PullRequestInfo

__all__ = ["GitHubAdapter", "PullRequestInfo"]
