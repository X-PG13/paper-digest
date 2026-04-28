from __future__ import annotations

import unittest

from tests.policy_assertions import (
    assert_file_contains_snippets,
    assert_files_contain_snippets,
    assert_issue_form_labels,
    assert_label_descriptions,
    assert_release_note_categories,
    assert_stale_exemptions,
)
from tools.community_pr_labels import desired_pr_labels
from tools.contributor_release_label_policy import (
    CONTRIBUTOR_DISCOVERY_LABELS,
    CONTRIBUTOR_RELEASE_LABEL_SPECS,
    GOOD_FIRST_ISSUE_LABEL,
    HELP_WANTED_LABEL,
    MAINTENANCE_LABEL,
    RELEASE_FACING_LABELS,
    required_artifact_snippets_by_path,
    required_issue_form_labels_by_path,
    required_issue_triage_snippets,
    required_label_descriptions,
    required_label_taxonomy_snippets,
    required_release_note_categories,
    validate_contributor_release_label_policy,
)


class ContributorReleaseLabelPolicyTests(unittest.TestCase):
    def test_contributor_release_label_policy_is_self_consistent(self) -> None:
        validate_contributor_release_label_policy()
        self.assertEqual(len(CONTRIBUTOR_RELEASE_LABEL_SPECS), 5)
        self.assertEqual(
            CONTRIBUTOR_DISCOVERY_LABELS,
            (GOOD_FIRST_ISSUE_LABEL, HELP_WANTED_LABEL),
        )
        self.assertEqual(
            RELEASE_FACING_LABELS,
            ("enhancement", "maintenance", "breaking"),
        )

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

    def test_contributor_release_artifacts_contain_required_contract_snippets(
        self,
    ) -> None:
        assert_files_contain_snippets(
            self,
            required_artifact_snippets_by_path(),
        )

    def test_issue_forms_contain_required_labels(self) -> None:
        assert_issue_form_labels(
            self,
            required_issue_form_labels_by_path(),
        )

    def test_release_yml_matches_release_note_contract(self) -> None:
        assert_release_note_categories(
            self,
            required_release_note_categories(),
        )

    def test_stale_workflow_matches_contributor_discovery_exemptions(self) -> None:
        assert_stale_exemptions(self, CONTRIBUTOR_RELEASE_LABEL_SPECS)

    def test_maintenance_pr_routing_matches_contract(self) -> None:
        for path in (".github/workflows/ci.yml", "Makefile"):
            labels = desired_pr_labels([path], actor="octocat")
            self.assertIn(MAINTENANCE_LABEL, labels)
        for label in CONTRIBUTOR_DISCOVERY_LABELS:
            self.assertNotIn(
                label,
                desired_pr_labels(["README.md"], actor="octocat"),
            )


if __name__ == "__main__":
    unittest.main()
