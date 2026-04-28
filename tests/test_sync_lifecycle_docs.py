from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.lifecycle_contracts import GeneratedManagedBlock
from tools.sync_lifecycle_docs import replace_generated_block, sync_lifecycle_docs


class SyncLifecycleDocsTests(unittest.TestCase):
    def test_replace_generated_block_rewrites_managed_region(self) -> None:
        original = textwrap.dedent(
            """\
            Before
            <!-- BEGIN GENERATED: example -->
            stale
            <!-- END GENERATED: example -->
            After
            """
        )

        updated, changed = replace_generated_block(
            original,
            GeneratedManagedBlock(
                path="docs/example.md",
                marker="example",
                content="fresh",
            ),
        )

        self.assertTrue(changed)
        self.assertIn(
            "\n".join(
                [
                    "<!-- BEGIN GENERATED: example -->",
                    "fresh",
                    "<!-- END GENERATED: example -->",
                ]
            ),
            updated,
        )

    def test_sync_lifecycle_docs_check_reports_stale_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            doc = root / "docs" / "example.md"
            doc.parent.mkdir(parents=True)
            doc.write_text(
                textwrap.dedent(
                    """\
                    <!-- BEGIN GENERATED: example -->
                    stale
                    <!-- END GENERATED: example -->
                    """
                ),
                encoding="utf-8",
            )

            errors = sync_lifecycle_docs(
                root,
                check=True,
                blocks=(
                    GeneratedManagedBlock(
                        path="docs/example.md",
                        marker="example",
                        content="fresh",
                    ),
                ),
            )

            self.assertEqual(
                errors,
                [
                    (
                        "docs/example.md: managed lifecycle blocks are "
                        "out of date; run `python tools/sync_lifecycle_docs.py`"
                    )
                ],
            )

    def test_sync_lifecycle_docs_updates_files_when_not_checking(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            doc = root / "docs" / "example.md"
            doc.parent.mkdir(parents=True)
            doc.write_text(
                textwrap.dedent(
                    """\
                    <!-- BEGIN GENERATED: example -->
                    stale
                    <!-- END GENERATED: example -->
                    """
                ),
                encoding="utf-8",
            )

            errors = sync_lifecycle_docs(
                root,
                check=False,
                blocks=(
                    GeneratedManagedBlock(
                        path="docs/example.md",
                        marker="example",
                        content="fresh",
                    ),
                ),
            )

            self.assertEqual(errors, [])
            self.assertEqual(
                doc.read_text(encoding="utf-8"),
                textwrap.dedent(
                    """\
                    <!-- BEGIN GENERATED: example -->
                    fresh
                    <!-- END GENERATED: example -->
                    """
                ),
            )

    def test_replace_generated_block_supports_custom_marker_styles(self) -> None:
        original = "\n".join(
            [
                "      # BEGIN GENERATED: example",
                "      value: |",
                "        stale",
                "      # END GENERATED: example",
            ]
        )

        updated, changed = replace_generated_block(
            original,
            GeneratedManagedBlock(
                path=".github/ISSUE_TEMPLATE/example.yml",
                marker="example",
                content="      value: |\n        fresh",
                begin_marker_override="      # BEGIN GENERATED: example",
                end_marker_override="      # END GENERATED: example",
            ),
        )

        self.assertTrue(changed)
        self.assertEqual(
            updated,
            "\n".join(
                [
                    "      # BEGIN GENERATED: example",
                    "      value: |",
                    "        fresh",
                    "      # END GENERATED: example",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
