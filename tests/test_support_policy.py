from __future__ import annotations

import unittest

from tests.policy_assertions import (
    assert_file_contains_snippets,
    assert_issue_form_checkbox_options,
    assert_issue_form_fields,
    assert_issue_form_metadata,
    assert_issue_template_contact_links,
)
from tools.issue_form_policy import (
    SUPPORT_REQUEST_FORM_NAME,
    SUPPORT_REQUEST_FORM_PATH,
    SUPPORT_REQUEST_FORM_TITLE,
)
from tools.support_policy import (
    SUPPORT_CONTACT_LINK_NAME,
    SUPPORT_CONTACT_LINK_TARGET,
    SUPPORT_PRECHECK_DOCS,
    SUPPORT_PRECHECK_MISSING_MESSAGE,
    SUPPORT_REQUEST_FIELDS,
    SUPPORT_REQUEST_FORM_INTRO_LINES,
    SUPPORT_TRIAGE_COMMENT_FOOTER,
    SUPPORT_TRIAGE_COMMENT_HEADER,
    SUPPORT_TRIAGE_MARKER,
    required_issue_template_contact_links,
    required_support_md_snippets,
    required_support_request_form_fields,
    required_support_request_form_snippets,
    required_support_request_precheck_options,
    validate_support_contract,
)


class SupportPolicyTests(unittest.TestCase):
    def test_support_contract_is_self_consistent(self) -> None:
        validate_support_contract()
        self.assertEqual(len(SUPPORT_PRECHECK_DOCS), 5)
        self.assertEqual(len(SUPPORT_REQUEST_FIELDS), 7)
        self.assertEqual(SUPPORT_CONTACT_LINK_NAME, "Support Expectations")
        self.assertEqual(SUPPORT_CONTACT_LINK_TARGET, "SUPPORT.md")
        self.assertEqual(
            SUPPORT_PRECHECK_MISSING_MESSAGE,
            "confirmation that the pre-read support docs were checked",
        )
        self.assertIn("minimum context", SUPPORT_TRIAGE_COMMENT_HEADER)
        self.assertIn(
            "automation will clear this reminder",
            SUPPORT_TRIAGE_COMMENT_FOOTER,
        )
        self.assertEqual(len(SUPPORT_REQUEST_FORM_INTRO_LINES), 2)
        self.assertEqual(
            SUPPORT_TRIAGE_MARKER,
            "<!-- community-triage-support-needs-info -->",
        )

    def test_support_request_form_matches_required_metadata_and_fields(self) -> None:
        assert_issue_form_metadata(
            self,
            SUPPORT_REQUEST_FORM_PATH,
            name=SUPPORT_REQUEST_FORM_NAME,
            title=SUPPORT_REQUEST_FORM_TITLE,
        )
        assert_issue_form_fields(
            self,
            SUPPORT_REQUEST_FORM_PATH,
            required_support_request_form_fields(),
        )
        assert_issue_form_checkbox_options(
            self,
            SUPPORT_REQUEST_FORM_PATH,
            "docs_checked",
            required_support_request_precheck_options(),
        )

    def test_support_request_form_contains_required_contract_snippets(self) -> None:
        assert_file_contains_snippets(
            self,
            SUPPORT_REQUEST_FORM_PATH,
            required_support_request_form_snippets(),
        )

    def test_support_md_contains_required_contract_snippets(self) -> None:
        assert_file_contains_snippets(
            self,
            "SUPPORT.md",
            required_support_md_snippets(),
        )

    def test_issue_template_config_routes_support_contact_link(self) -> None:
        assert_issue_template_contact_links(
            self,
            required_issue_template_contact_links(),
        )


if __name__ == "__main__":
    unittest.main()
