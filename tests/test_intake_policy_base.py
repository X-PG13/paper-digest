from __future__ import annotations

import unittest

from tools.intake_policy_base import (
    ContactLinkSpec,
    DocPathSpec,
    KeyLabelSpec,
    collect_spec_snippets,
    validate_contact_link_specs,
    validate_unique_doc_paths,
    validate_unique_key_labels,
)


class IntakePolicyBaseTests(unittest.TestCase):
    def test_collect_spec_snippets_preserves_group_order(self) -> None:
        class FormSnippetSpec(KeyLabelSpec):
            def __init__(
                self,
                *,
                key: str,
                label: str,
                required_form_snippets: tuple[str, ...],
            ) -> None:
                super().__init__(key=key, label=label)
                self.required_form_snippets = required_form_snippets

        snippets = collect_spec_snippets(
            (
                FormSnippetSpec(
                    key="alpha",
                    label="Alpha",
                    required_form_snippets=("alpha-1",),
                ),
            ),
            (
                FormSnippetSpec(
                    key="beta",
                    label="Beta",
                    required_form_snippets=("beta-1", "beta-2"),
                ),
            ),
            attribute="required_form_snippets",
        )

        self.assertEqual(snippets, ("alpha-1", "beta-1", "beta-2"))

    def test_validate_unique_doc_paths_rejects_duplicates(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate docs path: README.md"):
            validate_unique_doc_paths(
                (
                    DocPathSpec(path="README.md"),
                    DocPathSpec(path="README.md"),
                ),
                duplicate_error_prefix="duplicate docs path",
            )

    def test_validate_unique_key_labels_rejects_duplicates(self) -> None:
        specs = (
            KeyLabelSpec(key="alpha", label="Alpha"),
            KeyLabelSpec(key="alpha", label="Beta"),
        )
        with self.assertRaisesRegex(ValueError, "duplicate policy key: alpha"):
            validate_unique_key_labels(
                specs,
                duplicate_key_error_prefix="duplicate policy key",
                duplicate_label_error_prefix="duplicate policy label",
            )

        label_specs = (
            KeyLabelSpec(key="alpha", label="Alpha"),
            KeyLabelSpec(key="beta", label="Alpha"),
        )
        with self.assertRaisesRegex(
            ValueError,
            "duplicate policy label: Alpha",
        ):
            validate_unique_key_labels(
                label_specs,
                duplicate_key_error_prefix="duplicate policy key",
                duplicate_label_error_prefix="duplicate policy label",
            )

    def test_validate_contact_link_specs_rejects_invalid_links(self) -> None:
        validate_contact_link_specs(
            (
                ContactLinkSpec(
                    name="Support",
                    target="SUPPORT.md",
                    about="Read support expectations.",
                ),
            ),
            duplicate_name_error_prefix="duplicate contact link",
        )

        with self.assertRaisesRegex(ValueError, "contact link name"):
            validate_contact_link_specs(
                (
                    ContactLinkSpec(
                        name="",
                        target="SUPPORT.md",
                        about="Read support expectations.",
                    ),
                ),
                duplicate_name_error_prefix="duplicate contact link",
            )

        with self.assertRaisesRegex(ValueError, "contact link target"):
            validate_contact_link_specs(
                (
                    ContactLinkSpec(
                        name="Support",
                        target="",
                        about="Read support expectations.",
                    ),
                ),
                duplicate_name_error_prefix="duplicate contact link",
            )

        with self.assertRaisesRegex(ValueError, "contact link about"):
            validate_contact_link_specs(
                (
                    ContactLinkSpec(
                        name="Support",
                        target="SUPPORT.md",
                        about="",
                    ),
                ),
                duplicate_name_error_prefix="duplicate contact link",
            )

        with self.assertRaisesRegex(ValueError, "duplicate contact link: Support"):
            validate_contact_link_specs(
                (
                    ContactLinkSpec(
                        name="Support",
                        target="SUPPORT.md",
                        about="Read support expectations.",
                    ),
                    ContactLinkSpec(
                        name="Support",
                        target="docs/support.md",
                        about="Duplicate support link.",
                    ),
                ),
                duplicate_name_error_prefix="duplicate contact link",
            )


if __name__ == "__main__":
    unittest.main()
