from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from paper_digest.feedback import FeedbackEntry, FeedbackState
from paper_digest.github_feedback import (
    DEFAULT_FEEDBACK_PULL_ARTIFACT,
    DEFAULT_FEEDBACK_PULL_WORKFLOW,
    DEFAULT_FEEDBACK_SECRET_NAME,
    GitHubFeedbackSyncError,
    detect_github_repository,
    parse_github_repository,
    pull_feedback_from_github_secret,
    sync_feedback_to_github_secret,
)


class GitHubFeedbackTests(unittest.TestCase):
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
        self.assertIsNone(parse_github_repository("https://example.com/not-github"))

    @patch("paper_digest.github_feedback.subprocess.run")
    def test_detect_github_repository_reads_origin_remote(self, mock_run) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "git@github.com:X-PG13/paper-digest.git\n"
        mock_run.return_value.stderr = ""

        repository = detect_github_repository(cwd=Path("/tmp/example"))

        self.assertEqual(repository, "X-PG13/paper-digest")
        mock_run.assert_called_once()

    @patch("paper_digest.github_feedback.subprocess.run")
    def test_sync_feedback_to_github_secret_uses_gh_secret_set(
        self,
        mock_run,
    ) -> None:
        mock_run.side_effect = [
            _completed_process(stdout="git@github.com:X-PG13/paper-digest.git\n"),
            _completed_process(),
        ]
        feedback_state = FeedbackState(
            papers={
                "doi:10.5555/example": FeedbackEntry(
                    status="star",
                    updated_at=datetime(2026, 4, 12, 10, 0, tzinfo=UTC),
                    note="anchor paper",
                )
            }
        )

        repository = sync_feedback_to_github_secret(
            feedback_state,
            cwd=Path("/tmp/example"),
        )

        self.assertEqual(repository, "X-PG13/paper-digest")
        gh_call = mock_run.call_args_list[1]
        self.assertEqual(
            gh_call.args[0][:6],
            [
                "gh",
                "secret",
                "set",
                DEFAULT_FEEDBACK_SECRET_NAME,
                "--app",
                "actions",
            ],
        )
        self.assertIn("X-PG13/paper-digest", gh_call.args[0])
        self.assertIn('"doi:10.5555/example"', gh_call.args[0][-1])

    @patch("paper_digest.github_feedback.subprocess.run")
    def test_sync_feedback_to_github_secret_wraps_gh_failures(
        self,
        mock_run,
    ) -> None:
        mock_run.side_effect = [
            _completed_process(stdout="git@github.com:X-PG13/paper-digest.git\n"),
            _completed_process(returncode=1, stderr="permission denied"),
        ]
        feedback_state = FeedbackState(papers={})

        with self.assertRaises(GitHubFeedbackSyncError):
            sync_feedback_to_github_secret(feedback_state, cwd=Path("/tmp/example"))

    @patch("paper_digest.github_feedback.subprocess.run")
    def test_pull_feedback_from_github_secret_downloads_feedback_artifact(
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
                (output_dir / "feedback.json").write_text(
                    (
                        "{\n"
                        '  "version": 1,\n'
                        '  "papers": {\n'
                        '    "doi:10.5555/example": {\n'
                        '      "status": "star",\n'
                        '      "note": "anchor paper"\n'
                        "    }\n"
                        "  }\n"
                        "}\n"
                    ),
                    encoding="utf-8",
                )
                return _completed_process()
            raise AssertionError(f"Unexpected command: {command!r}")

        mock_run.side_effect = _side_effect

        result = pull_feedback_from_github_secret(cwd=Path("/tmp/example"))

        self.assertEqual(result.repository, "X-PG13/paper-digest")
        self.assertEqual(result.run_id, "123456789")
        self.assertEqual(
            result.run_url,
            "https://github.com/X-PG13/paper-digest/actions/runs/123456789",
        )
        self.assertEqual(
            result.feedback_state.papers["doi:10.5555/example"].status,
            "star",
        )
        workflow_call = mock_run.call_args_list[1]
        self.assertEqual(
            workflow_call.args[0][:4],
            ["gh", "workflow", "run", DEFAULT_FEEDBACK_PULL_WORKFLOW],
        )
        self.assertIn(
            f"secret_name={DEFAULT_FEEDBACK_SECRET_NAME}",
            workflow_call.args[0],
        )
        download_call = mock_run.call_args_list[3]
        self.assertEqual(
            download_call.args[0][:3],
            ["gh", "run", "download"],
        )
        self.assertIn(DEFAULT_FEEDBACK_PULL_ARTIFACT, download_call.args[0])

    @patch("paper_digest.github_feedback.subprocess.run")
    def test_pull_feedback_from_github_secret_wraps_failed_workflow(
        self,
        mock_run,
    ) -> None:
        mock_run.side_effect = [
            _completed_process(stdout="git@github.com:X-PG13/paper-digest.git\n"),
            _completed_process(
                stdout=(
                    "https://github.com/X-PG13/paper-digest/actions/runs/123456789\n"
                )
            ),
            _completed_process(returncode=1, stderr="workflow failed"),
        ]

        with self.assertRaises(GitHubFeedbackSyncError):
            pull_feedback_from_github_secret(cwd=Path("/tmp/example"))


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
