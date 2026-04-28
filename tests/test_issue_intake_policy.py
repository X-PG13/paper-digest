from __future__ import annotations

import unittest

from tests.policy_assertions import (
    assert_file_contains_snippets,
    assert_issue_form_fields,
    assert_issue_form_metadata,
)
from tools.issue_form_policy import (
    BUG_REPORT_FORM_NAME,
    BUG_REPORT_FORM_PATH,
    BUG_REPORT_FORM_TITLE,
)
from tools.issue_intake_policy import (
    ISSUE_INTAKE_COMMENT_FOOTER,
    ISSUE_INTAKE_COMMENT_HEADER,
    ISSUE_INTAKE_FIELDS,
    ISSUE_INTAKE_SECTIONS,
    get_issue_intake_field,
    get_issue_intake_section,
    required_bug_report_form_fields,
    required_bug_report_form_snippets,
    validate_issue_intake_contract,
)


class IssueIntakePolicyTests(unittest.TestCase):
    def test_issue_intake_contract_is_self_consistent(self) -> None:
        validate_issue_intake_contract()
        self.assertEqual(len(ISSUE_INTAKE_SECTIONS), 3)
        self.assertEqual(len(ISSUE_INTAKE_FIELDS), 3)
        self.assertIn("minimum information", ISSUE_INTAKE_COMMENT_HEADER)
        self.assertIn(
            "automation will clear this reminder",
            ISSUE_INTAKE_COMMENT_FOOTER,
        )

    def test_get_issue_intake_specs_return_expected_labels(self) -> None:
        self.assertEqual(
            get_issue_intake_section("reproduction").label,
            "Reproduction",
        )
        self.assertEqual(
            get_issue_intake_field("project_version").label,
            "Project version or commit",
        )
        with self.assertRaisesRegex(KeyError, "unknown issue intake section key"):
            get_issue_intake_section("missing")
        with self.assertRaisesRegex(KeyError, "unknown issue intake field key"):
            get_issue_intake_field("missing")

    def test_bug_report_form_matches_required_metadata_and_fields(self) -> None:
        assert_issue_form_metadata(
            self,
            BUG_REPORT_FORM_PATH,
            name=BUG_REPORT_FORM_NAME,
            title=BUG_REPORT_FORM_TITLE,
        )
        assert_issue_form_fields(
            self,
            BUG_REPORT_FORM_PATH,
            required_bug_report_form_fields(),
        )

    def test_bug_report_form_contains_required_contract_snippets(self) -> None:
        assert_file_contains_snippets(
            self,
            BUG_REPORT_FORM_PATH,
            required_bug_report_form_snippets(),
            normalize=False,
        )


if __name__ == "__main__":
    unittest.main()
