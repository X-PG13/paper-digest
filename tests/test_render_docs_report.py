from __future__ import annotations

import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from tools.docs_pipeline import (
    DOCS_CHECK_COMMAND,
    DocsCheckFinding,
    DocsCheckReport,
    DocsCheckReportCheck,
    docs_check_report_to_payload,
)
from tools.render_docs_report import (
    DocsCheckAnnotationCommand,
    DocsCheckCommentCommand,
    format_docs_check_github_annotations,
    format_docs_check_pr_comment,
    load_docs_check_report,
    main,
    validate_docs_check_annotation_command,
    validate_docs_check_comment_command,
)


class RenderDocsReportTests(unittest.TestCase):
    def test_validate_annotation_command_requires_placeholders(self) -> None:
        command = DocsCheckAnnotationCommand(
            expected_schema_version="",
            error_level="",
            warning_level="warning",
            preflight_title_template="Docs check preflight",
            failed_check_title_template="Docs check",
            skipped_check_title_template="Skipped",
            skipped_check_message_template="Did not run",
        )

        self.assertEqual(
            validate_docs_check_annotation_command(command),
            [
                "docs check annotation command: empty expected schema version",
                "docs check annotation command: empty error level",
                "docs check annotation command: failed check title template missing "
                "'{check_label}' placeholder",
                "docs check annotation command: failed check title template missing "
                "'{check_id}' placeholder",
                "docs check annotation command: skipped check title template missing "
                "'{check_label}' placeholder",
                "docs check annotation command: skipped check title template missing "
                "'{check_id}' placeholder",
                "docs check annotation command: skipped check message template missing "
                "'{check_label}' placeholder",
            ],
        )

    def test_format_docs_check_github_annotations_emits_errors_and_warnings(
        self,
    ) -> None:
        report = DocsCheckReport(
            schema_version=DOCS_CHECK_COMMAND.report_schema_version,
            status=DOCS_CHECK_COMMAND.preflight_failed_status,
            exit_code=1,
            root="/tmp/repo",
            markdown_count=1,
            github_metadata_count=0,
            check_count=2,
            failed_check_count=1,
            preflight_findings=(
                DocsCheckFinding(
                    message="config broken 100%\nnext line",
                    path="README.md",
                    line=7,
                    end_line=9,
                ),
            ),
            checks=(
                DocsCheckReportCheck(
                    name="broken",
                    report_label="Broken, docs: check",
                    status=DOCS_CHECK_COMMAND.failed_status,
                    findings=(
                        DocsCheckFinding(
                            message="drifted%\nline two",
                            path="docs/guide.md",
                            line=12,
                            end_line=15,
                        ),
                    ),
                ),
                DocsCheckReportCheck(
                    name="skipped",
                    report_label="Skipped check",
                    status=DOCS_CHECK_COMMAND.not_run_status,
                    findings=(),
                ),
            ),
        )

        self.assertEqual(
            format_docs_check_github_annotations(report),
            (
                "::error title=Docs check preflight,file=README.md,line=7,"
                "endLine=9::"
                "config broken 100%25%0Anext line",
                "::error title=Docs check [broken]%3A Broken%2C docs%3A "
                "check,file=docs/guide.md,line=12,endLine=15::"
                "drifted%25%0Aline two",
                "::warning title=Docs check skipped [skipped]%3A Skipped check::"
                "Skipped check did not run because docs check failed before "
                "execution.",
            ),
        )

    def test_format_docs_check_github_annotations_uses_warning_severity(self) -> None:
        report = DocsCheckReport(
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
                    findings=(
                        DocsCheckFinding(message="warn only", severity="warning"),
                    ),
                ),
            ),
        )

        self.assertEqual(
            format_docs_check_github_annotations(report),
            ("::warning title=Docs check [broken]%3A Broken check::warn only",),
        )

    def test_validate_comment_command_requires_placeholders(self) -> None:
        command = DocsCheckCommentCommand(
            expected_schema_version="",
            comment_marker="",
            title="",
            passed_summary_template="passed",
            failed_summary_template="failed",
            preflight_failed_summary_template="preflight",
            failed_check_heading_template="heading",
            skipped_checks_heading="",
            preflight_heading="",
            failed_checks_heading="",
        )

        self.assertEqual(
            validate_docs_check_comment_command(command),
            [
                "docs check comment command: empty expected schema version",
                "docs check comment command: empty comment marker",
                "docs check comment command: empty title",
                "docs check comment command: passed summary template missing "
                "'{markdown_count}' placeholder",
                "docs check comment command: passed summary template missing "
                "'{github_metadata_count}' placeholder",
                "docs check comment command: failed summary template missing "
                "'{failed_check_count}' placeholder",
                "docs check comment command: failed summary template missing "
                "'{check_count}' placeholder",
                "docs check comment command: preflight summary template missing "
                "'{preflight_error_count}' placeholder",
                "docs check comment command: failed check heading template missing "
                "'{check_id}' placeholder",
                "docs check comment command: failed check heading template missing "
                "'{check_label}' placeholder",
                "docs check comment command: empty preflight heading",
                "docs check comment command: empty failed checks heading",
                "docs check comment command: empty skipped checks heading",
            ],
        )

    def test_format_docs_check_pr_comment_groups_failed_and_skipped_checks(
        self,
    ) -> None:
        report = DocsCheckReport(
            schema_version=DOCS_CHECK_COMMAND.report_schema_version,
            status=DOCS_CHECK_COMMAND.failed_status,
            exit_code=1,
            root="/tmp/repo",
            markdown_count=1,
            github_metadata_count=0,
            check_count=2,
            failed_check_count=1,
            preflight_findings=(),
            checks=(
                DocsCheckReportCheck(
                    name="broken",
                    report_label="Broken check",
                    status=DOCS_CHECK_COMMAND.failed_status,
                    findings=(
                        DocsCheckFinding(
                            message="drifted",
                            path="docs/guide.md",
                            line=12,
                            end_line=15,
                        ),
                    ),
                ),
                DocsCheckReportCheck(
                    name="skipped",
                    report_label="Skipped check",
                    status=DOCS_CHECK_COMMAND.not_run_status,
                    findings=(),
                ),
            ),
        )

        rendered = format_docs_check_pr_comment(report)

        self.assertIn("<!-- docs-check-report-comment -->", rendered)
        self.assertIn("#### `broken` · Broken check", rendered)
        self.assertIn("- `docs/guide.md:12-15` drifted", rendered)
        self.assertIn("### Skipped Checks", rendered)
        self.assertIn("- `skipped` Skipped check", rendered)

    def test_load_docs_check_report_round_trips_payload(self) -> None:
        report = DocsCheckReport(
            schema_version=DOCS_CHECK_COMMAND.report_schema_version,
            status=DOCS_CHECK_COMMAND.passed_status,
            exit_code=0,
            root="/tmp/repo",
            markdown_count=3,
            github_metadata_count=2,
            check_count=1,
            failed_check_count=0,
            preflight_findings=(),
            checks=(
                DocsCheckReportCheck(
                    name="links",
                    report_label="Markdown links",
                    status=DOCS_CHECK_COMMAND.passed_status,
                    findings=(),
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "docs-check-report.json"
            report_file.write_text(
                json.dumps(docs_check_report_to_payload(report)),
                encoding="utf-8",
            )

            self.assertEqual(load_docs_check_report(report_file), report)

    def test_load_docs_check_report_rejects_mismatched_preflight_findings(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "docs-check-report.json"
            report_file.write_text(
                json.dumps(
                    {
                        "schema_version": DOCS_CHECK_COMMAND.report_schema_version,
                        "status": "failed",
                        "exit_code": 1,
                        "root": "/tmp/repo",
                        "counts": {
                            "markdown_files": 0,
                            "github_metadata_files": 0,
                            "checks": 0,
                            "failed_checks": 0,
                        },
                        "preflight_errors": ["wrong"],
                        "preflight_findings": [
                            {
                                "message": "different",
                                "severity": "error",
                                "path": None,
                                "line": None,
                                "end_line": None,
                            }
                        ],
                        "checks": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "preflight_errors does not match preflight findings",
            ):
                load_docs_check_report(report_file)

    def test_main_renders_markdown_to_stdout(self) -> None:
        report = DocsCheckReport(
            schema_version=DOCS_CHECK_COMMAND.report_schema_version,
            status=DOCS_CHECK_COMMAND.passed_status,
            exit_code=0,
            root="/tmp/repo",
            markdown_count=3,
            github_metadata_count=2,
            check_count=1,
            failed_check_count=0,
            preflight_findings=(),
            checks=(
                DocsCheckReportCheck(
                    name="links",
                    report_label="Markdown links",
                    status=DOCS_CHECK_COMMAND.passed_status,
                    findings=(),
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "docs-check-report.json"
            report_file.write_text(
                json.dumps(docs_check_report_to_payload(report)),
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()

            exit_code = main(
                report_file=report_file,
                output_format="markdown",
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("## Docs Check", stdout.getvalue())
            self.assertIn("| Markdown links | `passed` | 0 |", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    def test_main_renders_pr_comment_to_stdout(self) -> None:
        report = DocsCheckReport(
            schema_version=DOCS_CHECK_COMMAND.report_schema_version,
            status=DOCS_CHECK_COMMAND.passed_status,
            exit_code=0,
            root="/tmp/repo",
            markdown_count=3,
            github_metadata_count=2,
            check_count=1,
            failed_check_count=0,
            preflight_findings=(),
            checks=(
                DocsCheckReportCheck(
                    name="links",
                    report_label="Markdown links",
                    status=DOCS_CHECK_COMMAND.passed_status,
                    findings=(),
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "docs-check-report.json"
            report_file.write_text(
                json.dumps(docs_check_report_to_payload(report)),
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()

            exit_code = main(
                report_file=report_file,
                output_format="pr-comment",
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("<!-- docs-check-report-comment -->", stdout.getvalue())
            self.assertIn("Docs check passed for 3 Markdown files", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    def test_main_reports_invalid_report_to_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "docs-check-report.json"
            report_file.write_text(
                json.dumps(
                    {
                        "schema_version": "999",
                        "status": "passed",
                        "exit_code": 0,
                        "root": "/tmp/repo",
                        "counts": {
                            "markdown_files": 0,
                            "github_metadata_files": 0,
                            "checks": 0,
                            "failed_checks": 0,
                        },
                        "preflight_errors": [],
                        "preflight_findings": [],
                        "checks": [],
                    }
                ),
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()

            exit_code = main(report_file=report_file, stdout=stdout, stderr=stderr)

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("unsupported schema version", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
