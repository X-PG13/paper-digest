from __future__ import annotations

import unittest
from dataclasses import dataclass

from tools.docs_assertions import (
    build_subject_finding,
    extend_contract_errors,
    normalize_text_block,
    require_expected_fields,
    require_expected_items,
    text_contains_all_snippets,
)
from tools.docs_findings import DocsCheckFinding, infer_repository_path
from tools.docs_sources import TextSourceOrigin


@dataclass(frozen=True)
class FakeExpectation:
    subject: str
    snippets: tuple[str, ...]


@dataclass(frozen=True)
class FakeContract:
    name: str
    expectations: tuple[FakeExpectation, ...]


class DocsAssertionsTests(unittest.TestCase):
    def test_normalize_text_block_strips_markup_and_collapses_space(self) -> None:
        self.assertEqual(
            normalize_text_block("  `Make`  _Docs_   ~Check~  "),
            "make docs check",
        )

    def test_text_contains_all_snippets_uses_normalized_matching(self) -> None:
        self.assertTrue(
            text_contains_all_snippets(
                "Use `make docs-check` before merge.",
                ("make docs-check", "before   merge"),
            )
        )
        self.assertFalse(
            text_contains_all_snippets(
                "Use `make docs-check` before merge.",
                ("release-check",),
            )
        )

    def test_require_expected_fields_reports_missing_and_mismatched_values(
        self,
    ) -> None:
        errors: list[DocsCheckFinding] = []

        require_expected_fields(
            "issue summary semantics",
            "post-release summary",
            "docs/post-release-checklist.md#Summary",
            {"Release": "v1.2.3", "Verified by": "@bot"},
            {"Release": "v1.2.3", "Verified by": "@maintainer", "Next-cycle": "done"},
            errors,
        )

        self.assertEqual(
            errors,
            [
                DocsCheckFinding(
                    message=(
                        "issue summary semantics contract "
                        "'post-release summary' has unexpected "
                        "value for 'Verified by' in "
                        "docs/post-release-checklist.md#Summary: expected "
                        "'@maintainer', found '@bot'"
                    ),
                    path="docs/post-release-checklist.md",
                ),
                DocsCheckFinding(
                    message=(
                        "issue summary semantics contract 'post-release summary' "
                        "missing field 'Next-cycle' from "
                        "docs/post-release-checklist.md#Summary"
                    ),
                    path="docs/post-release-checklist.md",
                ),
            ],
        )

    def test_require_expected_items_matches_normalized_items(self) -> None:
        errors: list[DocsCheckFinding] = []

        require_expected_items(
            "issue close-out",
            "quarterly review close-out",
            "quarterly-maintainer-review.yml#close-out",
            ["Link any follow-up issue or pull request here."],
            (
                "link any follow-up issue or pull request here.",
                "Say none explicitly.",
            ),
            errors,
        )

        self.assertEqual(
            errors,
            [
                DocsCheckFinding(
                    message=(
                        "issue close-out contract 'quarterly review close-out' "
                        "missing item from quarterly-maintainer-review.yml#close-out: "
                        "Say none explicitly."
                    ),
                    path="quarterly-maintainer-review.yml",
                )
            ],
        )

    def test_extend_contract_errors_reports_missing_snippet_group(self) -> None:
        errors: list[DocsCheckFinding] = []

        extend_contract_errors(
            "release lifecycle",
            {
                "RELEASING.md#Before Tagging": "Ensure CHANGELOG is updated.",
                "RELEASING.md#After Release": "Open the post-release follow-up issue.",
            },
            [
                FakeContract(
                    name="release prep verification suite",
                    expectations=(
                        FakeExpectation(
                            subject="RELEASING.md#Before Tagging",
                            snippets=("make check", "make build", "make release-check"),
                        ),
                    ),
                ),
                FakeContract(
                    name="post-release issue linkage",
                    expectations=(
                        FakeExpectation(
                            subject="RELEASING.md#After Release",
                            snippets=("post-release follow-up issue",),
                        ),
                    ),
                ),
            ],
            errors,
        )

        self.assertEqual(
            errors,
            [
                DocsCheckFinding(
                    message=(
                        "release lifecycle contract "
                        "'release prep verification suite' missing from "
                        "RELEASING.md#Before Tagging: make check, make build, "
                        "make release-check"
                    ),
                    path="RELEASING.md",
                )
            ],
        )

    def test_infer_repository_path_accepts_fragment_subjects(self) -> None:
        self.assertEqual(
            infer_repository_path(".github/ISSUE_TEMPLATE/release_preparation.yml#close_out"),
            ".github/ISSUE_TEMPLATE/release_preparation.yml",
        )
        self.assertIsNone(infer_repository_path("release lifecycle contract"))

    def test_build_subject_finding_prefers_declared_origin(self) -> None:
        self.assertEqual(
            build_subject_finding(
                "missing item",
                "RELEASING.md#Before Tagging",
                subject_origins={
                    "RELEASING.md#Before Tagging": TextSourceOrigin(
                        path="RELEASING.md",
                        line=12,
                        end_line=18,
                    )
                },
            ),
            DocsCheckFinding(
                message="missing item",
                path="RELEASING.md",
                line=12,
                end_line=18,
            ),
        )


if __name__ == "__main__":
    unittest.main()
