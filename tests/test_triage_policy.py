from __future__ import annotations

import unittest

from tests.policy_assertions import assert_file_contains_snippets
from tools.triage_policy import (
    DOCS_FOLLOW_UP_POLICY_LINE,
    DOCUMENTATION_LABEL_FOLLOW_UP_RULE,
    TRIAGE_REPLY_POLICY_SPECS,
    required_issue_triage_snippets,
    required_label_taxonomy_snippets,
    validate_triage_reply_policy,
)


class TriagePolicyTests(unittest.TestCase):
    def test_triage_reply_policy_is_self_consistent(self) -> None:
        validate_triage_reply_policy()
        self.assertEqual(len(TRIAGE_REPLY_POLICY_SPECS), 7)
        self.assertIn("docs gap", DOCS_FOLLOW_UP_POLICY_LINE)
        self.assertIn("closed or redirected report", DOCUMENTATION_LABEL_FOLLOW_UP_RULE)

    def test_issue_triage_doc_contains_required_contract_snippets(self) -> None:
        assert_file_contains_snippets(
            self,
            "docs/issue-triage.md",
            required_issue_triage_snippets(),
        )

    def test_label_taxonomy_doc_contains_required_contract_snippets(self) -> None:
        assert_file_contains_snippets(
            self,
            "docs/label-taxonomy.md",
            required_label_taxonomy_snippets(),
        )


if __name__ == "__main__":
    unittest.main()
