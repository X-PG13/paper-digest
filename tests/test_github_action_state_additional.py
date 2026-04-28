from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from paper_digest.github_action_state import (
    GitHubActionStateSyncError,
    detect_github_repository,
    parse_github_repository,
    pull_action_notifications_from_github_actions,
    sync_action_notifications_to_github_actions,
)


class GitHubActionStateAdditionalTests(unittest.TestCase):
    def test_parse_github_repository_rejects_blank_input(self) -> None:
        self.assertIsNone(parse_github_repository("   "))

    @patch("paper_digest.github_action_state.subprocess.run")
    def test_detect_github_repository_reports_git_failures_and_unsupported_remotes(
        self,
        mock_run,
    ) -> None:
        mock_run.return_value = _completed_process(
            returncode=1,
            stderr="fatal: no remote",
        )
        with self.assertRaisesRegex(
            GitHubActionStateSyncError,
            "failed to detect the GitHub repository: fatal: no remote",
        ):
            detect_github_repository(cwd=Path("/tmp/example"))

        mock_run.return_value = _completed_process(stdout="https://example.com/not-github")
        with self.assertRaisesRegex(
            GitHubActionStateSyncError,
            "unsupported GitHub remote URL",
        ):
            detect_github_repository(cwd=Path("/tmp/example"))

    def test_sync_helpers_validate_non_empty_workflow_and_artifact_names(self) -> None:
        with self.assertRaisesRegex(
            GitHubActionStateSyncError,
            "workflow_file must not be empty",
        ):
            sync_action_notifications_to_github_actions(
                {},
                repo="X-PG13/paper-digest",
                workflow_file=" ",
            )

        with self.assertRaisesRegex(
            GitHubActionStateSyncError,
            "artifact_name must not be empty",
        ):
            pull_action_notifications_from_github_actions(
                repo="X-PG13/paper-digest",
                artifact_name=" ",
            )

    @patch("paper_digest.github_action_state.subprocess.run")
    def test_pull_action_notifications_rejects_missing_run_url(self, mock_run) -> None:
        mock_run.return_value = _completed_process(stdout="no run url here")

        with self.assertRaisesRegex(
            GitHubActionStateSyncError,
            "failed to determine the GitHub Actions run URL",
        ):
            pull_action_notifications_from_github_actions(
                repo="X-PG13/paper-digest"
            )

    @patch("paper_digest.github_action_state.subprocess.run")
    def test_pull_action_notifications_rejects_invalid_run_id(self, mock_run) -> None:
        mock_run.return_value = _completed_process(
            stdout=(
                "https://github.com/X-PG13/paper-digest/"
                "actions/runs/not-a-number\n"
            )
        )

        with self.assertRaisesRegex(
            GitHubActionStateSyncError,
            "failed to extract run id from workflow URL",
        ):
            pull_action_notifications_from_github_actions(
                repo="X-PG13/paper-digest"
            )

    @patch("paper_digest.github_action_state.subprocess.run")
    def test_pull_action_notifications_requires_action_state_artifact_file(
        self,
        mock_run,
    ) -> None:
        def _side_effect(command, **_kwargs):
            if command[:3] == ["gh", "workflow", "run"]:
                return _completed_process(
                    stdout=(
                        "https://github.com/X-PG13/paper-digest/"
                        "actions/runs/123456789\n"
                    )
                )
            if command[:3] == ["gh", "run", "watch"]:
                return _completed_process()
            if command[:3] == ["gh", "run", "download"]:
                output_dir = Path(command[command.index("--dir") + 1])
                output_dir.mkdir(parents=True, exist_ok=True)
                return _completed_process()
            raise AssertionError(f"Unexpected command: {command!r}")

        mock_run.side_effect = _side_effect

        with self.assertRaisesRegex(
            GitHubActionStateSyncError,
            "did not contain action-state.json",
        ):
            pull_action_notifications_from_github_actions(
                repo="X-PG13/paper-digest"
            )

    @patch(
        "paper_digest.github_action_state.subprocess.run",
        side_effect=FileNotFoundError("gh missing"),
    )
    def test_detect_github_repository_requires_git_binary(self, _mock_run) -> None:
        with self.assertRaisesRegex(
            GitHubActionStateSyncError,
            "git is required for action state sync",
        ):
            detect_github_repository(cwd=Path("/tmp/example"))


def _completed_process(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
):
    class _Result:
        pass

    result = _Result()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result
