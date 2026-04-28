from __future__ import annotations

import unittest

from tools.workflow_path_policy import (
    is_changelog_path,
    is_governance_path,
    is_maintenance_path,
    is_public_doc_path,
    is_runtime_or_ops_path,
    is_test_path,
)


class WorkflowPathPolicyTests(unittest.TestCase):
    def test_public_doc_path_matches_docs_templates_and_doc_roots(self) -> None:
        self.assertTrue(is_public_doc_path("README.md"))
        self.assertTrue(is_public_doc_path("docs/guide.md"))
        self.assertTrue(is_public_doc_path(".github/ISSUE_TEMPLATE/bug_report.yml"))
        self.assertFalse(is_public_doc_path("paper_digest/service.py"))

    def test_changelog_and_test_path_helpers_match_expected_roots(self) -> None:
        self.assertTrue(is_changelog_path("CHANGELOG.md"))
        self.assertFalse(is_changelog_path("docs/CHANGELOG.md"))
        self.assertTrue(is_test_path("tests/test_cli.py"))
        self.assertFalse(is_test_path("paper_digest/tests.py"))

    def test_runtime_or_ops_path_matches_runtime_workflows_and_ops_roots(self) -> None:
        self.assertTrue(is_runtime_or_ops_path("paper_digest/service.py"))
        self.assertTrue(is_runtime_or_ops_path(".github/workflows/ci.yml"))
        self.assertTrue(is_runtime_or_ops_path("Makefile"))
        self.assertFalse(is_runtime_or_ops_path("docs/guide.md"))

    def test_maintenance_and_governance_path_helpers_match_policy_sets(self) -> None:
        self.assertTrue(is_maintenance_path(".github/workflows/ci.yml"))
        self.assertTrue(is_maintenance_path("pyproject.toml"))
        self.assertFalse(is_maintenance_path("README.md"))
        self.assertTrue(is_governance_path("GOVERNANCE.md"))
        self.assertTrue(is_governance_path("docs/adr/0001-test.md"))
        self.assertFalse(is_governance_path("docs/guide.md"))


if __name__ == "__main__":
    unittest.main()
