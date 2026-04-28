from __future__ import annotations

import unittest

from tests.policy_assertions import assert_file_contains_snippets
from tools.pr_policy import (
    PR_HYGIENE_COMMENT_FOOTER,
    PR_HYGIENE_COMMENT_HEADER,
    PR_HYGIENE_REMINDERS,
    get_pr_hygiene_reminder,
    required_pull_request_template_lines,
    validate_pr_hygiene_contract,
)


class PrPolicyTests(unittest.TestCase):
    def test_pr_hygiene_contract_is_self_consistent(self) -> None:
        validate_pr_hygiene_contract()
        self.assertEqual(len(PR_HYGIENE_REMINDERS), 3)
        self.assertTrue(PR_HYGIENE_COMMENT_HEADER.endswith("before merge:"))
        self.assertIn("`No ... needed.`", PR_HYGIENE_COMMENT_FOOTER)

    def test_get_pr_hygiene_reminder_returns_expected_specs(self) -> None:
        self.assertEqual(
            get_pr_hygiene_reminder("linked_issue").checkbox_label,
            "No linked issue needed.",
        )
        with self.assertRaisesRegex(KeyError, "unknown PR hygiene reminder key"):
            get_pr_hygiene_reminder("missing")

    def test_pull_request_template_contains_required_contract_lines(self) -> None:
        assert_file_contains_snippets(
            self,
            ".github/pull_request_template.md",
            required_pull_request_template_lines(),
            normalize=False,
        )


if __name__ == "__main__":
    unittest.main()
