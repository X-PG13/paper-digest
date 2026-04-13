"""GitHub Actions feedback secret helpers."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .feedback import FeedbackState, load_feedback_file, serialize_feedback_state

DEFAULT_FEEDBACK_SECRET_NAME = "PAPER_DIGEST_FEEDBACK_JSON"
DEFAULT_FEEDBACK_PULL_WORKFLOW = "feedback-secret-sync.yml"
DEFAULT_FEEDBACK_PULL_ARTIFACT = "feedback-secret"
_HTTPS_REPO_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    re.IGNORECASE,
)
_SSH_REPO_RE = re.compile(
    r"^(?:ssh://)?git@github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    re.IGNORECASE,
)
_RUN_URL_RE = re.compile(r"/runs/(?P<run_id>\d+)", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class GitHubFeedbackPullResult:
    repository: str
    run_id: str
    run_url: str
    feedback_state: FeedbackState


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
    _run_gh_command(
        [
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
        ],
        cwd=cwd,
        error_prefix=(
            f"failed to sync feedback secret {normalized_secret_name!r}"
        ),
    )
    return target_repo


def pull_feedback_from_github_secret(
    *,
    cwd: Path | None = None,
    repo: str | None = None,
    secret_name: str = DEFAULT_FEEDBACK_SECRET_NAME,
    workflow_file: str = DEFAULT_FEEDBACK_PULL_WORKFLOW,
    artifact_name: str = DEFAULT_FEEDBACK_PULL_ARTIFACT,
) -> GitHubFeedbackPullResult:
    normalized_secret_name = _normalize_secret_name(secret_name)
    target_repo = repo or detect_github_repository(cwd=cwd)
    workflow = workflow_file.strip()
    if not workflow:
        raise GitHubFeedbackSyncError("workflow_file must not be empty")
    artifact = artifact_name.strip()
    if not artifact:
        raise GitHubFeedbackSyncError("artifact_name must not be empty")

    dispatch = _run_gh_command(
        [
            "gh",
            "workflow",
            "run",
            workflow,
            "--repo",
            target_repo,
            "-f",
            f"secret_name={normalized_secret_name}",
        ],
        cwd=cwd,
        error_prefix="failed to dispatch feedback secret pull workflow",
    )
    run_url = _extract_run_url(dispatch.stdout or dispatch.stderr)
    run_id = _extract_run_id(run_url)
    _run_gh_command(
        [
            "gh",
            "run",
            "watch",
            run_id,
            "--repo",
            target_repo,
            "--exit-status",
        ],
        cwd=cwd,
        error_prefix=f"feedback secret export run {run_id} failed",
    )
    feedback_state = _download_feedback_artifact(
        run_id,
        cwd=cwd,
        repo=target_repo,
        artifact_name=artifact,
    )
    return GitHubFeedbackPullResult(
        repository=target_repo,
        run_id=run_id,
        run_url=run_url,
        feedback_state=feedback_state,
    )


def detect_github_repository(*, cwd: Path | None = None) -> str:
    command = ["git", "config", "--get", "remote.origin.url"]
    result = _run_command(
        command,
        cwd=cwd,
        tool_name="git",
    )
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


def _download_feedback_artifact(
    run_id: str,
    *,
    cwd: Path | None,
    repo: str,
    artifact_name: str,
) -> FeedbackState:
    with tempfile.TemporaryDirectory(prefix="paper-digest-feedback-pull-") as temp_dir:
        temp_path = Path(temp_dir)
        _run_gh_command(
            [
                "gh",
                "run",
                "download",
                run_id,
                "--repo",
                repo,
                "--name",
                artifact_name,
                "--dir",
                str(temp_path),
            ],
            cwd=cwd,
            error_prefix=(
                f"failed to download feedback artifact {artifact_name!r} "
                f"from run {run_id}"
            ),
        )
        matches = sorted(temp_path.rglob("feedback.json"))
        if not matches:
            raise GitHubFeedbackSyncError(
                f"feedback artifact {artifact_name!r} from run {run_id} "
                "did not contain feedback.json"
            )
        try:
            return load_feedback_file(matches[0])
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise GitHubFeedbackSyncError(
                f"failed to parse feedback.json from run {run_id}: {exc}"
            ) from exc


def _extract_run_url(value: str) -> str:
    for token in value.split():
        if "github.com" in token and "/actions/runs/" in token:
            return token.strip()
    raise GitHubFeedbackSyncError(
        "failed to determine the GitHub Actions run URL for feedback pull"
    )


def _extract_run_id(run_url: str) -> str:
    match = _RUN_URL_RE.search(run_url)
    if match is None:
        raise GitHubFeedbackSyncError(
            f"failed to extract run id from workflow URL: {run_url}"
        )
    return match.group("run_id")


def _run_gh_command(
    command: list[str],
    *,
    cwd: Path | None,
    error_prefix: str,
) -> subprocess.CompletedProcess[str]:
    result = _run_command(command, cwd=cwd, tool_name="GitHub CLI (gh)")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "unknown gh error"
        raise GitHubFeedbackSyncError(f"{error_prefix}: {detail}")
    return result


def _run_command(
    command: list[str],
    *,
    cwd: Path | None,
    tool_name: str,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("XDG_CACHE_HOME", tempfile.gettempdir())
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise GitHubFeedbackSyncError(
            f"{tool_name} is required for GitHub feedback sync."
        ) from exc
