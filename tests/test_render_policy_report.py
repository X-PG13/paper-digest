from __future__ import annotations

import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from tools.check_policies import POLICY_REPORT_SCHEMA_VERSION
from tools.render_policy_report import (
    PolicyContractReport,
    PolicyReport,
    PolicyReportError,
    format_policy_github_annotations,
    format_policy_markdown_report,
    load_policy_report,
    main,
)


class RenderPolicyReportTests(unittest.TestCase):
    def test_format_policy_markdown_report_summarizes_passed_contracts(self) -> None:
        report = PolicyReport(
            schema_version=POLICY_REPORT_SCHEMA_VERSION,
            status="passed",
            contracts=(
                PolicyContractReport(
                    name="issue form policy",
                    status="passed",
                    errors=(),
                ),
            ),
            errors=(),
        )

        rendered = format_policy_markdown_report(report)

        self.assertIn("## Policy Check", rendered)
        self.assertIn("- Status: `passed`", rendered)
        self.assertIn("| issue form policy | `passed` | 0 |", rendered)
        self.assertNotIn("### Failed Contracts", rendered)

    def test_format_policy_markdown_report_groups_failed_contracts(self) -> None:
        report = PolicyReport(
            schema_version=POLICY_REPORT_SCHEMA_VERSION,
            status="failed",
            contracts=(
                PolicyContractReport(
                    name="issue form policy",
                    status="passed",
                    errors=(),
                ),
                PolicyContractReport(
                    name="routing label policy",
                    status="failed",
                    errors=("missing label", "bad label"),
                ),
            ),
            errors=(
                PolicyReportError(
                    contract="routing label policy",
                    message="missing label",
                ),
                PolicyReportError(
                    contract="routing label policy",
                    message="bad label",
                ),
            ),
        )

        rendered = format_policy_markdown_report(report)

        self.assertIn("- Status: `failed`", rendered)
        self.assertIn("| routing label policy | `failed` | 2 |", rendered)
        self.assertIn("### Failed Contracts", rendered)
        self.assertIn("#### routing label policy", rendered)
        self.assertIn("- missing label", rendered)
        self.assertIn("- bad label", rendered)

    def test_format_policy_github_annotations_escapes_values(self) -> None:
        report = PolicyReport(
            schema_version=POLICY_REPORT_SCHEMA_VERSION,
            status="failed",
            contracts=(
                PolicyContractReport(
                    name="routing, label: policy",
                    status="failed",
                    errors=("drifted 100%\nnext line",),
                ),
            ),
            errors=(
                PolicyReportError(
                    contract="routing, label: policy",
                    message="drifted 100%\nnext line",
                ),
            ),
        )

        self.assertEqual(
            format_policy_github_annotations(report),
            (
                "::error title=Policy check%3A routing%2C label%3A policy::"
                "drifted 100%25%0Anext line",
            ),
        )

    def test_load_policy_report_round_trips_payload(self) -> None:
        payload = {
            "schema_version": POLICY_REPORT_SCHEMA_VERSION,
            "status": "passed",
            "contracts": [
                {
                    "name": "issue form policy",
                    "status": "passed",
                    "errors": [],
                },
            ],
            "errors": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "policy-check-report.json"
            report_file.write_text(json.dumps(payload), encoding="utf-8")

            self.assertEqual(
                load_policy_report(report_file),
                PolicyReport(
                    schema_version=POLICY_REPORT_SCHEMA_VERSION,
                    status="passed",
                    contracts=(
                        PolicyContractReport(
                            name="issue form policy",
                            status="passed",
                            errors=(),
                        ),
                    ),
                    errors=(),
                ),
            )

    def test_load_policy_report_rejects_mismatched_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "policy-check-report.json"
            report_file.write_text(
                json.dumps(
                    {
                        "schema_version": POLICY_REPORT_SCHEMA_VERSION,
                        "status": "failed",
                        "contracts": [
                            {
                                "name": "issue form policy",
                                "status": "failed",
                                "errors": ["missing"],
                            },
                        ],
                        "errors": [
                            {
                                "contract": "issue form policy",
                                "message": "different",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "policy report errors do not match contract errors",
            ):
                load_policy_report(report_file)

    def test_main_renders_markdown_to_stdout_and_file(self) -> None:
        payload = {
            "schema_version": POLICY_REPORT_SCHEMA_VERSION,
            "status": "passed",
            "contracts": [
                {
                    "name": "issue form policy",
                    "status": "passed",
                    "errors": [],
                },
            ],
            "errors": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "policy-check-report.json"
            output_file = Path(tmpdir) / "policy-check-summary.md"
            report_file.write_text(json.dumps(payload), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()

            exit_code = main(
                report_file=report_file,
                output_format="markdown",
                output_file=output_file,
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("## Policy Check", output_file.read_text(encoding="utf-8"))

    def test_main_reports_invalid_report_to_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "policy-check-report.json"
            report_file.write_text("not json", encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()

            exit_code = main(report_file=report_file, stdout=stdout, stderr=stderr)

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("policy report render failed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
