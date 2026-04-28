from __future__ import annotations

import unittest

from tests.policy_assertions import (
    assert_issue_form_fields,
    assert_issue_form_labels,
    assert_issue_form_metadata,
)
from tools.issue_form_policy import (
    BUG_REPORT_FORM_NAME,
    BUG_REPORT_FORM_PATH,
    BUG_REPORT_FORM_TITLE,
    CONTRIBUTOR_RELEASE_LABEL_ISSUE_FORM_GROUP,
    FEATURE_REQUEST_FORM_PATH,
    POST_RELEASE_FOLLOW_UP_FORM_PATH,
    PROPOSAL_FORM_PATH,
    RELEASE_LIFECYCLE_ISSUE_FORM_GROUP,
    RELEASE_PREPARATION_FORM_PATH,
    ROUTING_LABEL_ISSUE_FORM_GROUP,
    STATUS_LABEL_ISSUE_FORM_GROUP,
    SUPPORT_REQUEST_FORM_NAME,
    SUPPORT_REQUEST_FORM_PATH,
    SUPPORT_REQUEST_FORM_TITLE,
    get_issue_form_group_spec,
    get_issue_form_spec,
    issue_form_labels_by_path,
    issue_form_labels_for_group,
    issue_form_paths_for_group,
    required_issue_form_group_specs,
    required_issue_form_paths,
    required_issue_form_specs,
    validate_issue_form_policy,
)


class IssueFormPolicyTests(unittest.TestCase):
    def test_issue_form_policy_is_self_consistent(self) -> None:
        validate_issue_form_policy()
        self.assertEqual(len(required_issue_form_specs()), 6)

    def test_issue_form_path_lookup_matches_registered_specs(self) -> None:
        specs = required_issue_form_specs()

        self.assertEqual(required_issue_form_paths(), {spec.path for spec in specs})
        for spec in specs:
            with self.subTest(path=spec.path):
                self.assertEqual(get_issue_form_spec(spec.path), spec)
        with self.assertRaisesRegex(KeyError, "unknown issue form path"):
            get_issue_form_spec(".github/ISSUE_TEMPLATE/missing.yml")

    def test_issue_form_labels_match_registered_specs(self) -> None:
        labels_by_path = issue_form_labels_by_path(required_issue_form_paths())

        self.assertEqual(
            labels_by_path,
            {
                spec.path: spec.labels
                for spec in required_issue_form_specs()
            },
        )
        assert_issue_form_labels(self, labels_by_path)
        with self.assertRaisesRegex(KeyError, "unknown issue form path"):
            issue_form_labels_by_path((".github/ISSUE_TEMPLATE/missing.yml",))

    def test_issue_form_groups_match_registered_path_sets(self) -> None:
        expected_groups = {
            ROUTING_LABEL_ISSUE_FORM_GROUP: (
                BUG_REPORT_FORM_PATH,
                SUPPORT_REQUEST_FORM_PATH,
                PROPOSAL_FORM_PATH,
            ),
            CONTRIBUTOR_RELEASE_LABEL_ISSUE_FORM_GROUP: (
                FEATURE_REQUEST_FORM_PATH,
                PROPOSAL_FORM_PATH,
                RELEASE_PREPARATION_FORM_PATH,
                POST_RELEASE_FOLLOW_UP_FORM_PATH,
            ),
            STATUS_LABEL_ISSUE_FORM_GROUP: (
                RELEASE_PREPARATION_FORM_PATH,
                POST_RELEASE_FOLLOW_UP_FORM_PATH,
            ),
            RELEASE_LIFECYCLE_ISSUE_FORM_GROUP: (
                RELEASE_PREPARATION_FORM_PATH,
                POST_RELEASE_FOLLOW_UP_FORM_PATH,
            ),
        }

        self.assertEqual(len(required_issue_form_group_specs()), len(expected_groups))
        for key, paths in expected_groups.items():
            with self.subTest(group=key):
                self.assertEqual(get_issue_form_group_spec(key).paths, paths)
                self.assertEqual(issue_form_paths_for_group(key), paths)
                self.assertEqual(
                    issue_form_labels_for_group(key),
                    issue_form_labels_by_path(paths),
                )
        with self.assertRaisesRegex(KeyError, "unknown issue form group"):
            issue_form_paths_for_group("missing-group")

    def test_intake_and_support_form_metadata_aliases_registry(self) -> None:
        from tools import issue_intake_policy, support_policy

        self.assertEqual(issue_intake_policy.BUG_REPORT_FORM_PATH, BUG_REPORT_FORM_PATH)
        self.assertEqual(issue_intake_policy.BUG_REPORT_FORM_NAME, BUG_REPORT_FORM_NAME)
        self.assertEqual(
            issue_intake_policy.BUG_REPORT_FORM_TITLE,
            BUG_REPORT_FORM_TITLE,
        )
        self.assertEqual(
            support_policy.SUPPORT_REQUEST_FORM_PATH,
            SUPPORT_REQUEST_FORM_PATH,
        )
        self.assertEqual(
            support_policy.SUPPORT_REQUEST_FORM_NAME,
            SUPPORT_REQUEST_FORM_NAME,
        )
        self.assertEqual(
            support_policy.SUPPORT_REQUEST_FORM_TITLE,
            SUPPORT_REQUEST_FORM_TITLE,
        )

    def test_issue_forms_match_required_metadata_and_fields(self) -> None:
        for spec in required_issue_form_specs():
            with self.subTest(path=spec.path):
                assert_issue_form_metadata(
                    self,
                    spec.path,
                    name=spec.name,
                    title=spec.title,
                )
                assert_issue_form_fields(
                    self,
                    spec.path,
                    spec.fields,
                )


if __name__ == "__main__":
    unittest.main()
