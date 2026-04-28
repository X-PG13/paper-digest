from __future__ import annotations

import unittest

from tools.label_policy_base import (
    ArtifactContract,
    LabelPolicySpec,
    collect_artifact_snippets_by_path,
    collect_issue_triage_snippets,
    collect_label_descriptions,
    collect_label_taxonomy_snippets,
    collect_release_note_categories,
    collect_release_note_excluded_labels,
    validate_label_policy_specs,
)


class LabelPolicyBaseTests(unittest.TestCase):
    def test_collect_helpers_preserve_order_and_group_artifacts(self) -> None:
        specs = (
            LabelPolicySpec(
                label="alpha",
                label_json_description="Alpha description",
                issue_triage_snippets=("issue-a",),
                label_taxonomy_snippets=("taxonomy-a",),
                artifact_contracts=(
                    ArtifactContract(path="docs/a.md", snippets=("artifact-a1",)),
                ),
                release_note_category="Features",
            ),
            LabelPolicySpec(
                label="beta",
                label_json_description="Beta description",
                issue_triage_snippets=("issue-b1", "issue-b2"),
                label_taxonomy_snippets=("taxonomy-b",),
                artifact_contracts=(
                    ArtifactContract(path="docs/a.md", snippets=("artifact-a2",)),
                    ArtifactContract(path="docs/b.md", snippets=("artifact-b1",)),
                ),
                release_note_category="Maintenance",
                release_note_excluded=False,
            ),
            LabelPolicySpec(
                label="gamma",
                label_json_description="Gamma description",
                issue_triage_snippets=("issue-c",),
                label_taxonomy_snippets=("taxonomy-c",),
                release_note_excluded=True,
            ),
        )

        self.assertEqual(
            collect_issue_triage_snippets(specs),
            ("issue-a", "issue-b1", "issue-b2", "issue-c"),
        )
        self.assertEqual(
            collect_label_taxonomy_snippets(specs),
            ("taxonomy-a", "taxonomy-b", "taxonomy-c"),
        )
        self.assertEqual(
            collect_label_descriptions(specs),
            {
                "alpha": "Alpha description",
                "beta": "Beta description",
                "gamma": "Gamma description",
            },
        )
        self.assertEqual(
            collect_artifact_snippets_by_path(specs),
            {
                "docs/a.md": ("artifact-a1", "artifact-a2"),
                "docs/b.md": ("artifact-b1",),
            },
        )
        self.assertEqual(
            collect_release_note_categories(specs),
            {
                "Features": ("alpha",),
                "Maintenance": ("beta",),
            },
        )
        self.assertEqual(
            collect_release_note_excluded_labels(specs),
            ("gamma",),
        )

    def test_validate_label_policy_specs_accepts_reply_lookup(self) -> None:
        seen_replies: list[str] = []
        specs = (
            LabelPolicySpec(
                label="alpha",
                label_json_description="Alpha description",
                issue_triage_snippets=("issue-a",),
                label_taxonomy_snippets=("taxonomy-a",),
                reply_slug="needs-info",
                artifact_contracts=(
                    ArtifactContract(path="docs/a.md", snippets=("artifact-a1",)),
                ),
            ),
        )

        validate_label_policy_specs(
            specs,
            duplicate_error_prefix="duplicate test label",
            missing_issue_triage_error_prefix="missing issue snippets",
            missing_label_taxonomy_error_prefix="missing taxonomy snippets",
            manual_only_auto_error_prefix="manual-only test label must not auto-route",
            reply_lookup=seen_replies.append,
        )

        self.assertEqual(seen_replies, ["needs-info"])

    def test_validate_label_policy_specs_rejects_duplicate_labels(self) -> None:
        specs = (
            LabelPolicySpec(
                label="alpha",
                label_json_description="Alpha description",
                issue_triage_snippets=("issue-a",),
                label_taxonomy_snippets=("taxonomy-a",),
            ),
            LabelPolicySpec(
                label="alpha",
                label_json_description="Alpha description",
                issue_triage_snippets=("issue-b",),
                label_taxonomy_snippets=("taxonomy-b",),
            ),
        )

        with self.assertRaisesRegex(ValueError, "duplicate test label: alpha"):
            validate_label_policy_specs(
                specs,
                duplicate_error_prefix="duplicate test label",
                missing_issue_triage_error_prefix="missing issue snippets",
                missing_label_taxonomy_error_prefix="missing taxonomy snippets",
                manual_only_auto_error_prefix=(
                    "manual-only test label must not auto-route"
                ),
            )

    def test_validate_label_policy_specs_rejects_manual_only_auto_routing(
        self,
    ) -> None:
        specs = (
            LabelPolicySpec(
                label="alpha",
                label_json_description="Alpha description",
                issue_triage_snippets=("issue-a",),
                label_taxonomy_snippets=("taxonomy-a",),
                manual_only=True,
                auto_pr_routing_paths=("docs/a.md",),
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "manual-only test label must not auto-route: alpha",
        ):
            validate_label_policy_specs(
                specs,
                duplicate_error_prefix="duplicate test label",
                missing_issue_triage_error_prefix="missing issue snippets",
                missing_label_taxonomy_error_prefix="missing taxonomy snippets",
                manual_only_auto_error_prefix=(
                    "manual-only test label must not auto-route"
                ),
            )

    def test_validate_label_policy_specs_rejects_release_note_conflicts(
        self,
    ) -> None:
        specs = (
            LabelPolicySpec(
                label="alpha",
                label_json_description="Alpha description",
                issue_triage_snippets=("issue-a",),
                label_taxonomy_snippets=("taxonomy-a",),
                release_note_category="Features",
                release_note_excluded=True,
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "release-note label cannot be both categorized and excluded: alpha",
        ):
            validate_label_policy_specs(
                specs,
                duplicate_error_prefix="duplicate test label",
                missing_issue_triage_error_prefix="missing issue snippets",
                missing_label_taxonomy_error_prefix="missing taxonomy snippets",
                manual_only_auto_error_prefix=(
                    "manual-only test label must not auto-route"
                ),
            )

    def test_validate_label_policy_specs_rejects_empty_artifact_contracts(
        self,
    ) -> None:
        missing_path = (
            LabelPolicySpec(
                label="alpha",
                label_json_description="Alpha description",
                issue_triage_snippets=("issue-a",),
                label_taxonomy_snippets=("taxonomy-a",),
                artifact_contracts=(
                    ArtifactContract(path="", snippets=("artifact-a1",)),
                ),
            ),
        )
        with self.assertRaisesRegex(
            ValueError,
            "artifact contract path must not be empty",
        ):
            validate_label_policy_specs(
                missing_path,
                duplicate_error_prefix="duplicate test label",
                missing_issue_triage_error_prefix="missing issue snippets",
                missing_label_taxonomy_error_prefix="missing taxonomy snippets",
                manual_only_auto_error_prefix=(
                    "manual-only test label must not auto-route"
                ),
            )

        missing_snippets = (
            LabelPolicySpec(
                label="alpha",
                label_json_description="Alpha description",
                issue_triage_snippets=("issue-a",),
                label_taxonomy_snippets=("taxonomy-a",),
                artifact_contracts=(
                    ArtifactContract(path="docs/a.md", snippets=()),
                ),
            ),
        )
        with self.assertRaisesRegex(
            ValueError,
            "artifact contract must define snippets: docs/a.md",
        ):
            validate_label_policy_specs(
                missing_snippets,
                duplicate_error_prefix="duplicate test label",
                missing_issue_triage_error_prefix="missing issue snippets",
                missing_label_taxonomy_error_prefix="missing taxonomy snippets",
                manual_only_auto_error_prefix=(
                    "manual-only test label must not auto-route"
                ),
            )


if __name__ == "__main__":
    unittest.main()
