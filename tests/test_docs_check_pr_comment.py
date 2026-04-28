from __future__ import annotations

import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tools.docs_check_pr_comment import (
    DocsCheckCommentContext,
    DocsCheckCommentDecision,
    WorkflowArtifact,
    decide_docs_check_comment_action,
    main_decide_comment,
    main_resolve_context,
    resolve_docs_check_comment_context,
)
from tools.docs_pipeline import (
    DOCS_CHECK_COMMAND,
    DocsCheckReport,
    DocsCheckReportCheck,
    docs_check_report_to_payload,
)


class DocsCheckPrCommentTests(unittest.TestCase):
    def test_resolve_docs_check_comment_context_requires_pr_and_artifact_match(
        self,
    ) -> None:
        event_payload = {
            "workflow_run": {
                "id": 42,
                "pull_requests": [{"number": 7}],
            }
        }
        context = resolve_docs_check_comment_context(
            event_payload,
            (
                WorkflowArtifact(name="other", expired=False),
                WorkflowArtifact(name="docs-check-report", expired=True),
                WorkflowArtifact(name="docs-check-report", expired=False),
            ),
        )
        self.assertEqual(
            context,
            DocsCheckCommentContext(
                pr_number=7,
                workflow_run_id=42,
                artifact_found=True,
            ),
        )

        with self.assertRaisesRegex(ValueError, "did not include an attached PR"):
            resolve_docs_check_comment_context(
                {"workflow_run": {"id": 42, "pull_requests": []}},
                (),
            )

    def test_decide_docs_check_comment_action_returns_delete_or_upsert(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            comment_path = Path(tmpdir) / "comment.md"
            report_path.write_text(
                json.dumps(
                    docs_check_report_to_payload(
                        DocsCheckReport(
                            schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                            status=DOCS_CHECK_COMMAND.failed_status,
                            exit_code=1,
                            root="/tmp/repo",
                            markdown_count=1,
                            github_metadata_count=0,
                            check_count=1,
                            failed_check_count=1,
                            preflight_findings=(),
                            checks=(
                                DocsCheckReportCheck(
                                    name="broken",
                                    report_label="Broken check",
                                    status=DOCS_CHECK_COMMAND.failed_status,
                                    findings=(),
                                ),
                            ),
                        )
                    )
                ),
                encoding="utf-8",
            )
            comment_path.write_text(
                "<!-- docs-check-report-comment -->\n## Docs Check\n",
                encoding="utf-8",
            )

            decision = decide_docs_check_comment_action(report_path, comment_path)
            self.assertEqual(
                decision,
                DocsCheckCommentDecision(
                    mode="upsert",
                    marker="<!-- docs-check-report-comment -->",
                    comment_body="<!-- docs-check-report-comment -->\n## Docs Check",
                ),
            )

            report_path.write_text(
                json.dumps(
                    docs_check_report_to_payload(
                        DocsCheckReport(
                            schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                            status=DOCS_CHECK_COMMAND.passed_status,
                            exit_code=0,
                            root="/tmp/repo",
                            markdown_count=1,
                            github_metadata_count=0,
                            check_count=0,
                            failed_check_count=0,
                            preflight_findings=(),
                            checks=(),
                        )
                    )
                ),
                encoding="utf-8",
            )
            delete_decision = decide_docs_check_comment_action(
                report_path,
                comment_path,
            )
            self.assertEqual(delete_decision.mode, "delete")
            self.assertIsNone(delete_decision.comment_body)

            comment_path.write_text("## Docs Check\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "marker is missing"):
                decide_docs_check_comment_action(report_path, comment_path)

    def test_main_resolve_context_writes_outputs_and_reports_missing_inputs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            event_path = Path(tmpdir) / "event.json"
            event_path.write_text(
                json.dumps(
                    {
                        "workflow_run": {
                            "id": 55,
                            "pull_requests": [{"number": 12}],
                        }
                    }
                ),
                encoding="utf-8",
            )
            stdout = StringIO()
            with patch(
                "tools.docs_check_pr_comment.GitHubWorkflowArtifactsService"
            ) as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.list_artifacts.return_value = (
                    WorkflowArtifact(name="docs-check-report", expired=False),
                )
                exit_code = main_resolve_context(
                    repo="owner/repo",
                    env={
                        "GITHUB_TOKEN": "token",
                        "GITHUB_EVENT_PATH": str(event_path),
                    },
                    stdout=stdout,
                )

        self.assertEqual(exit_code, 0)
        self.assertIn('"artifact-found": "true"', stdout.getvalue())
        self.assertIn('"pr-number": "12"', stdout.getvalue())
        mock_service_class.assert_called_once_with(
            repository="owner/repo",
            token="token",
        )

        stderr = StringIO()
        exit_code = main_resolve_context(
            repo="owner/repo",
            env={"GITHUB_EVENT_PATH": "missing"},
            stderr=stderr,
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("missing GitHub token", stderr.getvalue())

    def test_main_decide_comment_writes_outputs_and_reports_invalid_comment(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            comment_path = Path(tmpdir) / "comment.md"
            report_path.write_text(
                json.dumps(
                    docs_check_report_to_payload(
                        DocsCheckReport(
                            schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                            status=DOCS_CHECK_COMMAND.failed_status,
                            exit_code=1,
                            root="/tmp/repo",
                            markdown_count=1,
                            github_metadata_count=0,
                            check_count=1,
                            failed_check_count=1,
                            preflight_findings=(),
                            checks=(
                                DocsCheckReportCheck(
                                    name="broken",
                                    report_label="Broken check",
                                    status=DOCS_CHECK_COMMAND.failed_status,
                                    findings=(),
                                ),
                            ),
                        )
                    )
                ),
                encoding="utf-8",
            )
            comment_path.write_text(
                "<!-- docs-check-report-comment -->\n## Docs Check\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            exit_code = main_decide_comment(
                report_file=report_path,
                comment_file=comment_path,
                stdout=stdout,
            )
            self.assertEqual(exit_code, 0)
            self.assertIn('"mode": "upsert"', stdout.getvalue())

            comment_path.write_text("broken\n", encoding="utf-8")
            stderr = StringIO()
            exit_code = main_decide_comment(
                report_file=report_path,
                comment_file=comment_path,
                stderr=stderr,
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("decision failed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
