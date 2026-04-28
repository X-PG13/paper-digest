from __future__ import annotations

import unittest
from io import StringIO
from unittest.mock import patch

from tools.community_pr_labels import (
    desired_pr_labels,
    is_documentation_path,
    is_maintenance_path,
    main,
)
from tools.github_services import IssueLabelSyncResult


class CommunityPrLabelsTests(unittest.TestCase):
    def test_path_helpers_and_desired_labels_cover_supported_routes(self) -> None:
        self.assertTrue(is_documentation_path("README.md"))
        self.assertTrue(is_documentation_path("docs/guide.md"))
        self.assertFalse(is_documentation_path("paper_digest/service.py"))
        self.assertTrue(is_maintenance_path(".github/workflows/ci.yml"))
        self.assertTrue(is_maintenance_path("Makefile"))
        self.assertFalse(is_maintenance_path("README.md"))

        labels = desired_pr_labels(
            [
                "docs/guide.md",
                ".github/workflows/ci.yml",
                ".github/dependabot.yml",
                "docs/adr/0001-test.md",
            ],
            actor="dependabot[bot]",
        )
        self.assertEqual(
            labels,
            ("documentation", "maintenance", "dependencies", "proposal"),
        )

    def test_main_syncs_labels_and_reports_missing_token(self) -> None:
        stdout = StringIO()
        with (
            patch(
                "tools.community_pr_labels.GitHubPullRequestFilesService"
            ) as mock_pull_service_class,
            patch(
                "tools.community_pr_labels.GitHubIssueLabelsService"
            ) as mock_label_service_class,
        ):
            mock_pull_service_class.return_value.list_paths.return_value = (
                "docs/guide.md",
                ".github/workflows/ci.yml",
            )
            mock_label_service_class.return_value.sync_labels.return_value = (
                IssueLabelSyncResult(added=("documentation",), removed=())
            )
            exit_code = main(
                repo="owner/repo",
                pull_number=9,
                actor="octocat",
                env={"GITHUB_TOKEN": "token"},
                stdout=stdout,
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("added documentation", stdout.getvalue())
        mock_pull_service_class.assert_called_once_with(
            repository="owner/repo",
            token="token",
        )
        mock_label_service_class.assert_called_once_with(
            repository="owner/repo",
            token="token",
        )
        mock_label_service_class.return_value.sync_labels.assert_called_once_with(
            9,
            ensure_labels=("documentation", "maintenance"),
            remove_labels=(),
        )

        stderr = StringIO()
        exit_code = main(
            repo="owner/repo",
            pull_number=9,
            actor="octocat",
            env={},
            stderr=stderr,
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("missing GitHub token", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
