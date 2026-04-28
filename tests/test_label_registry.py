from __future__ import annotations

import unittest

from tests.policy_assertions import (
    assert_file_contains_snippets,
    load_label_descriptions,
)
from tools.label_registry import (
    CATEGORY_TO_SECTION,
    CONTRIBUTION_CATEGORY,
    CONTRIBUTION_SECTION,
    LABEL_REGISTRY,
    PLANNING_CATEGORY,
    PLANNING_SECTION,
    RESOLUTION_CATEGORY,
    RESOLUTION_SECTION,
    ROUTING_CATEGORY,
    ROUTING_SECTION,
    TRIAGE_STATUS_CATEGORY,
    TRIAGE_STATUS_SECTION,
    get_label_category,
    get_label_description,
    labels_for_category,
    required_label_descriptions,
    required_label_taxonomy_rows,
    validate_label_registry,
)


class LabelRegistryTests(unittest.TestCase):
    def test_label_registry_is_self_consistent(self) -> None:
        validate_label_registry()
        self.assertEqual(len(LABEL_REGISTRY), 22)
        self.assertEqual(CATEGORY_TO_SECTION[ROUTING_CATEGORY], ROUTING_SECTION)
        self.assertEqual(CATEGORY_TO_SECTION[PLANNING_CATEGORY], PLANNING_SECTION)
        self.assertEqual(
            CATEGORY_TO_SECTION[TRIAGE_STATUS_CATEGORY], TRIAGE_STATUS_SECTION
        )
        self.assertEqual(
            CATEGORY_TO_SECTION[CONTRIBUTION_CATEGORY], CONTRIBUTION_SECTION
        )
        self.assertEqual(CATEGORY_TO_SECTION[RESOLUTION_CATEGORY], RESOLUTION_SECTION)

    def test_labels_json_matches_registry_descriptions(self) -> None:
        self.assertEqual(load_label_descriptions(), required_label_descriptions())

    def test_label_taxonomy_tables_match_registry_rows(self) -> None:
        for rows in required_label_taxonomy_rows().values():
            assert_file_contains_snippets(
                self,
                "docs/label-taxonomy.md",
                rows,
            )

    def test_category_helpers_return_expected_boundaries(self) -> None:
        self.assertEqual(get_label_category("bug"), ROUTING_CATEGORY)
        self.assertEqual(get_label_category("proposal"), PLANNING_CATEGORY)
        self.assertEqual(get_label_category("blocked"), TRIAGE_STATUS_CATEGORY)
        self.assertEqual(get_label_category("help wanted"), CONTRIBUTION_CATEGORY)
        self.assertEqual(get_label_category("wontfix"), RESOLUTION_CATEGORY)
        self.assertEqual(
            labels_for_category(CONTRIBUTION_CATEGORY),
            ("good first issue", "help wanted"),
        )
        self.assertEqual(
            get_label_description("release-prep"),
            "Maintainer release-preparation tracking work",
        )


if __name__ == "__main__":
    unittest.main()
