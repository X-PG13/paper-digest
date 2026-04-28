from __future__ import annotations

import unittest
from pathlib import Path

from tests.workflow_assertions import (
    extract_indented_block,
    extract_step_block,
    load_workflow_lines,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = ".github/workflows/release.yml"


class ReleaseDryRunContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = load_workflow_lines(RELEASE_WORKFLOW)

    def test_makefile_exposes_composed_release_dry_run_target(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("release-dry-run", makefile)
        self.assertIn("release-dry-run: check build release-check", makefile)

    def test_release_docs_and_release_prep_form_surface_dry_run(self) -> None:
        for relative_path in (
            "CONTRIBUTING.md",
            "RELEASING.md",
            ".github/ISSUE_TEMPLATE/release_preparation.yml",
        ):
            with self.subTest(path=relative_path):
                text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("make release-dry-run", text)

    def test_release_workflow_dispatch_defaults_to_dry_run(self) -> None:
        block = extract_indented_block(self.lines, "      dry_run:")

        self.assertIn(
            "        description: Build and validate release artifacts without "
            "publishing.",
            block,
        )
        self.assertIn("        required: false", block)
        self.assertIn("        type: boolean", block)
        self.assertIn("        default: true", block)

    def test_release_workflow_builds_package_dist_artifact(self) -> None:
        block = extract_indented_block(self.lines, "  build:")

        self.assertIn("    uses: ./.github/workflows/reusable-python-checks.yml", block)
        self.assertIn("      upload_dist: true", block)
        self.assertIn("      contents: read", block)

    def test_release_workflow_dry_run_downloads_and_validates_artifacts(self) -> None:
        job_block = extract_indented_block(self.lines, "  dry-run:")
        download_block = extract_step_block(self.lines, "Download dry-run artifacts")
        verify_block = extract_step_block(self.lines, "Verify dry-run artifacts")

        self.assertIn("    needs: build", job_block)
        self.assertIn(
            "    if: github.event_name == 'workflow_dispatch' && inputs.dry_run",
            job_block,
        )
        self.assertIn("      contents: read", job_block)
        self.assertIn("        uses: actions/download-artifact@v5", download_block)
        self.assertIn("          name: package-dist", download_block)
        self.assertIn("          path: dist", download_block)
        self.assertIn("find dist -maxdepth 1 -name '*.whl'", verify_block)
        self.assertIn("find dist -maxdepth 1 -name '*.tar.gz'", verify_block)
        self.assertIn("Release dry run", verify_block)
        self.assertIn("$GITHUB_STEP_SUMMARY", verify_block)

    def test_release_publish_job_is_tag_and_explicit_publish_gated(self) -> None:
        job_block = extract_indented_block(self.lines, "  publish:")
        release_block = extract_step_block(self.lines, "Create GitHub release")

        self.assertIn("    needs: build", job_block)
        self.assertIn("startsWith(github.ref, 'refs/tags/')", job_block)
        self.assertIn("github.event_name == 'push'", job_block)
        self.assertIn("inputs.dry_run == false", job_block)
        self.assertIn("      contents: write", job_block)
        self.assertIn("        if: startsWith(github.ref, 'refs/tags/')", release_block)
        self.assertIn("gh release create", release_block)
        self.assertIn("gh release upload", release_block)


if __name__ == "__main__":
    unittest.main()
