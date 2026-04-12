"""GitHub Actions feedback secret helpers."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .feedback import FeedbackState, serialize_feedback_state

DEFAULT_FEEDBACK_SECRET_NAME = "PAPER_DIGEST_FEEDBACK_JSON"
_HTTPS_REPO_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    re.IGNORECASE,
)
_SSH_REPO_RE = re.compile(
    r"^(?:ssh://)?git@github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    re.IGNORECASE,
)


class GitHubFeedbackSyncError(RuntimeError):
    """Raised when feedback state cannot be synced to GitHub Actions secrets."""


def sync_feedback_to_github_secret(
    feedback_state: FeedbackState,
    *,
    cwd: Path | None = None,
    repo: str | None = None,
    secret_name: str = DEFAULT_FEEDBACK_SECRET_NAME,
) -> str:
    normalized_secret_name = _normalize_secret_name(secret_name)
    target_repo = repo or detect_github_repository(cwd=cwd)
    payload = serialize_feedback_state(feedback_state)
    command = [
        "gh",
        "secret",
        "set",
        normalized_secret_name,
        "--app",
        "actions",
        "--repo",
        target_repo,
        "--body",
        payload,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitHubFeedbackSyncError(
            "GitHub CLI (gh) is required to sync feedback secrets."
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "unknown gh error"
        raise GitHubFeedbackSyncError(
            f"failed to sync feedback secret {normalized_secret_name!r}: {detail}"
        )
    return target_repo


def detect_github_repository(*, cwd: Path | None = None) -> str:
    command = ["git", "config", "--get", "remote.origin.url"]
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitHubFeedbackSyncError(
            "git is required to detect the GitHub repository."
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "missing origin remote"
        raise GitHubFeedbackSyncError(
            f"failed to detect the GitHub repository: {detail}"
        )
    remote_url = result.stdout.strip()
    repository = parse_github_repository(remote_url)
    if repository is None:
        raise GitHubFeedbackSyncError(
            f"unsupported GitHub remote URL: {remote_url or '<empty>'}"
        )
    return repository


def parse_github_repository(remote_url: str) -> str | None:
    value = remote_url.strip()
    if not value:
        return None
    for pattern in (_HTTPS_REPO_RE, _SSH_REPO_RE):
        match = pattern.match(value)
        if match is not None:
            owner = match.group("owner")
            repo = match.group("repo")
            return f"{owner}/{repo}"
    return None


def _normalize_secret_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise GitHubFeedbackSyncError("secret_name must not be empty")
    return normalized
