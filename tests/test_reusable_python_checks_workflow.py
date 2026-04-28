from __future__ import annotations

import unittest

from tests.workflow_assertions import (
    extract_indented_block,
    extract_step_block,
    load_workflow_lines,
)

WORKFLOW_PATH = ".github/workflows/reusable-python-checks.yml"


class ReusablePythonChecksWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = load_workflow_lines(WORKFLOW_PATH)

    def test_docs_check_report_upload_input_defaults_to_enabled(self) -> None:
        block = extract_indented_block(
            self.lines,
            "      upload_docs_check_report:",
        )

        self.assertIn("        required: false", block)
        self.assertIn("        type: boolean", block)
        self.assertIn("        default: true", block)

    def test_docs_check_report_json_is_generated(self) -> None:
        block = extract_step_block(self.lines, "Generate docs-check report")

        self.assertIn(
            "        if: always() && inputs.upload_docs_check_report",
            block,
        )
        self.assertIn("        continue-on-error: true", block)
        self.assertIn(
            "        run: python tools/check_docs.py --json-report-file "
            "reports/docs-check-report.json",
            block,
        )

    def test_docs_check_markdown_summary_is_rendered_and_published(self) -> None:
        render_block = extract_step_block(self.lines, "Render docs-check summary")
        publish_block = extract_step_block(self.lines, "Publish docs-check summary")

        self.assertIn(
            "hashFiles('reports/docs-check-report.json') != ''",
            render_block,
        )
        self.assertIn(
            "        run: python tools/render_docs_report.py "
            "reports/docs-check-report.json --format markdown "
            "--output reports/docs-check-summary.md",
            render_block,
        )
        self.assertIn(
            "hashFiles('reports/docs-check-summary.md') != ''",
            publish_block,
        )
        self.assertIn(
            "        run: cat reports/docs-check-summary.md >> "
            '"$GITHUB_STEP_SUMMARY"',
            publish_block,
        )

    def test_docs_check_pr_comment_preview_is_rendered(self) -> None:
        block = extract_step_block(self.lines, "Render docs-check PR comment")

        self.assertIn("hashFiles('reports/docs-check-report.json') != ''", block)
        self.assertIn(
            "        run: python tools/render_docs_report.py "
            "reports/docs-check-report.json --format pr-comment "
            "--output reports/docs-check-pr-comment.md",
            block,
        )

    def test_docs_check_annotations_are_rendered_from_json_report(self) -> None:
        block = extract_step_block(self.lines, "Publish docs-check annotations")

        self.assertIn("hashFiles('reports/docs-check-report.json') != ''", block)
        self.assertIn(
            "        run: python tools/render_docs_report.py "
            "reports/docs-check-report.json --format github-annotations",
            block,
        )

    def test_docs_check_artifact_contains_json_markdown_and_pr_comment(self) -> None:
        block = extract_step_block(self.lines, "Upload docs-check reports")

        self.assertIn(
            "        if: always() && inputs.upload_docs_check_report",
            block,
        )
        self.assertIn("        uses: actions/upload-artifact@v7", block)
        self.assertIn("          name: docs-check-report", block)
        self.assertIn("            reports/docs-check-report.json", block)
        self.assertIn("            reports/docs-check-summary.md", block)
        self.assertIn("            reports/docs-check-pr-comment.md", block)
        self.assertIn("          if-no-files-found: error", block)

    def test_policy_check_report_upload_input_defaults_to_enabled(self) -> None:
        block = extract_indented_block(
            self.lines,
            "      upload_policy_check_report:",
        )

        self.assertIn("        required: false", block)
        self.assertIn("        type: boolean", block)
        self.assertIn("        default: true", block)

    def test_policy_check_report_json_is_generated(self) -> None:
        block = extract_step_block(self.lines, "Generate policy-check report")

        self.assertIn(
            "        if: always() && inputs.upload_policy_check_report",
            block,
        )
        self.assertIn("        continue-on-error: true", block)
        self.assertIn(
            "        run: python tools/check_policies.py --json-report-file "
            "reports/policy-check-report.json",
            block,
        )

    def test_policy_check_markdown_summary_is_rendered_and_published(self) -> None:
        render_block = extract_step_block(self.lines, "Render policy-check summary")
        publish_block = extract_step_block(self.lines, "Publish policy-check summary")

        self.assertIn(
            "hashFiles('reports/policy-check-report.json') != ''",
            render_block,
        )
        self.assertIn(
            "        run: python tools/render_policy_report.py "
            "reports/policy-check-report.json --format markdown "
            "--output reports/policy-check-summary.md",
            render_block,
        )
        self.assertIn(
            "hashFiles('reports/policy-check-summary.md') != ''",
            publish_block,
        )
        self.assertIn(
            "        run: cat reports/policy-check-summary.md >> "
            '"$GITHUB_STEP_SUMMARY"',
            publish_block,
        )

    def test_policy_check_annotations_are_rendered_from_json_report(self) -> None:
        block = extract_step_block(self.lines, "Publish policy-check annotations")

        self.assertIn("hashFiles('reports/policy-check-report.json') != ''", block)
        self.assertIn(
            "        run: python tools/render_policy_report.py "
            "reports/policy-check-report.json --format github-annotations",
            block,
        )

    def test_policy_check_artifact_contains_json_and_markdown_reports(self) -> None:
        block = extract_step_block(self.lines, "Upload policy-check reports")

        self.assertIn(
            "        if: always() && inputs.upload_policy_check_report",
            block,
        )
        self.assertIn("        uses: actions/upload-artifact@v7", block)
        self.assertIn("          name: policy-check-report", block)
        self.assertIn("            reports/policy-check-report.json", block)
        self.assertIn("            reports/policy-check-summary.md", block)
        self.assertIn("          if-no-files-found: error", block)


if __name__ == "__main__":
    unittest.main()
