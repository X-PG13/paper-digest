from __future__ import annotations

import unittest

from tests.policy_assertions import (
    assert_file_contains_snippets,
    assert_files_contain_snippets,
    assert_issue_form_labels,
    assert_issue_template_contact_links,
    assert_label_descriptions,
    assert_release_note_categories,
    assert_release_note_excluded_labels,
)
from tools.community_pr_labels import desired_pr_labels
from tools.routing_label_policy import (
    ROUTING_LABEL_SPECS,
    required_artifact_snippets_by_path,
    required_issue_form_labels_by_path,
    required_issue_template_contact_links,
    required_issue_triage_snippets,
    required_label_descriptions,
    required_label_taxonomy_snippets,
    required_release_note_categories,
    required_release_note_excluded_labels,
    validate_routing_label_policy,
)


class RoutingLabelPolicyTests(unittest.TestCase):
    def test_routing_label_policy_is_self_consistent(self) -> None:
        validate_routing_label_policy()
        self.assertEqual(len(ROUTING_LABEL_SPECS), 5)

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

    def test_routing_artifacts_contain_required_contract_snippets(self) -> None:
        assert_files_contain_snippets(
            self,
            required_artifact_snippets_by_path(),
        )

    def test_issue_forms_contain_required_labels(self) -> None:
        assert_issue_form_labels(
            self,
            required_issue_form_labels_by_path(),
        )

    def test_issue_template_config_contains_required_contact_links(self) -> None:
        assert_issue_template_contact_links(
            self,
            required_issue_template_contact_links(),
        )

    def test_release_yml_matches_routing_label_contract(self) -> None:
        assert_release_note_categories(
            self,
            required_release_note_categories(),
        )
        assert_release_note_excluded_labels(
            self,
            required_release_note_excluded_labels(),
        )

    def test_pr_routing_matches_proposal_and_dependency_contracts(self) -> None:
        self.assertIn(
            "proposal",
            desired_pr_labels(["docs/roadmap-policy.md"], actor="octocat"),
        )
        self.assertIn(
            "dependencies",
            desired_pr_labels([".github/dependabot.yml"], actor="octocat"),
        )
        self.assertIn(
            "dependencies",
            desired_pr_labels(["paper_digest/service.py"], actor="dependabot[bot]"),
        )


if __name__ == "__main__":
    unittest.main()
