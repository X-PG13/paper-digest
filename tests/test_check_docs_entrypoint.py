from __future__ import annotations

import tempfile
import unittest
from io import StringIO
from pathlib import Path

from tools.check_docs import main
from tools.docs_pipeline import (
    DOCS_CHECK_COMMAND,
    DOCS_CHECK_PIPELINE,
    DocsCheck,
    DocsCheckCommand,
    DocsCheckPipeline,
)


class CheckDocsEntrypointTests(unittest.TestCase):
    def test_main_writes_success_message_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            command = DocsCheckCommand(
                root=root,
                pipeline=DocsCheckPipeline(
                    checks=(DocsCheck("pass", "Pass check", lambda _: []),),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=0,
                failure_exit_code=1,
                report_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                passed_status=DOCS_CHECK_COMMAND.passed_status,
                failed_status=DOCS_CHECK_COMMAND.failed_status,
                preflight_failed_status=(DOCS_CHECK_COMMAND.preflight_failed_status),
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=(DOCS_CHECK_COMMAND.failure_summary_template),
                failure_detail_template=(DOCS_CHECK_COMMAND.failure_detail_template),
            )

            exit_code = main(command=command, stdout=stdout, stderr=stderr)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                stdout.getvalue(),
                "Docs check passed for 1 Markdown files and 0 GitHub metadata files.\n",
            )
            self.assertEqual(stderr.getvalue(), "")

    def test_main_writes_errors_to_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            stdout = StringIO()
            stderr = StringIO()
            command = DocsCheckCommand(
                root=root,
                pipeline=DocsCheckPipeline(
                    checks=(
                        DocsCheck(
                            "fail",
                            "Failure check",
                            lambda _: ["pipeline drift"],
                        ),
                    ),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=0,
                failure_exit_code=5,
                report_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                passed_status=DOCS_CHECK_COMMAND.passed_status,
                failed_status=DOCS_CHECK_COMMAND.failed_status,
                preflight_failed_status=(DOCS_CHECK_COMMAND.preflight_failed_status),
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template="SUMMARY {failed_check_count}/{check_count}",
                failure_detail_template="ERROR[{check_label}] {error}",
            )

            exit_code = main(command=command, stdout=stdout, stderr=stderr)

            self.assertEqual(exit_code, 5)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(
                stderr.getvalue(),
                "SUMMARY 1/1\nERROR[Failure check] pipeline drift\n",
            )

    def test_main_writes_json_report_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            command = DocsCheckCommand(
                root=root,
                pipeline=DocsCheckPipeline(
                    checks=(DocsCheck("pass", "Pass check", lambda _: []),),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=0,
                failure_exit_code=1,
                report_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                passed_status=DOCS_CHECK_COMMAND.passed_status,
                failed_status=DOCS_CHECK_COMMAND.failed_status,
                preflight_failed_status=(DOCS_CHECK_COMMAND.preflight_failed_status),
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=(DOCS_CHECK_COMMAND.failure_summary_template),
                failure_detail_template=(DOCS_CHECK_COMMAND.failure_detail_template),
            )

            exit_code = main(
                command=command,
                output_format="json",
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn('"status": "passed"', stdout.getvalue())
            self.assertIn('"report_label": "Pass check"', stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    def test_main_writes_json_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
            report_file = root / "reports" / "docs-check-report.json"
            stdout = StringIO()
            stderr = StringIO()
            command = DocsCheckCommand(
                root=root,
                pipeline=DocsCheckPipeline(
                    checks=(DocsCheck("pass", "Pass check", lambda _: []),),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=0,
                failure_exit_code=1,
                report_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                passed_status=DOCS_CHECK_COMMAND.passed_status,
                failed_status=DOCS_CHECK_COMMAND.failed_status,
                preflight_failed_status=(DOCS_CHECK_COMMAND.preflight_failed_status),
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=(DOCS_CHECK_COMMAND.failure_summary_template),
                failure_detail_template=(DOCS_CHECK_COMMAND.failure_detail_template),
            )

            exit_code = main(
                command=command,
                output_format="text",
                json_report_file=report_file,
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(report_file.exists())
            self.assertIn('"status": "passed"', report_file.read_text(encoding="utf-8"))
            self.assertEqual(
                stdout.getvalue(),
                "Docs check passed for 1 Markdown files and 0 GitHub metadata files.\n",
            )
            self.assertEqual(stderr.getvalue(), "")

    def test_main_writes_markdown_report_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            command = DocsCheckCommand(
                root=root,
                pipeline=DocsCheckPipeline(
                    checks=(DocsCheck("pass", "Pass check", lambda _: []),),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=0,
                failure_exit_code=1,
                report_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                passed_status=DOCS_CHECK_COMMAND.passed_status,
                failed_status=DOCS_CHECK_COMMAND.failed_status,
                preflight_failed_status=(DOCS_CHECK_COMMAND.preflight_failed_status),
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=(DOCS_CHECK_COMMAND.failure_summary_template),
                failure_detail_template=(DOCS_CHECK_COMMAND.failure_detail_template),
            )

            exit_code = main(
                command=command,
                output_format="markdown",
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("## Docs Check", stdout.getvalue())
            self.assertIn("| Pass check | `passed` | 0 |", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    def test_main_writes_markdown_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
            report_file = root / "reports" / "docs-check-summary.md"
            stdout = StringIO()
            stderr = StringIO()
            command = DocsCheckCommand(
                root=root,
                pipeline=DocsCheckPipeline(
                    checks=(DocsCheck("pass", "Pass check", lambda _: []),),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=0,
                failure_exit_code=1,
                report_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                passed_status=DOCS_CHECK_COMMAND.passed_status,
                failed_status=DOCS_CHECK_COMMAND.failed_status,
                preflight_failed_status=(DOCS_CHECK_COMMAND.preflight_failed_status),
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=(DOCS_CHECK_COMMAND.failure_summary_template),
                failure_detail_template=(DOCS_CHECK_COMMAND.failure_detail_template),
            )

            exit_code = main(
                command=command,
                markdown_report_file=report_file,
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(report_file.exists())
            self.assertIn("## Docs Check", report_file.read_text(encoding="utf-8"))
            self.assertEqual(
                stdout.getvalue(),
                "Docs check passed for 1 Markdown files and 0 GitHub metadata files.\n",
            )
            self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
