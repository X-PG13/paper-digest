from __future__ import annotations

import unittest

from tools.docs_contracts import TextSource
from tools.issue_form_policy import (
    RELEASE_LIFECYCLE_ISSUE_FORM_GROUP,
    issue_form_paths_for_group,
)
from tools.lifecycle_contracts import (
    ISSUE_CLOSE_OUT_TEXT_CONTRACTS,
    ISSUE_CLOSE_OUT_TEXT_SOURCES,
    ISSUE_LINKAGE_POST_RELEASE_FORM_FIELDS,
    ISSUE_LINKAGE_RELEASE_PREP_FORM_FIELDS,
    ISSUE_LINKAGE_TEXT_CONTRACTS,
    ISSUE_LINKAGE_TEXT_SOURCES,
    ISSUE_SUMMARY_SOURCE_BINDINGS,
    MAINTAINER_ISSUE_TEXT_CONTRACTS,
    MAINTAINER_ISSUE_TEXT_SOURCES,
    POST_RELEASE_CLOSE_OUT_FORM_FIELD,
    POST_RELEASE_FORM_SOURCE,
    POST_RELEASE_SUMMARY_CONTRACT,
    QUARTERLY_SUMMARY_CONTRACT,
    RELEASE_LIFECYCLE_ISSUE_FORM_PATHS,
    RELEASE_LIFECYCLE_TEXT_CONTRACTS,
    RELEASE_LIFECYCLE_TEXT_SOURCES,
    RELEASE_PREP_CLOSE_OUT_FORM_FIELD,
    RELEASE_PREP_FORM_SOURCE,
    TextContract,
    iter_generated_lifecycle_blocks,
    iter_generated_lifecycle_doc_blocks,
    validate_lifecycle_contract_schema,
)


