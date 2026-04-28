from __future__ import annotations

import unittest

from tests.workflow_assertions import (
    extract_indented_block,
    extract_step_block,
    load_workflow_lines,
)

WORKFLOW_PATH = ".github/workflows/docs-check-pr-comment.yml"


class DocsCheckPrCommentWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = load_workflow_lines(WORKFLOW_PATH)

    def test_workflow_runs_as_trusted_follow_up_for_ci_pull_requests(self) -> None:
        trigger_block = extract_indented_block(self.lines, "on:")
        job_block = extract_indented_block(self.lines, "  sync-comment:")

        self.assertIn("  workflow_run:", trigger_block)
        self.assertIn('    workflows: ["CI"]', trigger_block)
        self.assertIn("      - completed", trigger_block)
        self.assertIn(
            "    if: github.event.workflow_run.event == 'pull_request' && "
            "github.event.workflow_run.conclusion != 'cancelled' && "
            "github.event.workflow_run.conclusion != 'skipped'",
            job_block,
        )
        self.assertIn("    runs-on: ubuntu-latest", job_block)
        self.assertIn("    timeout-minutes: 10", job_block)

    def test_workflow_has_minimal_permissions_for_comment_sync(self) -> None:
        block = extract_indented_block(self.lines, "permissions:")

        self.assertIn("  actions: read", block)
        self.assertIn("  contents: read", block)
        self.assertIn("  issues: write", block)

    def test_context_step_resolves_pr_and_docs_check_artifact(self) -> None:
        block = extract_step_block(self.lines, "Resolve PR and docs-check artifact")

        self.assertIn("        id: context", block)
        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}", block)
        self.assertIn(
            "          python -m tools.docs_check_pr_comment resolve-context \\",
            block,
        )
        self.assertIn('            --repo "${{ github.repository }}"', block)

    def test_workflow_fails_fast_when_docs_check_artifact_is_missing(self) -> None:
        block = extract_step_block(self.lines, "Fail if docs-check artifact is missing")

        self.assertIn("steps.context.outputs.artifact-found != 'true'", block)
        self.assertIn(
            '          echo "Expected docs-check-report artifact for CI workflow run '
            '${{ steps.context.outputs.workflow-run-id }}." >&2',
            block,
        )
        self.assertIn("          exit 1", block)

    def test_workflow_downloads_docs_check_report_artifact_from_ci_run(self) -> None:
        block = extract_step_block(self.lines, "Download docs-check artifact")

        self.assertIn("        uses: actions/download-artifact@v5", block)
        self.assertIn("          name: docs-check-report", block)
        self.assertIn("          path: reports", block)
        self.assertIn("          repository: ${{ github.repository }}", block)
        self.assertIn(
            "          run-id: ${{ steps.context.outputs.workflow-run-id }}",
            block,
        )
        self.assertIn("          github-token: ${{ github.token }}", block)

    def test_workflow_rerenders_pr_comment_from_trusted_default_branch(self) -> None:
        block = extract_step_block(self.lines, "Render trusted docs-check PR comment")

        self.assertIn(
            "        run: python -m tools.render_docs_report "
            "reports/docs-check-report.json --format pr-comment "
            "--output reports/docs-check-pr-comment.md",
            block,
        )

    def test_workflow_decides_comment_action_from_report_and_comment_files(
        self,
    ) -> None:
        block = extract_step_block(self.lines, "Determine docs-check comment action")

        self.assertIn("        id: comment", block)
        self.assertIn(
            "          python -m tools.docs_check_pr_comment decide-comment \\",
            block,
        )
        self.assertIn(
            "            --report-file reports/docs-check-report.json \\",
            block,
        )
        self.assertIn(
            "            --comment-file reports/docs-check-pr-comment.md",
            block,
        )

    def test_workflow_syncs_or_deletes_marker_comment_through_shared_helper(
        self,
    ) -> None:
        block = extract_step_block(self.lines, "Sync docs-check PR comment")

        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}", block)
        self.assertIn(
            "          COMMENT_BODY: ${{ steps.comment.outputs.comment-body }}",
            block,
        )
        self.assertIn(
            '          if [ "${{ steps.comment.outputs.mode }}" = "delete" ]; then',
            block,
        )
        self.assertIn("            python -m tools.sync_marker_comment \\", block)
        self.assertIn('              --repo "${{ github.repository }}" \\', block)
        self.assertIn(
            '              --issue-number "${{ steps.context.outputs.pr-number }}" \\',
            block,
        )
        self.assertIn(
            '              --marker "${{ steps.comment.outputs.marker }}" \\',
            block,
        )
        self.assertIn("              --delete", block)
        self.assertIn("              --body-env COMMENT_BODY", block)


if __name__ == "__main__":
    unittest.main()
