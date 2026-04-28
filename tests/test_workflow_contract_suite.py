from __future__ import annotations

import unittest

from tests.workflow_assertions import (
    extract_indented_block,
    extract_step_block,
    load_workflow_lines,
)


class PrHygieneWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = load_workflow_lines(".github/workflows/pr-hygiene.yml")

    def test_pr_hygiene_runs_on_pull_request_target_lifecycle_events(self) -> None:
        block = extract_indented_block(self.lines, "on:")

        self.assertIn("  pull_request_target:", block)
        self.assertIn("      - opened", block)
        self.assertIn("      - edited", block)
        self.assertIn("      - reopened", block)
        self.assertIn("      - synchronize", block)
        self.assertIn("      - ready_for_review", block)

    def test_pr_hygiene_has_minimal_comment_permissions(self) -> None:
        block = extract_indented_block(self.lines, "permissions:")

        self.assertIn("  contents: read", block)
        self.assertIn("  issues: write", block)
        self.assertIn("  pull-requests: write", block)

    def test_pr_hygiene_uses_repo_local_policy_evaluator(self) -> None:
        block = extract_step_block(
            self.lines,
            "Evaluate PR docs, changelog, and context hygiene",
        )

        self.assertIn("        id: reminder", block)
        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}", block)
        self.assertIn(
            "          PR_BODY: ${{ github.event.pull_request.body || '' }}",
            block,
        )
        self.assertIn("          python tools/pr_hygiene.py \\", block)
        self.assertIn('            --repo "${{ github.repository }}" \\', block)
        self.assertIn(
            '            --pull-number "${{ github.event.pull_request.number }}" \\',
            block,
        )
        self.assertIn("            --body-env PR_BODY", block)

    def test_pr_hygiene_syncs_or_deletes_marker_comment(self) -> None:
        block = extract_step_block(self.lines, "Sync PR hygiene comment")

        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}", block)
        self.assertIn(
            "          COMMENT_BODY: ${{ steps.reminder.outputs.comment-body }}",
            block,
        )
        self.assertIn(
            '          if [ "${{ steps.reminder.outputs.mode }}" = "delete" ]; then',
            block,
        )
        self.assertIn("            python tools/sync_marker_comment.py \\", block)
        self.assertIn('              --repo "${{ github.repository }}" \\', block)
        self.assertIn(
            '              --issue-number "${{ github.event.pull_request.number }}" \\',
            block,
        )
        self.assertIn(
            '              --marker "${{ steps.reminder.outputs.marker }}" \\',
            block,
        )
        self.assertIn("              --delete", block)
        self.assertIn("              --body-env COMMENT_BODY", block)


class CommunityTriageWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = load_workflow_lines(".github/workflows/community-triage.yml")

    def test_community_triage_runs_on_issue_and_pr_lifecycle_events(self) -> None:
        block = extract_indented_block(self.lines, "on:")

        self.assertIn("  issues:", block)
        self.assertIn("      - labeled", block)
        self.assertIn("      - unlabeled", block)
        self.assertIn("  pull_request_target:", block)
        self.assertIn("      - synchronize", block)
        self.assertIn("      - ready_for_review", block)

    def test_community_triage_has_minimal_label_and_comment_permissions(self) -> None:
        block = extract_indented_block(self.lines, "permissions:")

        self.assertIn("  contents: read", block)
        self.assertIn("  issues: write", block)
        self.assertIn("  pull-requests: write", block)

    def test_issue_intake_job_uses_repo_local_triage_evaluator(self) -> None:
        job_block = extract_indented_block(self.lines, "  issue-intake:")
        step_block = extract_step_block(self.lines, "Evaluate bug report completeness")

        self.assertIn("    if: github.event_name == 'issues'", job_block)
        self.assertIn("        id: intake", step_block)
        self.assertIn(
            "          ISSUE_BODY: ${{ github.event.issue.body || '' }}",
            step_block,
        )
        self.assertIn(
            "          ISSUE_LABELS_JSON: ${{ toJson(github.event.issue.labels) }}",
            step_block,
        )
        self.assertIn("          python tools/community_triage.py \\", step_block)
        self.assertIn("            --body-env ISSUE_BODY \\", step_block)
        self.assertIn("            --labels-json-env ISSUE_LABELS_JSON", step_block)

    def test_issue_intake_syncs_needs_info_label_through_helper(self) -> None:
        block = extract_step_block(self.lines, "Sync needs-info label")

        self.assertIn("steps.intake.outputs.needs-info-action != 'none'", block)
        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}", block)
        self.assertIn(
            '          if [ "${{ steps.intake.outputs.needs-info-action }}" = '
            '"add" ]; then',
            block,
        )
        self.assertIn("            python tools/sync_issue_labels.py \\", block)
        self.assertIn('              --repo "${{ github.repository }}" \\', block)
        self.assertIn(
            '              --issue-number "${{ github.event.issue.number }}" \\',
            block,
        )
        self.assertIn("              --ensure needs-info", block)
        self.assertIn("              --remove needs-info", block)

    def test_issue_intake_syncs_or_deletes_marker_comment(self) -> None:
        block = extract_step_block(self.lines, "Sync issue-intake comment")

        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}", block)
        self.assertIn(
            "          COMMENT_BODY: ${{ steps.intake.outputs.comment-body }}",
            block,
        )
        self.assertIn(
            '          if [ "${{ steps.intake.outputs.mode }}" = "delete" ]; then',
            block,
        )
        self.assertIn("            python tools/sync_marker_comment.py \\", block)
        self.assertIn('              --repo "${{ github.repository }}" \\', block)
        self.assertIn(
            '              --issue-number "${{ github.event.issue.number }}" \\',
            block,
        )
        self.assertIn(
            '              --marker "${{ steps.intake.outputs.marker }}" \\',
            block,
        )
        self.assertIn("              --delete", block)
        self.assertIn("              --body-env COMMENT_BODY", block)

    def test_pr_label_job_uses_repo_local_label_router(self) -> None:
        job_block = extract_indented_block(self.lines, "  pr-labels:")
        step_block = extract_step_block(self.lines, "Apply path-based labels")

        self.assertIn("    if: github.event_name == 'pull_request_target'", job_block)
        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}", step_block)
        self.assertIn("          python tools/community_pr_labels.py \\", step_block)
        self.assertIn('            --repo "${{ github.repository }}" \\', step_block)
        self.assertIn(
            '            --pull-number "${{ github.event.pull_request.number }}" \\',
            step_block,
        )
        self.assertIn('            --actor "${{ github.actor }}"', step_block)


class LabelSyncWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = load_workflow_lines(".github/workflows/label-sync.yml")

    def test_label_sync_runs_only_on_safe_pushes_and_manual_dispatch(self) -> None:
        block = extract_indented_block(self.lines, "on:")

        self.assertIn("  push:", block)
        self.assertIn('    branches: ["main", "master"]', block)
        self.assertIn("      - \".github/labels.json\"", block)
        self.assertIn("      - \".github/workflows/label-sync.yml\"", block)
        self.assertIn("  workflow_dispatch:", block)
        self.assertNotIn("pull_request", block)
        self.assertNotIn("pull_request_target", block)
        self.assertNotIn("issues:", block)

    def test_label_sync_has_minimal_repository_label_permissions(self) -> None:
        block = extract_indented_block(self.lines, "permissions:")

        self.assertIn("  issues: write", block)
        self.assertIn("  contents: read", block)

    def test_label_sync_uses_repo_local_sync_helper_and_labels_registry(self) -> None:
        block = extract_step_block(self.lines, "Sync repository labels")

        self.assertIn("          GITHUB_TOKEN: ${{ github.token }}", block)
        self.assertIn("          python tools/sync_repository_labels.py \\", block)
        self.assertIn('            --repo "${{ github.repository }}" \\', block)
        self.assertIn("            --labels-file .github/labels.json", block)
        self.assertNotIn("actions/github-script", block)


if __name__ == "__main__":
    unittest.main()
