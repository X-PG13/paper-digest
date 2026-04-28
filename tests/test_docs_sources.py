from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.docs_contracts import (
    FileTextSource,
    MarkdownSectionSource,
    WorkflowSectionSource,
)
from tools.docs_findings import DocsCheckFinding
from tools.docs_sources import (
    TextSourceOrigin,
    collect_text_by_label,
    collect_text_source_origins,
    find_text_source_origin,
    get_workflow_body_parts,
    get_workflow_section_lines,
    read_markdown_section_lines,
    read_markdown_section_text,
    read_text_from_source,
    resolve_repository_path,
)


class DocsSourcesTests(unittest.TestCase):
    def test_resolve_repository_path_joins_root_and_relative_path(self) -> None:
        root = Path("/tmp/example-root")
        self.assertEqual(
            resolve_repository_path(root, "docs/guide.md"),
            root / "docs/guide.md",
        )

    def test_read_markdown_section_helpers_cover_present_and_missing_sections(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            page = Path(tmpdir, "README.md")
            page.write_text(
                textwrap.dedent(
                    """\
                    # Title

                    ## Docs Map
                    - one
                    - two
                    """
                ),
                encoding="utf-8",
            )

            errors: list[DocsCheckFinding] = []
            self.assertEqual(
                read_markdown_section_lines(page, "Docs Map", errors),
                ["- one", "- two"],
            )
            self.assertEqual(
                read_markdown_section_text(page, "Docs Map", errors),
                "- one\n- two",
            )
            self.assertIsNone(
                read_markdown_section_text(
                    page,
                    "Missing",
                    errors,
                    label="README.md",
                )
            )
            self.assertEqual(
                errors,
                [
                    DocsCheckFinding(
                        message="missing section 'Missing'",
                        path="README.md",
                    )
                ],
            )

    def test_workflow_source_helpers_cover_intro_section_and_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workflow = root / ".github" / "workflows" / "quarterly.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "Intro line.",
                      "## Summary",
                      "- Field: value",
                    ];
                    """
                ),
                encoding="utf-8",
            )

            cache: dict[str, tuple[list[str], dict[str, list[str]]]] = {}
            source = WorkflowSectionSource(
                label="workflow summary",
                path=".github/workflows/quarterly.yml",
                section="Summary",
            )
            intro, sections = get_workflow_body_parts(root, source, cache)

            self.assertEqual(intro, ["Intro line."])
            self.assertEqual(sections["Summary"], ["- Field: value"])
            self.assertIn(source.path, cache)
            self.assertEqual(
                get_workflow_section_lines(
                    root,
                    WorkflowSectionSource(
                        label="workflow intro",
                        path=".github/workflows/quarterly.yml",
                    ),
                ),
                ["Intro line."],
            )
            self.assertEqual(
                get_workflow_section_lines(root, source),
                ["- Field: value"],
            )

    def test_text_source_origin_helpers_cover_file_markdown_and_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "RELEASING.md").write_text("# Releasing\n", encoding="utf-8")
            guide = root / "docs" / "guide.md"
            guide.parent.mkdir()
            guide.write_text(
                textwrap.dedent(
                    """\
                    # Guide

                    ## Summary
                    - One
                    """
                ),
                encoding="utf-8",
            )
            workflow = root / ".github" / "workflows" / "post-release.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "Intro line.",
                      "## Follow-Up",
                      "- Release: vX.Y.Z",
                    ];
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                find_text_source_origin(
                    root,
                    FileTextSource(label="release file", path="RELEASING.md"),
                ),
                TextSourceOrigin(path="RELEASING.md", line=1, end_line=1),
            )
            self.assertEqual(
                find_text_source_origin(
                    root,
                    MarkdownSectionSource(
                        label="guide summary",
                        path="docs/guide.md",
                        heading="Summary",
                    ),
                ),
                TextSourceOrigin(path="docs/guide.md", line=3, end_line=4),
            )
            self.assertEqual(
                find_text_source_origin(
                    root,
                    WorkflowSectionSource(
                        label="workflow follow-up",
                        path=".github/workflows/post-release.yml",
                        section="Follow-Up",
                    ),
                ),
                TextSourceOrigin(
                    path=".github/workflows/post-release.yml",
                    line=3,
                    end_line=4,
                ),
            )
            self.assertEqual(
                collect_text_source_origins(
                    root,
                    (
                        FileTextSource(label="release file", path="RELEASING.md"),
                        MarkdownSectionSource(
                            label="guide summary",
                            path="docs/guide.md",
                            heading="Summary",
                        ),
                    ),
                ),
                {
                    "release file": TextSourceOrigin(
                        path="RELEASING.md",
                        line=1,
                        end_line=1,
                    ),
                    "guide summary": TextSourceOrigin(
                        path="docs/guide.md",
                        line=3,
                        end_line=4,
                    ),
                },
            )

    def test_read_text_from_source_and_collect_text_by_label_cover_all_source_types(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "RELEASING.md").write_text(
                "# Releasing\n",
                encoding="utf-8",
            )
            guide = root / "docs" / "guide.md"
            guide.parent.mkdir()
            guide.write_text(
                textwrap.dedent(
                    """\
                    # Guide

                    ## Summary
                    - One
                    """
                ),
                encoding="utf-8",
            )
            workflow = root / ".github" / "workflows" / "post-release.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "Intro line.",
                      "## Follow-Up",
                      "- Release: vX.Y.Z",
                    ];
                    """
                ),
                encoding="utf-8",
            )

            errors: list[DocsCheckFinding] = []
            workflow_cache: dict[str, tuple[list[str], dict[str, list[str]]]] = {}
            self.assertEqual(
                read_text_from_source(
                    root,
                    FileTextSource(label="release file", path="RELEASING.md"),
                    errors,
                    workflow_cache,
                ),
                "# Releasing\n",
            )
            self.assertEqual(
                read_text_from_source(
                    root,
                    MarkdownSectionSource(
                        label="guide summary",
                        path="docs/guide.md",
                        heading="Summary",
                    ),
                    errors,
                    workflow_cache,
                ),
                "- One",
            )
            self.assertEqual(
                read_text_from_source(
                    root,
                    MarkdownSectionSource(
                        label="missing summary",
                        path="docs/guide.md",
                        heading="Missing",
                    ),
                    errors,
                    workflow_cache,
                ),
                "",
            )
            self.assertEqual(
                read_text_from_source(
                    root,
                    WorkflowSectionSource(
                        label="workflow follow-up",
                        path=".github/workflows/post-release.yml",
                        section="Follow-Up",
                    ),
                    errors,
                    workflow_cache,
                ),
                "- Release: vX.Y.Z",
            )

            collected = collect_text_by_label(
                root,
                [
                    FileTextSource(label="release file", path="RELEASING.md"),
                    MarkdownSectionSource(
                        label="guide summary",
                        path="docs/guide.md",
                        heading="Summary",
                    ),
                    WorkflowSectionSource(
                        label="workflow intro",
                        path=".github/workflows/post-release.yml",
                    ),
                    WorkflowSectionSource(
                        label="workflow follow-up",
                        path=".github/workflows/post-release.yml",
                        section="Follow-Up",
                    ),
                ],
                [],
            )

            self.assertEqual(
                collected,
                {
                    "release file": "# Releasing\n",
                    "guide summary": "- One",
                    "workflow intro": "Intro line.",
                    "workflow follow-up": "- Release: vX.Y.Z",
                },
            )
            self.assertEqual(
                errors,
                [
                    DocsCheckFinding(
                        message="missing section 'Missing'",
                        path="docs/guide.md",
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()
