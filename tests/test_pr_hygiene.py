from __future__ import annotations

import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tools.pr_hygiene import (
    PR_HYGIENE_MARKER,
    body_has_issue_reference,
    evaluate_pr_hygiene,
    has_reference,
    main,
)


class PrHygieneTests(unittest.TestCase):
    def test_reference_helpers_cover_keywords_and_links(self) -> None:
        self.assertTrue(has_reference("see #12"))
        self.assertTrue(has_reference("https://example.com/issues/12"))
        self.assertFalse(has_reference("no reference"))
        self.assertTrue(body_has_issue_reference("Fixes #44", ""))
        self.assertTrue(body_has_issue_reference("", "related /pull/2"))
        self.assertFalse(body_has_issue_reference("no ref", ""))

    def test_evaluate_pr_hygiene_returns_delete_when_acknowledged_or_docs_only(
        self,
    ) -> None:
        body = (
            "- [x] No changelog entry needed.\n"
            "- [x] No doc update needed.\n"
            "- [x] No linked issue needed.\n"
            "- Linked issue or proposal: #12\n"
        )
        result = evaluate_pr_hygiene(body, ["paper_digest/service.py"])
        self.assertEqual(result.mode, "delete")
        self.assertIsNone(result.comment_body)

        docs_only = evaluate_pr_hygiene("", ["README.md", "tests/test_cli.py"])
        self.assertEqual(docs_only.mode, "delete")

    def test_evaluate_pr_hygiene_collects_expected_reminders(self) -> None:
        result = evaluate_pr_hygiene("", ["paper_digest/service.py"])
        self.assertEqual(result.mode, "upsert")
        self.assertEqual(len(result.reminders), 3)
        assert result.comment_body is not None
        self.assertIn(PR_HYGIENE_MARKER, result.comment_body)
        self.assertIn("CHANGELOG.md", result.comment_body)
        self.assertIn("No linked issue needed.", result.comment_body)

    def test_main_writes_github_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.txt"
            env = {
                "GITHUB_TOKEN": "token",
                "PR_BODY": "",
                "GITHUB_OUTPUT": str(output_path),
            }
            with patch(
                "tools.pr_hygiene.GitHubPullRequestFilesService"
            ) as mock_service_class:
                mock_service_class.return_value.list_paths.return_value = (
                    "paper_digest/service.py",
                )
                exit_code = main(
                    repo="owner/repo",
                    pull_number=9,
                    env=env,
                )
            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("mode=upsert", output_text)
        self.assertIn("marker=<!-- pr-hygiene-reminder -->", output_text)
        self.assertIn("comment-body<<", output_text)
        mock_service_class.assert_called_once_with(
            repository="owner/repo",
            token="token",
        )

    def test_main_reports_missing_token(self) -> None:
        stderr = StringIO()
        exit_code = main(
            repo="owner/repo",
            pull_number=9,
            env={"PR_BODY": ""},
            stderr=stderr,
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("missing GitHub token", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
