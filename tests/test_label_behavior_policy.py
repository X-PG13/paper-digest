from __future__ import annotations

import unittest

from tests.policy_assertions import (
    assert_file_contains_snippets,
    assert_label_descriptions,
    assert_release_note_categories,
    assert_release_note_excluded_labels,
    assert_stale_exemptions,
)
from tools.community_pr_labels import desired_pr_labels
from tools.label_behavior_policy import (
    BLOCKED_LABEL,
    LABEL_BEHAVIOR_SPECS,
    MANUAL_RESOLUTION_LABELS,
    RELEASE_NOTE_LABEL,
    required_issue_triage_snippets,
    required_label_descriptions,
    required_label_taxonomy_snippets,
    required_release_note_categories,
    required_release_note_excluded_labels,
    validate_label_behavior_policy,
)


class LabelBehaviorPolicyTests(unittest.TestCase):
    def test_label_behavior_policy_is_self_consistent(self) -> None:
        validate_label_behavior_policy()
        self.assertEqual(len(LABEL_BEHAVIOR_SPECS), 6)
        self.assertEqual(MANUAL_RESOLUTION_LABELS, ("duplicate", "invalid", "wontfix"))

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

    def test_pr_routing_only_auto_applies_documentation(self) -> None:
        documentation_paths = next(
            behavior.auto_pr_routing_paths
            for behavior in LABEL_BEHAVIOR_SPECS
            if behavior.label == "documentation"
        )
        for path in documentation_paths:
            labels = desired_pr_labels([path], actor="octocat")
            self.assertIn("documentation", labels)
            self.assertTrue(set(MANUAL_RESOLUTION_LABELS).isdisjoint(labels))

    def test_stale_workflow_matches_issue_and_pr_exemptions(self) -> None:
        assert_stale_exemptions(self, LABEL_BEHAVIOR_SPECS)

    def test_release_yml_matches_release_note_contract(self) -> None:
        assert_release_note_categories(
            self,
            required_release_note_categories(),
        )
        assert_release_note_excluded_labels(
            self,
            required_release_note_excluded_labels(),
        )

        blocked = next(
            behavior
            for behavior in LABEL_BEHAVIOR_SPECS
            if behavior.label == BLOCKED_LABEL
        )
        release_note = next(
            behavior
            for behavior in LABEL_BEHAVIOR_SPECS
            if behavior.label == RELEASE_NOTE_LABEL
        )
        self.assertTrue(blocked.stale_exempt_issues)
        self.assertTrue(blocked.stale_exempt_prs)
        self.assertTrue(release_note.stale_exempt_issues)
        self.assertTrue(release_note.stale_exempt_prs)


if __name__ == "__main__":
    unittest.main()
