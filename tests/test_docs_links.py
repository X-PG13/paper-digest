from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.docs_links import (
    check_markdown_links,
    check_repository_references,
    extract_markdown_link_targets_from_lines,
    extract_repository_reference_targets_from_lines,
)


class DocsLinksTests(unittest.TestCase):
    def test_extract_markdown_link_targets_from_lines_normalizes_targets(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "README.md"
            source.write_text("# Home\n", encoding="utf-8")

            targets = extract_markdown_link_targets_from_lines(
                root,
                source,
                [
                    "[Guide](./docs/guide.md#section)",
                    "[Policy](/docs/review-policy.md)",
                    "[Mail](mailto:test@example.com)",
                ],
            )

            self.assertEqual(
                targets,
                {"docs/guide.md", "docs/review-policy.md"},
            )

    def test_extract_repository_reference_targets_from_lines_strips_dots_and_anchors(
        self,
    ) -> None:
        targets = extract_repository_reference_targets_from_lines(
            [
                "Use `./docs/guide.md#section` and `README.md`.",
                "Repeat `README.md` once more.",
            ]
        )

        self.assertEqual(targets, {"docs/guide.md", "README.md"})

    def test_check_markdown_links_reports_missing_file_and_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "README.md"
            target = root / "docs" / "guide.md"
            target.parent.mkdir()
            source.write_text(
                textwrap.dedent(
                    """\
                    [missing file](./docs/missing.md)
                    [missing anchor](./docs/guide.md#nope)
                    """
                ),
                encoding="utf-8",
            )
            target.write_text("# Guide\n", encoding="utf-8")

            errors = check_markdown_links(root, [source, target])

            self.assertEqual(
                errors[0].message,
                "missing target: ./docs/missing.md",
            )
            self.assertEqual(errors[0].path, "README.md")
            self.assertEqual(errors[0].line, 1)
            self.assertEqual(
                errors[1].message,
                "missing anchor 'nope' in docs/guide.md",
            )
            self.assertEqual(errors[1].path, "README.md")
            self.assertEqual(errors[1].line, 2)

    def test_check_markdown_links_accepts_root_relative_and_same_file_anchors(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs = root / "docs"
            docs.mkdir()
            readme = root / "README.md"
            guide = docs / "guide.md"
            readme.write_text(
                textwrap.dedent(
                    """\
                    # Home

                    [Guide](/docs/guide.md#section)
                    [Home](#home)
                    """
                ),
                encoding="utf-8",
            )
            guide.write_text(
                textwrap.dedent(
                    """\
                    # Guide
                    ## Section
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(check_markdown_links(root, [readme, guide]), [])

    def test_check_repository_references_reports_missing_file_and_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata = root / ".github" / "ISSUE_TEMPLATE" / "release.yml"
            guide = root / "docs" / "guide.md"
            metadata.parent.mkdir(parents=True)
            guide.parent.mkdir()
            metadata.write_text(
                textwrap.dedent(
                    """\
                    description: Use `docs/missing.md`
                    description: and `docs/guide.md#missing-anchor`.
                    """
                ),
                encoding="utf-8",
            )
            guide.write_text("# Guide\n", encoding="utf-8")

            errors = check_repository_references(root, [metadata])

            self.assertEqual(
                errors[0].message,
                "missing repository file: docs/missing.md",
            )
            self.assertEqual(errors[0].path, ".github/ISSUE_TEMPLATE/release.yml")
            self.assertEqual(errors[0].line, 1)
            self.assertEqual(
                errors[1].message,
                "missing anchor 'missing-anchor' in docs/guide.md",
            )
            self.assertEqual(errors[1].path, ".github/ISSUE_TEMPLATE/release.yml")
            self.assertEqual(errors[1].line, 2)

    def test_check_repository_references_accepts_existing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata = root / ".github" / "workflows" / "release.yml"
            guide = root / "docs" / "guide.md"
            readme = root / "README.md"
            codeowners = root / ".github" / "CODEOWNERS"
            metadata.parent.mkdir(parents=True)
            guide.parent.mkdir()
            metadata.write_text(
                textwrap.dedent(
                    """\
                    description: |
                      Use `docs/guide.md#section`, `README.md`,
                      and `.github/CODEOWNERS`.
                    """
                ),
                encoding="utf-8",
            )
            guide.write_text("# Guide\n## Section\n", encoding="utf-8")
            readme.write_text("# Home\n", encoding="utf-8")
            codeowners.write_text("* @maintainer\n", encoding="utf-8")

            self.assertEqual(check_repository_references(root, [metadata]), [])
