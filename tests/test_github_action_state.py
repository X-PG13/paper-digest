from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from paper_digest.github_action_state import (
    DEFAULT_ACTION_STATE_SYNC_ARTIFACT,
    DEFAULT_ACTION_STATE_SYNC_WORKFLOW,
    GitHubActionStateSyncError,
    parse_github_repository,
    pull_action_notifications_from_github_actions,
    sync_action_notifications_to_github_actions,
)


class GitHubActionStateTests(unittest.TestCase):
    def test_parse_github_repository_supports_https_and_ssh(self) -> None:
        self.assertEqual(
            parse_github_repository("https://github.com/X-PG13/paper-digest.git"),
            "X-PG13/paper-digest",
        )
        self.assertEqual(
            parse_github_repository("git@github.com:X-PG13/paper-digest.git"),
            "X-PG13/paper-digest",
        )
        self.assertEqual(
            parse_github_repository("ssh://git@github.com/X-PG13/paper-digest.git"),
            "X-PG13/paper-digest",
        )

    @patch("paper_digest.github_action_state.subprocess.run")
    def test_sync_action_notifications_dispatches_import_workflow(
        self,
        mock_run,
    ) -> None:
        def _side_effect(command, **kwargs):
            if command[:3] == ["git", "config", "--get"]:
                return _completed_process(
                    stdout="git@github.com:X-PG13/paper-digest.git\n"
                )
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
                (output_dir / "action-state.json").write_text(
                    (
                        "{\n"
                        '  "version": 1,\n'
                        '  "action_notifications": {\n'
                        '    "doi:10.5555/example": {\n'
                        '      "due_soon": "2026-04-13T09:30:00+00:00"\n'
                        "    }\n"
                        "  }\n"
                        "}\n"
                    ),
                    encoding="utf-8",
                )
                return _completed_process()
            raise AssertionError(f"Unexpected command: {command!r}")

        mock_run.side_effect = _side_effect

        result = sync_action_notifications_to_github_actions(
            {
                "doi:10.5555/example": {
                    "due_soon": "2026-04-13T09:30:00+00:00",
                }
            },
            cwd=Path("/tmp/example"),
        )

        self.assertEqual(result.repository, "X-PG13/paper-digest")
        self.assertEqual(result.run_id, "123456789")
        workflow_call = mock_run.call_args_list[1]
        self.assertEqual(
            workflow_call.args[0][:4],
            ["gh", "workflow", "run", DEFAULT_ACTION_STATE_SYNC_WORKFLOW],
        )
        self.assertIn("direction=import", workflow_call.args[0])
        self.assertIn("action_state_json=", workflow_call.args[0][-1])
        download_call = mock_run.call_args_list[3]
        self.assertEqual(download_call.args[0][:3], ["gh", "run", "download"])
        self.assertIn(DEFAULT_ACTION_STATE_SYNC_ARTIFACT, download_call.args[0])

    @patch("paper_digest.github_action_state.subprocess.run")
    def test_pull_action_notifications_downloads_export_artifact(
        self,
        mock_run,
    ) -> None:
        def _side_effect(command, **kwargs):
            if command[:3] == ["git", "config", "--get"]:
                return _completed_process(
                    stdout="git@github.com:X-PG13/paper-digest.git\n"
                )
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
                (output_dir / "action-state.json").write_text(
                    (
                        "{\n"
                        '  "version": 1,\n'
                        '  "action_notifications": {\n'
                        '    "doi:10.5555/example": {\n'
                        '      "overdue_3d": "2026-04-15T09:30:00+00:00"\n'
                        "    }\n"
                        "  }\n"
                        "}\n"
                    ),
                    encoding="utf-8",
                )
                return _completed_process()
            raise AssertionError(f"Unexpected command: {command!r}")

        mock_run.side_effect = _side_effect

        result = pull_action_notifications_from_github_actions(
            cwd=Path("/tmp/example")
        )

        self.assertEqual(result.repository, "X-PG13/paper-digest")
        self.assertEqual(
            result.action_notifications,
            {
                "doi:10.5555/example": {
                    "overdue_3d": "2026-04-15T09:30:00+00:00",
                }
            },
        )
        workflow_call = mock_run.call_args_list[1]
        self.assertIn("direction=export", workflow_call.args[0])

    @patch("paper_digest.github_action_state.subprocess.run")
    def test_pull_action_notifications_wraps_failed_workflow(self, mock_run) -> None:
        mock_run.side_effect = [
            _completed_process(stdout="git@github.com:X-PG13/paper-digest.git\n"),
            _completed_process(
                stdout=(
                    "https://github.com/X-PG13/paper-digest/actions/runs/123456789\n"
                )
            ),
            _completed_process(returncode=1, stderr="workflow failed"),
        ]

        with self.assertRaises(GitHubActionStateSyncError):
            pull_action_notifications_from_github_actions(cwd=Path("/tmp/example"))


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
