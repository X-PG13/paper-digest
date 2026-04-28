from __future__ import annotations

import unittest

from tools.reply_policy_base import (
    ReplyContractSpec,
    ReplySnippetPolicySpec,
    collect_issue_triage_snippets,
    collect_label_taxonomy_snippets,
    collect_saved_reply_snippets,
    get_reply_spec_by_slug,
    validate_reply_contract_specs,
    validate_reply_snippet_policy_specs,
)


class ReplyPolicyBaseTests(unittest.TestCase):
    def test_get_reply_spec_by_slug_and_saved_reply_collector(self) -> None:
        specs = (
            ReplyContractSpec(
                slug="alpha",
                header="Alpha header",
                body_lines=("Alpha body",),
                bullet_items=("Alpha bullet",),
                footer_lines=("Alpha footer",),
            ),
            ReplyContractSpec(
                slug="beta",
                header="Beta header",
                body_lines=("Beta body",),
            ),
        )

        self.assertEqual(
            get_reply_spec_by_slug(
                specs,
                "alpha",
                unknown_error_prefix="unknown reply slug",
            ).header,
            "Alpha header",
        )
        self.assertEqual(
            collect_saved_reply_snippets(specs, "beta"),
            ("## `beta`", "Beta header", "Beta body"),
        )
        with self.assertRaisesRegex(KeyError, "unknown reply slug: missing"):
            get_reply_spec_by_slug(
                specs,
                "missing",
                unknown_error_prefix="unknown reply slug",
            )

    def test_snippet_collectors_preserve_order(self) -> None:
        specs = (
            ReplySnippetPolicySpec(
                reply_slug="alpha",
                issue_triage_snippets=("issue-a",),
                label_taxonomy_snippets=("taxonomy-a",),
            ),
            ReplySnippetPolicySpec(
                reply_slug="beta",
                issue_triage_snippets=("issue-b1", "issue-b2"),
                label_taxonomy_snippets=("taxonomy-b",),
            ),
        )

        self.assertEqual(
            collect_issue_triage_snippets(specs),
            ("issue-a", "issue-b1", "issue-b2"),
        )
        self.assertEqual(
            collect_label_taxonomy_snippets(specs),
            ("taxonomy-a", "taxonomy-b"),
        )

    def test_validate_reply_contract_specs_rejects_empty_parts(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate reply slug: alpha"):
            validate_reply_contract_specs(
                (
                    ReplyContractSpec(
                        slug="alpha",
                        header="Alpha",
                        body_lines=("Alpha body",),
                    ),
                    ReplyContractSpec(
                        slug="alpha",
                        header="Alpha again",
                        body_lines=("Alpha body",),
                    ),
                ),
                duplicate_error_prefix="duplicate reply slug",
                missing_header_error_prefix="reply must define a header",
                empty_reply_error_prefix="reply must not be empty",
                empty_body_error_prefix="reply body must not be empty",
                empty_bullet_error_prefix="reply bullets must not be empty",
                empty_footer_error_prefix="reply footer must not be empty",
            )

        with self.assertRaisesRegex(
            ValueError,
            "reply body must not be empty: alpha",
        ):
            validate_reply_contract_specs(
                (
                    ReplyContractSpec(
                        slug="alpha",
                        header="Alpha",
                        body_lines=("",),
                    ),
                ),
                duplicate_error_prefix="duplicate reply slug",
                missing_header_error_prefix="reply must define a header",
                empty_reply_error_prefix="reply must not be empty",
                empty_body_error_prefix="reply body must not be empty",
                empty_bullet_error_prefix="reply bullets must not be empty",
                empty_footer_error_prefix="reply footer must not be empty",
            )

    def test_validate_reply_snippet_policy_specs_uses_lookup_and_rejects_empty(
        self,
    ) -> None:
        seen: list[str] = []
        validate_reply_snippet_policy_specs(
            (
                ReplySnippetPolicySpec(
                    reply_slug="alpha",
                    issue_triage_snippets=("issue-a",),
                    label_taxonomy_snippets=("taxonomy-a",),
                ),
            ),
            duplicate_error_prefix="duplicate triage reply slug",
            missing_issue_triage_error_prefix="missing issue snippets",
            missing_label_taxonomy_error_prefix="missing taxonomy snippets",
            reply_lookup=seen.append,
        )
        self.assertEqual(seen, ["alpha"])

        with self.assertRaisesRegex(
            ValueError,
            "missing taxonomy snippets: alpha",
        ):
            validate_reply_snippet_policy_specs(
                (
                    ReplySnippetPolicySpec(
                        reply_slug="alpha",
                        issue_triage_snippets=("issue-a",),
                        label_taxonomy_snippets=(),
                    ),
                ),
                duplicate_error_prefix="duplicate triage reply slug",
                missing_issue_triage_error_prefix="missing issue snippets",
                missing_label_taxonomy_error_prefix="missing taxonomy snippets",
                reply_lookup=seen.append,
            )


if __name__ == "__main__":
    unittest.main()
