from __future__ import annotations

import unittest
from io import StringIO
from unittest.mock import patch

from tools.github_services import (
    GitHubIssueLabelsService,
    IssueLabelSyncResult,
    normalize_labels,
)
from tools.sync_issue_labels import (
    main,
    sync_issue_labels,
)


class FakeClient:
    def __init__(self, labels: list[str]) -> None:
        self.labels = list(labels)
        self.added: list[tuple[int, tuple[str, ...]]] = []
        self.removed: list[tuple[int, str]] = []

    def list_issue_labels(self, issue_number: int) -> tuple[str, ...]:
        return tuple(self.labels)

    def add_labels(self, issue_number: int, labels: tuple[str, ...]) -> None:
        self.added.append((issue_number, labels))
        for label in labels:
            if label not in self.labels:
                self.labels.append(label)

    def remove_label(self, issue_number: int, label: str) -> None:
        self.removed.append((issue_number, label))
        if label in self.labels:
            self.labels.remove(label)


class SyncIssueLabelsTests(unittest.TestCase):
    def test_normalize_labels_deduplicates_and_strips(self) -> None:
        self.assertEqual(
            normalize_labels([" needs-info ", "", "bug", "bug"]),
            ("needs-info", "bug"),
        )

    def test_sync_issue_labels_adds_removes_and_noops(self) -> None:
        client = FakeClient(["bug", "stale"])
        result = sync_issue_labels(
            GitHubIssueLabelsService(client=client),
            12,
            ensure_labels=("needs-info", "bug"),
            remove_labels=("stale",),
        )
        self.assertEqual(
            result,
            IssueLabelSyncResult(added=("needs-info",), removed=("stale",)),
        )
        self.assertEqual(client.added, [(12, ("needs-info",))])
        self.assertEqual(client.removed, [(12, "stale")])

        noop_client = FakeClient(["bug"])
        noop_result = sync_issue_labels(
            GitHubIssueLabelsService(client=noop_client),
            18,
            ensure_labels=("bug",),
            remove_labels=("stale",),
        )
        self.assertEqual(noop_result, IssueLabelSyncResult(added=(), removed=()))
        self.assertEqual(noop_client.added, [])
        self.assertEqual(noop_client.removed, [])

    def test_sync_issue_labels_rejects_overlapping_targets(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            sync_issue_labels(
                GitHubIssueLabelsService(client=FakeClient(["bug"])),
                5,
                ensure_labels=("needs-info",),
                remove_labels=("needs-info",),
            )

    def test_main_writes_summary_and_reports_missing_token(self) -> None:
        stdout = StringIO()
        with patch(
            "tools.sync_issue_labels.GitHubIssueLabelsService"
        ) as mock_service_class:
            mock_service_class.return_value.sync_labels.return_value = (
                IssueLabelSyncResult(added=("needs-info",), removed=())
            )
            exit_code = main(
                repo="owner/repo",
                issue_number=14,
                ensure_labels=("needs-info",),
                env={"GITHUB_TOKEN": "token"},
                stdout=stdout,
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("added needs-info", stdout.getvalue())
        mock_service_class.assert_called_once_with(
            repository="owner/repo",
            token="token",
        )

        stderr = StringIO()
        exit_code = main(
            repo="owner/repo",
            issue_number=14,
            ensure_labels=("needs-info",),
            env={},
            stderr=stderr,
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("missing GitHub token", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