class LifecycleContractTests(unittest.TestCase):
    def assert_source_labels_match_contract_subjects(
        self,
        *,
        sources: tuple[TextSource, ...],
        contracts: tuple[TextContract, ...],
    ) -> None:
        self.assertEqual(
            {source.label for source in sources},
            {
                expectation.subject
                for contract in contracts
                for expectation in contract.expectations
            },
        )

    def test_validate_lifecycle_contract_schema_accepts_repository_contracts(
        self,
    ) -> None:
        self.assertEqual(validate_lifecycle_contract_schema(), [])

    def test_issue_form_field_ids_are_unique_within_each_contract_group(
        self,
    ) -> None:
        for fields in (
            ISSUE_LINKAGE_RELEASE_PREP_FORM_FIELDS,
            ISSUE_LINKAGE_POST_RELEASE_FORM_FIELDS,
            (RELEASE_PREP_CLOSE_OUT_FORM_FIELD,),
            (POST_RELEASE_CLOSE_OUT_FORM_FIELD,),
        ):
            field_ids = [field.field_id for field in fields]
            self.assertEqual(len(field_ids), len(set(field_ids)))

    def test_summary_contract_doc_fields_match_workflow_default_fields(self) -> None:
        for contract in (
            QUARTERLY_SUMMARY_CONTRACT,
            POST_RELEASE_SUMMARY_CONTRACT,
        ):
            self.assertEqual(
                [label for label, _ in contract.doc_fields],
                [label for label, _ in contract.workflow_defaults],
            )

    def test_generated_lifecycle_blocks_cover_expected_targets(self) -> None:
        actual_blocks = {
            (block.path, block.marker) for block in iter_generated_lifecycle_blocks()
        }
        self.assertEqual(
            actual_blocks,
            {
                ("docs/quarterly-maintainer-review.md", "quarterly-review-close-out"),
                ("docs/quarterly-maintainer-review.md", "quarterly-review-summary"),
                ("docs/post-release-checklist.md", "post-release-close-out"),
                ("docs/post-release-checklist.md", "post-release-summary"),
                (
                    ".github/ISSUE_TEMPLATE/release_preparation.yml",
                    "release-prep-form-scope-summary",
                ),
                (
                    ".github/ISSUE_TEMPLATE/release_preparation.yml",
                    "release-prep-form-compatibility",
                ),
                (
                    ".github/ISSUE_TEMPLATE/release_preparation.yml",
                    "release-prep-form-changelog",
                ),
                (
                    ".github/ISSUE_TEMPLATE/release_preparation.yml",
                    "release-prep-form-validation",
                ),
                (
                    ".github/ISSUE_TEMPLATE/release_preparation.yml",
                    "release-prep-form-follow-up",
                ),
                (
                    ".github/ISSUE_TEMPLATE/release_preparation.yml",
                    "release-prep-form-close-out",
                ),
                (
                    ".github/ISSUE_TEMPLATE/post_release_follow_up.yml",
                    "post-release-form-immediate-validation",
                ),
                (
                    ".github/ISSUE_TEMPLATE/post_release_follow_up.yml",
                    "post-release-form-next-cycle",
                ),
                (
                    ".github/ISSUE_TEMPLATE/post_release_follow_up.yml",
                    "post-release-form-retrospective",
                ),
                (
                    ".github/ISSUE_TEMPLATE/post_release_follow_up.yml",
                    "post-release-form-close-out",
                ),
                (
                    ".github/workflows/quarterly-maintainer-review.yml",
                    "quarterly-review-workflow-close-out",
                ),
                (
                    ".github/workflows/quarterly-maintainer-review.yml",
                    "quarterly-review-workflow-summary",
                ),
                (
                    ".github/workflows/post-release-follow-up.yml",
                    "post-release-workflow-summary",
                ),
            },
        )

    def test_generated_lifecycle_doc_blocks_remain_markdown_only(self) -> None:
        actual_blocks = {
            (block.path, block.marker)
            for block in iter_generated_lifecycle_doc_blocks()
        }
        self.assertEqual(
            actual_blocks,
            {
                ("docs/quarterly-maintainer-review.md", "quarterly-review-close-out"),
                ("docs/quarterly-maintainer-review.md", "quarterly-review-summary"),
                ("docs/post-release-checklist.md", "post-release-close-out"),
                ("docs/post-release-checklist.md", "post-release-summary"),
            },
        )

    def test_lifecycle_issue_form_paths_come_from_registry_group(self) -> None:
        self.assertEqual(
            RELEASE_LIFECYCLE_ISSUE_FORM_PATHS,
            issue_form_paths_for_group(RELEASE_LIFECYCLE_ISSUE_FORM_GROUP),
        )
        self.assertEqual(
            (RELEASE_PREP_FORM_SOURCE.path, POST_RELEASE_FORM_SOURCE.path),
            RELEASE_LIFECYCLE_ISSUE_FORM_PATHS,
        )

    def test_release_lifecycle_text_contracts_cover_core_release_rules(self) -> None:
        contract_names = {
            contract.name for contract in RELEASE_LIFECYCLE_TEXT_CONTRACTS
        }
        self.assertEqual(
            contract_names,
            {
                "release prep changelog",
                "release prep version confirmation",
                "release prep verification suite",
                "quarterly review currency",
                "release-prep issue linkage",
                "release-prep pr linkage",
                "post-release issue linkage",
                "artifact verification",
                "release notes verification",
                "compatibility verification",
                "next-cycle version bump",
                "unreleased reset",
                "operations history update",
                "retrospective capture",
            },
        )

    def test_release_lifecycle_text_contracts_keep_unique_subjects(self) -> None:
        for contract in RELEASE_LIFECYCLE_TEXT_CONTRACTS:
            subjects = [
                expectation.subject for expectation in contract.expectations
            ]
            self.assertEqual(len(subjects), len(set(subjects)))

    def test_release_lifecycle_text_sources_match_contract_subjects(self) -> None:
        self.assert_source_labels_match_contract_subjects(
            sources=RELEASE_LIFECYCLE_TEXT_SOURCES,
            contracts=RELEASE_LIFECYCLE_TEXT_CONTRACTS,
        )

    def test_maintainer_issue_text_contracts_cover_core_issue_rules(self) -> None:
        contract_names = {
            contract.name for contract in MAINTAINER_ISSUE_TEXT_CONTRACTS
        }
        self.assertEqual(
            contract_names,
            {
                "release-prep scope summary",
                "quarterly review close-out",
                "quarterly review summary template",
                "post-release close-out",
                "post-release summary template",
            },
        )

    def test_maintainer_issue_text_contracts_keep_unique_subjects(self) -> None:
        for contract in MAINTAINER_ISSUE_TEXT_CONTRACTS:
            subjects = [
                expectation.subject for expectation in contract.expectations
            ]
            self.assertEqual(len(subjects), len(set(subjects)))

    def test_maintainer_issue_text_sources_match_contract_subjects(self) -> None:
        self.assert_source_labels_match_contract_subjects(
            sources=MAINTAINER_ISSUE_TEXT_SOURCES,
            contracts=MAINTAINER_ISSUE_TEXT_CONTRACTS,
        )

    def test_issue_linkage_text_sources_match_contract_subjects(self) -> None:
        self.assert_source_labels_match_contract_subjects(
            sources=ISSUE_LINKAGE_TEXT_SOURCES,
            contracts=ISSUE_LINKAGE_TEXT_CONTRACTS,
        )

    def test_issue_close_out_text_sources_match_contract_subjects(self) -> None:
        self.assert_source_labels_match_contract_subjects(
            sources=ISSUE_CLOSE_OUT_TEXT_SOURCES,
            contracts=ISSUE_CLOSE_OUT_TEXT_CONTRACTS,
        )

    def test_issue_summary_source_bindings_cover_expected_sections(self) -> None:
        actual_bindings = {
            (
                binding.contract.name,
                binding.doc_source.label,
                binding.workflow_source.label,
            )
            for binding in ISSUE_SUMMARY_SOURCE_BINDINGS
        }
        self.assertEqual(
            actual_bindings,
            {
                (
                    QUARTERLY_SUMMARY_CONTRACT.name,
                    "docs/quarterly-maintainer-review.md#Review Summary Template",
                    ".github/workflows/quarterly-maintainer-review.yml#Review Summary",
                ),
                (
                    POST_RELEASE_SUMMARY_CONTRACT.name,
                    "docs/post-release-checklist.md#Follow-Up Summary Template",
                    ".github/workflows/post-release-follow-up.yml#Post-Release Summary",
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
