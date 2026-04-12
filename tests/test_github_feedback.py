from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from paper_digest.feedback import FeedbackEntry, FeedbackState
from paper_digest.github_feedback import (
    DEFAULT_FEEDBACK_SECRET_NAME,
    GitHubFeedbackSyncError,
    detect_github_repository,
    parse_github_repository,
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
