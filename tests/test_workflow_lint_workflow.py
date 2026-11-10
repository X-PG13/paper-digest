from __future__ import annotations

import unittest

from tests.workflow_assertions import extract_indented_block, load_workflow_lines


class WorkflowLintWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = load_workflow_lines(".github/workflows/workflow-lint.yml")

    def test_workflow_lint_runs_on_every_pull_request_and_default_branch_push(
        self,
    ) -> None:
        block = extract_indented_block(self.lines, "on:")

        self.assertIn("  push:", block)
        self.assertIn('    branches: ["main", "master"]', block)
        self.assertIn("  pull_request:", block)
        self.assertIn("  workflow_dispatch:", block)
        self.assertNotIn("paths:", block)
        self.assertNotIn("paths-ignore:", block)

    def test_actionlint_job_runs_pinned_workflow_lint(self) -> None:
        job = extract_indented_block(self.lines, "  actionlint:")
        preamble, _, steps = job.partition("\n    steps:")

        self.assertIn("    runs-on: ubuntu-latest", preamble)
        self.assertNotIn("if:", preamble)
        self.assertNotIn("continue-on-error:", job)
        self.assertIn("        run: make workflow-tools", steps)
        self.assertIn("        run: make workflow-check", steps)
