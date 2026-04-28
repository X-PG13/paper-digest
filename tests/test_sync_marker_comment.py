from __future__ import annotations

import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tools.github_resources import IssueComment
from tools.github_services import GitHubManagedCommentsService, find_marker_comment
from tools.sync_marker_comment import (
    DEFAULT_GITHUB_TOKEN_ENV,
    load_comment_body,
    main,
    sync_marker_comment,
)


class FakeClient:
    def __init__(self, comments: list[IssueComment]) -> None:
        self.comments = list(comments)
        self.created: list[tuple[int, str]] = []
        self.updated: list[tuple[int, str]] = []
        self.deleted: list[int] = []

    def list_issue_comments(self, issue_number: int) -> tuple[IssueComment, ...]:
        return tuple(self.comments)

    def create_issue_comment(self, issue_number: int, body: str) -> None:
        self.created.append((issue_number, body))

    def update_issue_comment(self, comment_id: int, body: str) -> None:
        self.updated.append((comment_id, body))

    def delete_issue_comment(self, comment_id: int) -> None:
        self.deleted.append(comment_id)


class SyncMarkerCommentTests(unittest.TestCase):
    def test_find_marker_comment_returns_first_match(self) -> None:
        comments = [
            IssueComment(comment_id=1, body="no marker here"),
            IssueComment(comment_id=2, body="<!-- marker -->\nhello"),
            IssueComment(comment_id=3, body="<!-- marker -->\nworld"),
        ]

        comment = find_marker_comment(comments, marker="<!-- marker -->")

        self.assertIsNotNone(comment)
        assert comment is not None
        self.assertEqual(comment.comment_id, 2)

    def test_sync_marker_comment_creates_updates_deletes_and_noops(self) -> None:
        client = FakeClient([])
        action = sync_marker_comment(
            GitHubManagedCommentsService(client=client),
            issue_number=12,
            marker="<!-- marker -->",
            desired_body="<!-- marker -->\ncreated",
        )
        self.assertEqual(action, "created")
        self.assertEqual(client.created, [(12, "<!-- marker -->\ncreated")])

        existing = FakeClient([IssueComment(comment_id=5, body="<!-- marker -->\nold")])
        action = sync_marker_comment(
            GitHubManagedCommentsService(client=existing),
            issue_number=12,
            marker="<!-- marker -->",
            desired_body="<!-- marker -->\nnew",
        )
        self.assertEqual(action, "updated")
        self.assertEqual(existing.updated, [(5, "<!-- marker -->\nnew")])

        unchanged = FakeClient(
            [IssueComment(comment_id=6, body="<!-- marker -->\nkeep")]
        )
        action = sync_marker_comment(
            GitHubManagedCommentsService(client=unchanged),
            issue_number=12,
            marker="<!-- marker -->",
            desired_body="<!-- marker -->\nkeep",
        )
        self.assertEqual(action, "unchanged")

        deleting = FakeClient([IssueComment(comment_id=7, body="<!-- marker -->\nbye")])
        action = sync_marker_comment(
            GitHubManagedCommentsService(client=deleting),
            issue_number=12,
            marker="<!-- marker -->",
            desired_body=None,
        )
        self.assertEqual(action, "deleted")
        self.assertEqual(deleting.deleted, [7])

    def test_sync_marker_comment_rejects_body_without_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "must include the configured marker"):
            sync_marker_comment(
                GitHubManagedCommentsService(client=FakeClient([])),
                issue_number=12,
                marker="<!-- marker -->",
                desired_body="missing marker",
            )

    def test_load_comment_body_reads_file_or_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "comment.md"
            path.write_text(" hello \n", encoding="utf-8")
            self.assertEqual(load_comment_body(body_file=path), "hello")

        with patch.dict(os.environ, {"COMMENT_BODY": " hi \n"}, clear=True):
            self.assertEqual(load_comment_body(body_env="COMMENT_BODY"), "hi")

    def test_main_reports_missing_token_and_empty_body(self) -> None:
        stderr = StringIO()
        exit_code = main(
            repo="owner/repo",
            issue_number=1,
            marker="<!-- marker -->",
            body_env="COMMENT_BODY",
            stderr=stderr,
        )
        self.assertEqual(exit_code, 1)
        self.assertIn(DEFAULT_GITHUB_TOKEN_ENV, stderr.getvalue())

        with patch.dict(
            os.environ,
            {DEFAULT_GITHUB_TOKEN_ENV: "token", "COMMENT_BODY": "   "},
            clear=True,
        ):
            stderr = StringIO()
            exit_code = main(
                repo="owner/repo",
                issue_number=1,
                marker="<!-- marker -->",
                body_env="COMMENT_BODY",
                stderr=stderr,
            )
        self.assertEqual(exit_code, 1)
        self.assertIn("comment body is empty", stderr.getvalue())

    def test_main_syncs_comment_through_client(self) -> None:
        stdout = StringIO()
        with patch.dict(
            os.environ,
            {
                DEFAULT_GITHUB_TOKEN_ENV: "token",
                "COMMENT_BODY": "<!-- marker -->\nbody",
            },
            clear=True,
        ):
            with patch(
                "tools.sync_marker_comment.GitHubManagedCommentsService"
            ) as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.sync_marker_comment.return_value = "created"
                exit_code = main(
                    repo="owner/repo",
                    issue_number=7,
                    marker="<!-- marker -->",
                    body_env="COMMENT_BODY",
                    stdout=stdout,
                )

        self.assertEqual(exit_code, 0)
        mock_service_class.assert_called_once_with(
            repository="owner/repo",
            token="token",
        )
        mock_service.sync_marker_comment.assert_called_once_with(
            issue_number=7,
            marker="<!-- marker -->",
            desired_body="<!-- marker -->\nbody",
        )
        self.assertEqual(stdout.getvalue().strip(), "created")


if __name__ == "__main__":
    unittest.main()
