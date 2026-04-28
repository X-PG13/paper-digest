from __future__ import annotations

import unittest

from tests.policy_assertions import (
    assert_file_contains_snippets,
    assert_files_contain_snippets,
    assert_issue_form_labels,
    assert_label_descriptions,
    assert_release_note_excluded_labels,
    assert_stale_exemptions,
)
from tools.status_label_policy import (
    RELEASE_FOLLOW_UP_LABEL,
    RELEASE_PREP_LABEL,
    STATUS_LABEL_SPECS,
    required_artifact_snippets_by_path,
    required_issue_form_labels_by_path,
    required_issue_triage_snippets,
    required_label_descriptions,
    required_label_taxonomy_snippets,
    required_release_note_excluded_labels,
    validate_status_label_policy,
)


class StatusLabelPolicyTests(unittest.TestCase):
    def test_status_label_policy_is_self_consistent(self) -> None:
        validate_status_label_policy()
        self.assertEqual(len(STATUS_LABEL_SPECS), 6)

    def test_labels_json_contains_required_descriptions(self) -> None:
        assert_label_descriptions(self, required_label_descriptions())

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

    def test_status_label_artifacts_contain_required_contract_snippets(self) -> None:
        assert_files_contain_snippets(
            self,
            required_artifact_snippets_by_path(),
        )

    def test_issue_forms_contain_required_labels(self) -> None:
        assert_issue_form_labels(
            self,
            required_issue_form_labels_by_path(),
        )

    def test_stale_workflow_matches_issue_and_pr_exemptions(self) -> None:
        assert_stale_exemptions(self, STATUS_LABEL_SPECS)

    def test_release_yml_matches_status_label_exclusions(self) -> None:
        assert_release_note_excluded_labels(
            self,
            required_release_note_excluded_labels(),
        )

    def test_release_tracking_labels_are_issue_only_exemptions(self) -> None:
        release_prep = next(
            spec for spec in STATUS_LABEL_SPECS if spec.label == RELEASE_PREP_LABEL
        )
        release_follow_up = next(
            spec
            for spec in STATUS_LABEL_SPECS
            if spec.label == RELEASE_FOLLOW_UP_LABEL
        )
        self.assertTrue(release_prep.stale_exempt_issues)
        self.assertFalse(release_prep.stale_exempt_prs)
        self.assertTrue(release_follow_up.stale_exempt_issues)
        self.assertFalse(release_follow_up.stale_exempt_prs)


if __name__ == "__main__":
    unittest.main()
