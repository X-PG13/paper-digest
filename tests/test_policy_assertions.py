from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.policy_assertions import (
    assert_file_contains_snippets,
    assert_files_contain_snippets,
    assert_issue_form_checkbox_options,
    assert_issue_form_fields,
    assert_issue_form_labels,
    assert_issue_form_metadata,
    assert_issue_template_contact_links,
    assert_label_descriptions,
    assert_release_note_categories,
    assert_release_note_excluded_labels,
    assert_stale_exemptions,
    load_issue_form_labels,
    load_issue_form_metadata,
    load_issue_template_contact_links,
    load_label_descriptions,
    load_release_note_config,
    load_stale_exempt_labels,
    normalize_space,
    parse_comma_separated_labels,
    strip_yaml_scalar_quotes,
)


class PolicyAssertionsTests(unittest.TestCase):
    def test_normalize_space_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_space("one\n  two\tthree"), "one two three")

    def test_load_and_assert_label_descriptions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            labels_path = Path(tmpdir) / "labels.json"
            labels_path.write_text(
                '[{"name": "bug", "description": "Bug report"}]',
                encoding="utf-8",
            )

            self.assertEqual(
                load_label_descriptions(labels_path),
                {"bug": "Bug report"},
            )
            assert_label_descriptions(
                self,
                {"bug": "Bug report"},
                path=labels_path,
            )

    def test_parse_comma_separated_labels_trims_empty_values(self) -> None:
        self.assertEqual(
            parse_comma_separated_labels(" blocked, release-note, ,help wanted "),
            frozenset({"blocked", "release-note", "help wanted"}),
        )

    def test_strip_yaml_scalar_quotes_handles_simple_scalars(self) -> None:
        self.assertEqual(strip_yaml_scalar_quotes(' "Features" '), "Features")
        self.assertEqual(strip_yaml_scalar_quotes("'release-note'"), "release-note")
        self.assertEqual(strip_yaml_scalar_quotes("maintenance"), "maintenance")

    def test_load_and_assert_stale_exempt_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stale_path = Path(tmpdir) / "stale.yml"
            stale_path.write_text(
                "\n".join(
                    (
                        "with:",
                        "  exempt-issue-labels: blocked,release-prep",
                        "  exempt-pr-labels: blocked,release-note",
                    )
                ),
                encoding="utf-8",
            )
            exempt_labels = load_stale_exempt_labels(stale_path)

            self.assertEqual(
                exempt_labels.issues,
                frozenset({"blocked", "release-prep"}),
            )
            self.assertEqual(
                exempt_labels.pull_requests,
                frozenset({"blocked", "release-note"}),
            )
            assert_stale_exemptions(
                self,
                (
                    _StaleSpec("blocked", True, True),
                    _StaleSpec("release-prep", True, False),
                    _StaleSpec("release-note", False, True),
                ),
                path=stale_path,
            )

    def test_load_stale_exempt_labels_reports_missing_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stale_path = Path(tmpdir) / "stale.yml"
            stale_path.write_text(
                "with:\n  exempt-issue-labels: blocked\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(AssertionError, "exempt-pr-labels"):
                load_stale_exempt_labels(stale_path)

    def test_load_and_assert_issue_form_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            form_path = Path(tmpdir) / "bug.yml"
            form_path.write_text(
                "\n".join(
                    (
                        "name: Bug report",
                        "labels:",
                        "  - bug",
                        "  - needs-info",
                        "body: []",
                    )
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                load_issue_form_labels(form_path),
                frozenset({"bug", "needs-info"}),
            )
            assert_issue_form_labels(
                self,
                {str(form_path): ("bug", "needs-info")},
            )

    def test_load_issue_form_labels_supports_inline_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            form_path = Path(tmpdir) / "release.yml"
            form_path.write_text(
                'name: Release\nlabels: ["maintenance", "release-prep"]\n',
                encoding="utf-8",
            )

            self.assertEqual(
                load_issue_form_labels(form_path),
                frozenset({"maintenance", "release-prep"}),
            )

    def test_load_issue_form_labels_reports_missing_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            form_path = Path(tmpdir) / "bug.yml"
            form_path.write_text("name: Bug report\n", encoding="utf-8")

            with self.assertRaisesRegex(AssertionError, "issue-form labels"):
                load_issue_form_labels(form_path)

    def test_load_and_assert_issue_form_metadata_and_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            form_path = Path(tmpdir) / "support.yml"
            form_path.write_text(
                "\n".join(
                    (
                        "name: Support request",
                        'title: "[Support] "',
                        "body:",
                        "  - type: checkboxes",
                        "    id: docs_checked",
                        "    attributes:",
                        "      label: What you already checked",
                        "      options:",
                        "        - label: README.md",
                        "          required: true",
                        "    validations:",
                        "      required: true",
                        "  - type: textarea",
                        "    id: question",
                        "    attributes:",
                        "      label: Question",
                        "    validations:",
                        "      required: true",
                        "  - type: textarea",
                        "    id: optional_context",
                        "    attributes:",
                        "      label: Optional context",
                        "    validations:",
                        "      required: false",
                    )
                ),
                encoding="utf-8",
            )

            metadata = load_issue_form_metadata(form_path)

            self.assertEqual(metadata.name, "Support request")
            self.assertEqual(metadata.title, "[Support] ")
            self.assertTrue(metadata.fields["docs_checked"].required)
            self.assertTrue(metadata.fields["question"].required)
            self.assertFalse(metadata.fields["optional_context"].required)
            self.assertEqual(
                metadata.fields["docs_checked"].options,
                frozenset({"README.md"}),
            )
            assert_issue_form_metadata(
                self,
                form_path,
                name="Support request",
                title="[Support] ",
            )
            assert_issue_form_fields(
                self,
                form_path,
                (
                    _IssueFormFieldSpec("question", "Question", True),
                    _IssueFormFieldSpec("optional_context", "Optional context", False),
                ),
            )
            assert_issue_form_checkbox_options(
                self,
                form_path,
                "docs_checked",
                ("README.md",),
            )

    def test_load_issue_form_metadata_reports_missing_top_level_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            form_path = Path(tmpdir) / "support.yml"
            form_path.write_text("name: Support request\nbody: []\n", encoding="utf-8")

            with self.assertRaisesRegex(AssertionError, "title"):
                load_issue_form_metadata(form_path)

    def test_load_and_assert_issue_template_contact_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(
                "\n".join(
                    (
                        "blank_issues_enabled: false",
                        "contact_links:",
                        "  - name: Support Expectations",
                        "    url: https://github.com/acme/project/blob/main/SUPPORT.md",
                        "    about: Read this before opening a usage question.",
                        "  - name: Security Policy",
                        "    url: SECURITY.md",
                        "    about: Report vulnerabilities privately.",
                    )
                ),
                encoding="utf-8",
            )
            links = load_issue_template_contact_links(config_path)

            self.assertEqual(
                links["Support Expectations"].url,
                "https://github.com/acme/project/blob/main/SUPPORT.md",
            )
            assert_issue_template_contact_links(
                self,
                (
                    _ContactLinkSpec(
                        "Support Expectations",
                        "SUPPORT.md",
                        "Read this before opening a usage question.",
                    ),
                    _ContactLinkSpec(
                        "Security Policy",
                        "SECURITY.md",
                        "Report vulnerabilities privately.",
                    ),
                ),
                path=config_path,
            )

    def test_load_issue_template_contact_links_reports_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(
                "\n".join(
                    (
                        "contact_links:",
                        "  - name: Support Expectations",
                        "    url: SUPPORT.md",
                    )
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(AssertionError, "about"):
                load_issue_template_contact_links(config_path)

    def test_load_issue_template_contact_links_reports_missing_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text("blank_issues_enabled: false\n", encoding="utf-8")

            with self.assertRaisesRegex(AssertionError, "contact_links"):
                load_issue_template_contact_links(config_path)

    def test_load_and_assert_release_note_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            release_path = Path(tmpdir) / "release.yml"
            release_path.write_text(
                "\n".join(
                    (
                        "changelog:",
                        "  exclude:",
                        "    labels:",
                        "      - support",
                        "      - invalid",
                        "  categories:",
                        "    - title: Features",
                        "      labels:",
                        "        - enhancement",
                        "        - release-note",
                        "    - title: Maintenance",
                        "      labels:",
                        "        - maintenance",
                    )
                ),
                encoding="utf-8",
            )
            config = load_release_note_config(release_path)

            self.assertEqual(config.excluded_labels, frozenset({"support", "invalid"}))
            self.assertEqual(config.categories[0].title, "Features")
            self.assertEqual(
                config.categories[0].labels,
                frozenset({"enhancement", "release-note"}),
            )
            assert_release_note_categories(
                self,
                {
                    "Features": ("enhancement", "release-note"),
                    "Maintenance": ("maintenance",),
                },
                path=release_path,
            )
            assert_release_note_excluded_labels(
                self,
                ("support", "invalid"),
                path=release_path,
            )

    def test_load_release_note_config_reports_missing_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            release_path = Path(tmpdir) / "release.yml"
            release_path.write_text("changelog:\n  exclude:\n", encoding="utf-8")

            with self.assertRaisesRegex(AssertionError, "changelog categories"):
                load_release_note_config(release_path)

    def test_snippet_assertions_support_normalized_and_literal_matching(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first_path = Path(tmpdir) / "first.md"
            second_path = Path(tmpdir) / "second.md"
            first_path.write_text("alpha\n  beta\n", encoding="utf-8")
            second_path.write_text("literal\nblock\n", encoding="utf-8")

            assert_file_contains_snippets(self, first_path, ("alpha beta",))
            assert_files_contain_snippets(
                self,
                {str(second_path): ("literal\nblock",)},
                normalize=False,
            )


class _StaleSpec:
    def __init__(
        self,
        label: str,
        stale_exempt_issues: bool,
        stale_exempt_prs: bool,
    ) -> None:
        self.label = label
        self.stale_exempt_issues = stale_exempt_issues
        self.stale_exempt_prs = stale_exempt_prs


class _ContactLinkSpec:
    def __init__(self, name: str, target: str, about: str) -> None:
        self.name = name
        self.target = target
        self.about = about


class _IssueFormFieldSpec:
    def __init__(self, key: str, label: str, required: bool) -> None:
        self.key = key
        self.label = label
        self.required = required


if __name__ == "__main__":
    unittest.main()
