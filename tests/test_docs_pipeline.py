from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.docs_pipeline import (
    DOCS_CHECK_COMMAND,
    DOCS_CHECK_PIPELINE,
    DocsCheck,
    DocsCheckCommand,
    DocsCheckContext,
    DocsCheckFinding,
    DocsCheckPipeline,
    DocsCheckReport,
    DocsCheckReportCheck,
    DocsCheckRun,
    build_docs_check_context,
    docs_check_finding_from_legacy_error,
    docs_check_report_from_payload,
    docs_check_report_to_payload,
    format_docs_check_failure_detail,
    format_docs_check_failure_summary,
    format_docs_check_json_report,
    format_docs_check_markdown_report,
    format_docs_check_markdown_report_from_report,
    format_docs_check_preflight_failure_summary,
    format_docs_check_success_message,
    run_docs_check_command,
    run_docs_check_pipeline,
    validate_docs_check_command,
    validate_docs_check_pipeline,
)


class DocsPipelineTests(unittest.TestCase):
    def test_build_docs_check_context_collects_markdown_and_github_metadata(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
            workflow = root / ".github" / "workflows" / "ci.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("name: CI\n", encoding="utf-8")

            context = build_docs_check_context(root)

            self.assertEqual(context.root, root.resolve())
            self.assertEqual(
                context.markdown_files,
                ((root / "README.md").resolve(),),
            )
            self.assertEqual(
                context.github_metadata_files,
                (workflow.resolve(),),
            )

    def test_validate_docs_check_pipeline_accepts_repository_pipeline(self) -> None:
        self.assertEqual(validate_docs_check_pipeline(), [])

    def test_validate_docs_check_command_accepts_repository_command(self) -> None:
        self.assertEqual(validate_docs_check_command(), [])

    def test_validate_docs_check_pipeline_reports_duplicate_names_and_bad_template(
        self,
    ) -> None:
        pipeline = DocsCheckPipeline(
            checks=(
                DocsCheck("duplicate", "Duplicate", lambda _: []),
                DocsCheck("duplicate", "Duplicate", lambda _: []),
            ),
            success_message_template="Docs check passed.",
        )

        self.assertEqual(
            validate_docs_check_pipeline(pipeline),
            [
                "docs check pipeline: duplicate check names",
                "docs check pipeline: duplicate check report labels",
                "docs check pipeline: duplicate check ids",
                "docs check pipeline: success message template missing "
                "'{markdown_count}' placeholder",
                "docs check pipeline: success message template missing "
                "'{github_metadata_count}' placeholder",
            ],
        )

    def test_validate_docs_check_command_reports_invalid_command_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_root = Path(tmpdir) / "missing"
            command = DocsCheckCommand(
                root=missing_root,
                pipeline=DOCS_CHECK_PIPELINE,
                success_exit_code=1,
                failure_exit_code=1,
                report_schema_version="",
                passed_status="status",
                failed_status="status",
                preflight_failed_status="preflight",
                not_run_status="not-run",
                preflight_failure_summary_template="preflight",
                failure_summary_template="failure",
                failure_detail_template="detail",
            )

            self.assertEqual(
                validate_docs_check_command(command),
                [
                    "docs check command: success and failure exit codes must differ",
                    "docs check command: empty report schema version",
                    "docs check command: duplicate report status values",
                    "docs check command: preflight failure summary template "
                    "missing '{error_count}' placeholder",
                    "docs check command: failure summary template missing "
                    "'{failed_check_count}' placeholder",
                    "docs check command: failure summary template missing "
                    "'{check_count}' placeholder",
                    "docs check command: failure detail template missing "
                    "'{check_label}' placeholder",
                    "docs check command: failure detail template missing "
                    "'{error}' placeholder",
                    f"docs check command: root does not exist: {missing_root}",
                ],
            )

    def test_validate_docs_check_pipeline_reports_invalid_check_id_format(
        self,
    ) -> None:
        pipeline = DocsCheckPipeline(
            checks=(
                DocsCheck(
                    "Duplicate Name",
                    "Readable label",
                    lambda _: [],
                    check_id="Bad-ID",
                ),
            ),
            success_message_template=DOCS_CHECK_PIPELINE.success_message_template,
        )

        self.assertEqual(
            validate_docs_check_pipeline(pipeline),
            ["docs check pipeline: invalid check id format"],
        )

    def test_run_docs_check_pipeline_executes_checks_in_declared_order(self) -> None:
        calls: list[str] = []
        context = DocsCheckContext(
            root=Path("/tmp/example"),
            markdown_files=(),
            github_metadata_files=(),
        )
        pipeline = DocsCheckPipeline(
            checks=(
                DocsCheck(
                    "first",
                    "First check",
                    lambda _: calls.append("first") or ["error:first"],
                ),
                DocsCheck(
                    "second",
                    "Second check",
                    lambda _: calls.append("second") or ["error:second"],
                ),
            ),
            success_message_template=DOCS_CHECK_PIPELINE.success_message_template,
        )

        result = run_docs_check_pipeline(context, pipeline)

        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(
            result.check_runs,
            (
                DocsCheckRun(
                    name="first",
                    report_label="First check",
                    findings=(DocsCheckFinding(message="error:first"),),
                ),
                DocsCheckRun(
                    name="second",
                    report_label="Second check",
                    findings=(DocsCheckFinding(message="error:second"),),
                ),
            ),
        )

    def test_run_docs_check_pipeline_returns_structured_phase_results(self) -> None:
        context = DocsCheckContext(
            root=Path("/tmp/example"),
            markdown_files=(),
            github_metadata_files=(),
        )
        pipeline = DocsCheckPipeline(
            checks=(
                DocsCheck("first", "First check", lambda _: ["error:first"]),
                DocsCheck("second", "Second check", lambda _: []),
            ),
            success_message_template=DOCS_CHECK_PIPELINE.success_message_template,
        )

        result = run_docs_check_pipeline(context, pipeline)

        self.assertEqual(result.context, context)
        self.assertEqual(
            result.check_runs,
            (
                DocsCheckRun(
                    name="first",
                    report_label="First check",
                    findings=(DocsCheckFinding(message="error:first"),),
                ),
                DocsCheckRun(
                    name="second",
                    report_label="Second check",
                    findings=(),
                ),
            ),
        )
        self.assertEqual(result.failed_runs, (result.check_runs[0],))

    def test_format_docs_check_success_message_uses_context_counts(self) -> None:
        context = DocsCheckContext(
            root=Path("/tmp/example"),
            markdown_files=(Path("README.md"), Path("docs/guide.md")),
            github_metadata_files=(Path(".github/workflows/ci.yml"),),
        )

        self.assertEqual(
            format_docs_check_success_message(context),
            "Docs check passed for 2 Markdown files and 1 GitHub metadata files.",
        )

    def test_failure_format_helpers_use_command_templates(self) -> None:
        context = DocsCheckContext(
            root=Path("/tmp/example"),
            markdown_files=(),
            github_metadata_files=(),
        )
        pipeline = DocsCheckPipeline(
            checks=(DocsCheck("first", "First check", lambda _: ["error:first"]),),
            success_message_template=DOCS_CHECK_PIPELINE.success_message_template,
        )
        command = DocsCheckCommand(
            root=Path("/tmp/example"),
            pipeline=pipeline,
            success_exit_code=0,
            failure_exit_code=2,
            report_schema_version="report-v1",
            passed_status="passed",
            failed_status="failed",
            preflight_failed_status="preflight_failed",
            not_run_status="not_run",
            preflight_failure_summary_template="Preflight failed with {error_count}",
            failure_summary_template="Failed {failed_check_count}/{check_count}",
            failure_detail_template="{check_label}: {error}",
        )
        result = run_docs_check_pipeline(context, pipeline)

        self.assertEqual(
            format_docs_check_preflight_failure_summary(3, command),
            "Preflight failed with 3",
        )
        self.assertEqual(
            format_docs_check_failure_summary(result, command),
            "Failed 1/1",
        )
        self.assertEqual(
            format_docs_check_failure_detail("First check", "broken", command),
            "First check: broken",
        )

    def test_run_docs_check_command_reports_success_with_configured_exit_code(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
            workflow = root / ".github" / "workflows" / "ci.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("name: CI\n", encoding="utf-8")
            command = DocsCheckCommand(
                root=root,
                pipeline=DocsCheckPipeline(
                    checks=(DocsCheck("pass", "Pass check", lambda _: []),),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=7,
                failure_exit_code=9,
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

            result = run_docs_check_command(command)

            self.assertEqual(result.exit_code, 7)
            self.assertEqual(result.report.status, DOCS_CHECK_COMMAND.passed_status)
            self.assertEqual(
                result.stdout_lines,
                (
                    "Docs check passed for 1 Markdown files and 1 GitHub metadata "
                    "files.",
                ),
            )
            self.assertEqual(result.stderr_lines, ())

    def test_run_docs_check_command_reports_failure_with_error_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
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
                failure_exit_code=3,
                report_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                passed_status=DOCS_CHECK_COMMAND.passed_status,
                failed_status=DOCS_CHECK_COMMAND.failed_status,
                preflight_failed_status=(DOCS_CHECK_COMMAND.preflight_failed_status),
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template="SUMMARY: {failed_check_count}/{check_count}",
                failure_detail_template="ERROR[{check_label}]: {error}",
            )

            result = run_docs_check_command(command)

            self.assertEqual(result.exit_code, 3)
            self.assertEqual(result.report.status, DOCS_CHECK_COMMAND.failed_status)
            self.assertEqual(result.stdout_lines, ())
            self.assertEqual(
                result.stderr_lines,
                (
                    "SUMMARY: 1/1",
                    "ERROR[Failure check]: pipeline drift",
                ),
            )

    def test_run_docs_check_command_reports_preflight_errors_with_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_root = Path(tmpdir) / "missing"
            command = DocsCheckCommand(
                root=missing_root,
                pipeline=DocsCheckPipeline(
                    checks=(DocsCheck("check", "Check label", lambda _: []),),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=2,
                failure_exit_code=4,
                report_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
                passed_status=DOCS_CHECK_COMMAND.passed_status,
                failed_status=DOCS_CHECK_COMMAND.failed_status,
                preflight_failed_status=(DOCS_CHECK_COMMAND.preflight_failed_status),
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    "PREFLIGHT: {error_count} problems"
                ),
                failure_summary_template=(DOCS_CHECK_COMMAND.failure_summary_template),
                failure_detail_template="{check_label} -> {error}",
            )

            result = run_docs_check_command(command)

            self.assertEqual(result.exit_code, 4)
            self.assertEqual(
                result.report.status,
                DOCS_CHECK_COMMAND.preflight_failed_status,
            )
            self.assertEqual(result.stdout_lines, ())
            self.assertEqual(
                result.stderr_lines,
                (
                    "PREFLIGHT: 1 problems",
                    f"Command config -> docs check command: root does not exist: "
                    f"{missing_root}",
                ),
            )

    def test_docs_check_report_payload_includes_counts_and_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
            workflow = root / ".github" / "workflows" / "ci.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("name: CI\n", encoding="utf-8")
            pipeline = DocsCheckPipeline(
                checks=(
                    DocsCheck("pass", "Pass check", lambda _: []),
                    DocsCheck("fail", "Failure check", lambda _: ["broken"]),
                ),
                success_message_template=DOCS_CHECK_PIPELINE.success_message_template,
            )
            context = build_docs_check_context(root)
            command = DocsCheckCommand(
                root=root,
                pipeline=pipeline,
                success_exit_code=0,
                failure_exit_code=5,
                report_schema_version="report-v1",
                passed_status="passed",
                failed_status="failed",
                preflight_failed_status="preflight_failed",
                not_run_status="not_run",
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=DOCS_CHECK_COMMAND.failure_summary_template,
                failure_detail_template=DOCS_CHECK_COMMAND.failure_detail_template,
            )
            pipeline_result = run_docs_check_pipeline(context, pipeline)
            result = run_docs_check_command(command)

            self.assertEqual(
                pipeline_result.failed_runs,
                (pipeline_result.check_runs[1],),
            )
            self.assertEqual(
                docs_check_report_to_payload(result.report),
                {
                    "schema_version": "report-v1",
                    "status": "failed",
                    "exit_code": 5,
                    "root": str(root.resolve()),
                    "counts": {
                        "markdown_files": 1,
                        "github_metadata_files": 1,
                        "checks": 2,
                        "failed_checks": 1,
                    },
                    "preflight_errors": [],
                    "preflight_findings": [],
                    "checks": [
                        {
                            "name": "pass",
                            "check_id": "pass",
                            "report_label": "Pass check",
                            "status": "passed",
                            "error_count": 0,
                            "errors": [],
                            "findings": [],
                        },
                        {
                            "name": "fail",
                            "check_id": "fail",
                            "report_label": "Failure check",
                            "status": "failed",
                            "error_count": 1,
                            "errors": ["broken"],
                            "findings": [
                                {
                                    "message": "broken",
                                    "severity": "error",
                                    "path": None,
                                    "line": None,
                                    "end_line": None,
                                }
                            ],
                        },
                    ],
                },
            )

    def test_docs_check_report_from_payload_round_trips_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
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
                preflight_failed_status=DOCS_CHECK_COMMAND.preflight_failed_status,
                not_run_status=DOCS_CHECK_COMMAND.not_run_status,
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=DOCS_CHECK_COMMAND.failure_summary_template,
                failure_detail_template=DOCS_CHECK_COMMAND.failure_detail_template,
            )

            result = run_docs_check_command(command)

            self.assertEqual(
                docs_check_report_from_payload(
                    docs_check_report_to_payload(result.report)
                ),
                result.report,
            )

    def test_docs_check_finding_from_legacy_error_extracts_path_and_line(self) -> None:
        self.assertEqual(
            docs_check_finding_from_legacy_error(
                "docs/guide.md:12-14: missing anchor '#overview'"
            ),
            DocsCheckFinding(
                message="missing anchor '#overview'",
                path="docs/guide.md",
                line=12,
                end_line=14,
            ),
        )
        self.assertEqual(
            docs_check_finding_from_legacy_error(
                "issue linkage contract 'foo' missing field 'bar' from "
                ".github/ISSUE_TEMPLATE/proposal.yml"
            ),
            DocsCheckFinding(
                message=(
                    "issue linkage contract 'foo' missing field 'bar' from "
                    ".github/ISSUE_TEMPLATE/proposal.yml"
                ),
                path=".github/ISSUE_TEMPLATE/proposal.yml",
            ),
        )

    def test_docs_check_report_from_payload_rejects_mismatched_error_count(
        self,
    ) -> None:
        payload = {
            "schema_version": DOCS_CHECK_COMMAND.report_schema_version,
            "status": DOCS_CHECK_COMMAND.failed_status,
            "exit_code": 1,
            "root": "/tmp/example",
            "counts": {
                "markdown_files": 1,
                "github_metadata_files": 0,
                "checks": 1,
                "failed_checks": 1,
            },
            "preflight_errors": [],
            "preflight_findings": [],
            "checks": [
                {
                    "name": "broken",
                    "check_id": "broken",
                    "report_label": "Broken check",
                    "status": DOCS_CHECK_COMMAND.failed_status,
                    "error_count": 2,
                    "errors": ["drifted"],
                    "findings": [
                        {
                            "message": "drifted",
                            "severity": "error",
                            "path": None,
                            "line": None,
                            "end_line": None,
                        }
                    ],
                }
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            "error_count does not match errors length",
        ):
            docs_check_report_from_payload(payload)

    def test_docs_check_report_from_payload_rejects_invalid_check_id(
        self,
    ) -> None:
        payload = {
            "schema_version": DOCS_CHECK_COMMAND.report_schema_version,
            "status": DOCS_CHECK_COMMAND.passed_status,
            "exit_code": 0,
            "root": "/tmp/example",
            "counts": {
                "markdown_files": 1,
                "github_metadata_files": 0,
                "checks": 1,
                "failed_checks": 0,
            },
            "preflight_errors": [],
            "preflight_findings": [],
            "checks": [
                {
                    "name": "broken",
                    "check_id": "Bad-ID",
                    "report_label": "Broken check",
                    "status": DOCS_CHECK_COMMAND.passed_status,
                    "error_count": 0,
                    "errors": [],
                    "findings": [],
                }
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            "must use snake_case check id format",
        ):
            docs_check_report_from_payload(payload)

    def test_format_docs_check_json_report_renders_machine_readable_payload(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
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
                report_schema_version="report-v1",
                passed_status="passed",
                failed_status="failed",
                preflight_failed_status="preflight_failed",
                not_run_status="not_run",
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=DOCS_CHECK_COMMAND.failure_summary_template,
                failure_detail_template=DOCS_CHECK_COMMAND.failure_detail_template,
            )

            result = run_docs_check_command(command)

            self.assertEqual(
                json.loads(format_docs_check_json_report(result)),
                {
                    "schema_version": "report-v1",
                    "status": "passed",
                    "exit_code": 0,
                    "root": str(root.resolve()),
                    "counts": {
                        "markdown_files": 1,
                        "github_metadata_files": 0,
                        "checks": 1,
                        "failed_checks": 0,
                    },
                    "preflight_errors": [],
                    "preflight_findings": [],
                    "checks": [
                        {
                            "name": "pass",
                            "check_id": "pass",
                            "report_label": "Pass check",
                            "status": "passed",
                            "error_count": 0,
                            "errors": [],
                            "findings": [],
                        }
                    ],
                },
            )

    def test_format_docs_check_markdown_report_renders_summary_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Home\n", encoding="utf-8")
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
                report_schema_version="report-v1",
                passed_status="passed",
                failed_status="failed",
                preflight_failed_status="preflight_failed",
                not_run_status="not_run",
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=DOCS_CHECK_COMMAND.failure_summary_template,
                failure_detail_template=DOCS_CHECK_COMMAND.failure_detail_template,
            )

            result = run_docs_check_command(command)
            report = format_docs_check_markdown_report(result)

            self.assertIn("## Docs Check", report)
            self.assertIn("- Status: `passed`", report)
            self.assertIn("| Pass check | `passed` | 0 |", report)
            self.assertNotIn("### Failed Check Details", report)

    def test_format_docs_check_markdown_report_includes_preflight_and_failures(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_root = Path(tmpdir) / "missing"
            command = DocsCheckCommand(
                root=missing_root,
                pipeline=DocsCheckPipeline(
                    checks=(DocsCheck("check", "Check label", lambda _: []),),
                    success_message_template=(
                        DOCS_CHECK_PIPELINE.success_message_template
                    ),
                ),
                success_exit_code=0,
                failure_exit_code=1,
                report_schema_version="report-v1",
                passed_status="passed",
                failed_status="failed",
                preflight_failed_status="preflight_failed",
                not_run_status="not_run",
                preflight_failure_summary_template=(
                    DOCS_CHECK_COMMAND.preflight_failure_summary_template
                ),
                failure_summary_template=DOCS_CHECK_COMMAND.failure_summary_template,
                failure_detail_template=DOCS_CHECK_COMMAND.failure_detail_template,
            )

            result = run_docs_check_command(command)
            report = format_docs_check_markdown_report(result)

            self.assertIn("- Status: `preflight_failed`", report)
            self.assertIn("### Preflight Errors", report)
            self.assertIn("docs check command: root does not exist", report)
            self.assertIn("| Check label | `not_run` | 0 |", report)

    def test_format_docs_check_markdown_report_uses_line_ranges_when_present(
        self,
    ) -> None:
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
                    name="registry",
                    report_label="Maintainer doc registry",
                    status=DOCS_CHECK_COMMAND.failed_status,
                    findings=(
                        DocsCheckFinding(
                            message="registry drift",
                            path="README.md",
                            line=3,
                            end_line=7,
                        ),
                    ),
                ),
            ),
        )

        self.assertIn(
            "- `README.md:3-7` registry drift",
            format_docs_check_markdown_report_from_report(report),
        )
        self.assertIn(
            "#### Maintainer doc registry (`registry`)",
            format_docs_check_markdown_report_from_report(report),
        )


if __name__ == "__main__":
    unittest.main()
