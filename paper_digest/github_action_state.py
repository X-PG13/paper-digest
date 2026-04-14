"""GitHub Actions helpers for syncing remembered action notification state."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .state import parse_action_notifications_payload, serialize_action_notifications

DEFAULT_ACTION_STATE_SYNC_WORKFLOW = "action-state-sync.yml"
DEFAULT_ACTION_STATE_SYNC_ARTIFACT = "action-state"
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
class GitHubActionStateResult:
    repository: str
    run_id: str
    run_url: str
    action_notifications: dict[str, dict[str, str]]


class GitHubActionStateSyncError(RuntimeError):
    """Raised when action notification state cannot be synced."""


def sync_action_notifications_to_github_actions(
    action_notifications: dict[str, dict[str, str]],
    *,
    cwd: Path | None = None,
    repo: str | None = None,
    workflow_file: str = DEFAULT_ACTION_STATE_SYNC_WORKFLOW,
    artifact_name: str = DEFAULT_ACTION_STATE_SYNC_ARTIFACT,
) -> GitHubActionStateResult:
    payload = serialize_action_notifications(action_notifications)
    return _run_action_state_workflow(
        direction="import",
        action_state_json=payload,
        cwd=cwd,
        repo=repo,
        workflow_file=workflow_file,
        artifact_name=artifact_name,
    )


def pull_action_notifications_from_github_actions(
    *,
    cwd: Path | None = None,
    repo: str | None = None,
    workflow_file: str = DEFAULT_ACTION_STATE_SYNC_WORKFLOW,
    artifact_name: str = DEFAULT_ACTION_STATE_SYNC_ARTIFACT,
) -> GitHubActionStateResult:
    return _run_action_state_workflow(
        direction="export",
        action_state_json=None,
        cwd=cwd,
        repo=repo,
        workflow_file=workflow_file,
        artifact_name=artifact_name,
    )


def detect_github_repository(*, cwd: Path | None = None) -> str:
    result = _run_command(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=cwd,
        tool_name="git",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "missing origin remote"
        raise GitHubActionStateSyncError(
            f"failed to detect the GitHub repository: {detail}"
        )
    repository = parse_github_repository(result.stdout.strip())
    if repository is None:
        raise GitHubActionStateSyncError(
            "unsupported GitHub remote URL: "
            f"{(result.stdout or '').strip() or '<empty>'}"
        )
    return repository


def parse_github_repository(remote_url: str) -> str | None:
    value = remote_url.strip()
    if not value:
        return None
    for pattern in (_HTTPS_REPO_RE, _SSH_REPO_RE):
        match = pattern.match(value)
        if match is not None:
            return f"{match.group('owner')}/{match.group('repo')}"
    return None


def _run_action_state_workflow(
    *,
    direction: str,
    action_state_json: str | None,
    cwd: Path | None,
    repo: str | None,
    workflow_file: str,
    artifact_name: str,
) -> GitHubActionStateResult:
    target_repo = repo or detect_github_repository(cwd=cwd)
    workflow = workflow_file.strip()
    if not workflow:
        raise GitHubActionStateSyncError("workflow_file must not be empty")
    artifact = artifact_name.strip()
    if not artifact:
        raise GitHubActionStateSyncError("artifact_name must not be empty")

    command = [
        "gh",
        "workflow",
        "run",
        workflow,
        "--repo",
        target_repo,
        "-f",
        f"direction={direction}",
    ]
    if action_state_json is not None:
        command.extend(["-f", f"action_state_json={action_state_json}"])

    dispatch = _run_gh_command(
        command,
        cwd=cwd,
        error_prefix=f"failed to dispatch action state {direction} workflow",
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
        error_prefix=f"action state {direction} run {run_id} failed",
    )
    action_notifications = _download_action_state_artifact(
        run_id,
        cwd=cwd,
        repo=target_repo,
        artifact_name=artifact,
    )
    return GitHubActionStateResult(
        repository=target_repo,
        run_id=run_id,
        run_url=run_url,
        action_notifications=action_notifications,
    )


def _download_action_state_artifact(
    run_id: str,
    *,
    cwd: Path | None,
    repo: str,
    artifact_name: str,
) -> dict[str, dict[str, str]]:
    with tempfile.TemporaryDirectory(prefix="paper-digest-action-state-") as temp_dir:
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
                f"failed to download action state artifact {artifact_name!r} "
                f"from run {run_id}"
            ),
        )
        matches = sorted(temp_path.rglob("action-state.json"))
        if not matches:
            raise GitHubActionStateSyncError(
                f"action state artifact {artifact_name!r} from run {run_id} "
                "did not contain action-state.json"
            )
        try:
            return parse_action_notifications_payload(
                matches[0].read_text(encoding="utf-8")
            )
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise GitHubActionStateSyncError(
                f"failed to parse action-state.json from run {run_id}: {exc}"
            ) from exc


def _extract_run_url(value: str) -> str:
    for token in value.split():
        if "github.com" in token and "/actions/runs/" in token:
            return token.strip()
    raise GitHubActionStateSyncError(
        "failed to determine the GitHub Actions run URL for action state sync"
    )


def _extract_run_id(run_url: str) -> str:
    match = _RUN_URL_RE.search(run_url)
    if match is None:
        raise GitHubActionStateSyncError(
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
        raise GitHubActionStateSyncError(f"{error_prefix}: {detail}")
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
        raise GitHubActionStateSyncError(
            f"{tool_name} is required for action state sync."
        ) from exc
