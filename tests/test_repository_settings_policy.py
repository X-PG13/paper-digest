from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.repository_settings_policy import (
    ADVISORY_STATUS_CHECKS,
    REPOSITORY_SETTINGS_DOC_LINKS,
    REQUIRED_STATUS_CHECK_DOCS,
    REQUIRED_STATUS_CHECKS,
    advisory_status_check_names,
    pr_facing_status_check_names,
    required_status_check_contexts,
    required_status_check_names,
    required_status_check_workflow_paths,
    validate_repository_settings_policy,
)


class RepositorySettingsPolicyTests(unittest.TestCase):
    def test_repository_settings_policy_accepts_current_repository(self) -> None:
        self.assertEqual(validate_repository_settings_policy(), ())

    def test_required_status_checks_have_unique_names_and_workflows(self) -> None:
        self.assertEqual(
            required_status_check_names(),
            ("CI", "Dependency Review", "Workflow Lint"),
        )
        self.assertEqual(advisory_status_check_names(), ("PR Hygiene",))
        self.assertEqual(
            pr_facing_status_check_names(),
            ("CI", "Dependency Review", "Workflow Lint", "PR Hygiene"),
        )
        self.assertEqual(
            required_status_check_contexts(),
            ("verify / verify", "dependency-review", "actionlint"),
        )
        self.assertEqual(
            len(required_status_check_names()),
            len(set(required_status_check_names())),
        )
        self.assertEqual(
            len(required_status_check_contexts()),
            len(set(required_status_check_contexts())),
        )
        self.assertEqual(
            len(required_status_check_workflow_paths()),
            len(set(required_status_check_workflow_paths())),
        )

    def test_repository_settings_docs_share_required_check_names_and_contexts(
        self,
    ) -> None:
        for doc_path in REQUIRED_STATUS_CHECK_DOCS:
            with self.subTest(path=doc_path):
                text = Path(doc_path).read_text(encoding="utf-8")
                for check_name in required_status_check_names():
                    self.assertIn(f"`{check_name}`", text)
                for check_context in required_status_check_contexts():
                    self.assertIn(f"`{check_context}`", text)
                for check_name in advisory_status_check_names():
                    self.assertIn(f"`{check_name}`", text)

    def test_repository_settings_docs_keep_cross_links(self) -> None:
        for doc_path, required_links in REPOSITORY_SETTINGS_DOC_LINKS.items():
            with self.subTest(path=doc_path):
                text = Path(doc_path).read_text(encoding="utf-8")
                for required_link in required_links:
                    self.assertIn(required_link, text)

    def test_required_check_workflows_keep_expected_names_and_pr_triggers(
        self,
    ) -> None:
        for check in REQUIRED_STATUS_CHECKS + ADVISORY_STATUS_CHECKS:
            with self.subTest(workflow=check.workflow_path):
                text = Path(check.workflow_path).read_text(encoding="utf-8")
                self.assertIn(f"name: {check.workflow_name}", text)
                self.assertIn(check.trigger, text)

    def test_validator_reports_missing_doc_check_and_workflow_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_minimal_policy_tree(root)
            (root / "docs/branch-protection-policy.md").write_text(
                textwrap.dedent(
                    """\
                    # Branch Protection Policy

                    Requires `CI` and `Dependency Review`.
                    Contexts: `verify / verify`, `dependency-review`.
                    Advisory: `PR Hygiene`.
                    See docs/review-policy.md,
                    docs/repository-settings-checklist.md, and
                    docs/ruleset-policy.md.
                    """
                ),
                encoding="utf-8",
            )
            (root / ".github/workflows/ci.yml").write_text(
                textwrap.dedent(
                    """\
                    name: Tests
                    on:
                      workflow_dispatch:
                    """
                ),
                encoding="utf-8",
            )

            errors = validate_repository_settings_policy(root)

        self.assertIn(
            ".github/workflows/ci.yml: workflow name must be `CI`",
            errors,
        )
        self.assertIn(
            ".github/workflows/ci.yml: missing trigger `pull_request:`",
            errors,
        )
        self.assertIn(
            "docs/branch-protection-policy.md: missing required status check "
            "`Workflow Lint`",
            errors,
        )
        self.assertIn(
            "docs/branch-protection-policy.md: missing required status check "
            "context `actionlint`",
            errors,
        )

    def _write_minimal_policy_tree(self, root: Path) -> None:
        workflows = root / ".github" / "workflows"
        docs = root / "docs"
        workflows.mkdir(parents=True)
        docs.mkdir()

        required_checks = ", ".join(
            f"`{check_name}`" for check_name in required_status_check_names()
        )
        required_contexts = ", ".join(
            f"`{check_context}`" for check_context in required_status_check_contexts()
        )
        advisory_checks = ", ".join(
            f"`{check_name}`" for check_name in advisory_status_check_names()
        )
        for doc_path, required_links in REPOSITORY_SETTINGS_DOC_LINKS.items():
            path = root / doc_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"# {path.stem}\n\nRequires {required_checks}.\n"
                f"Contexts {required_contexts}.\n"
                f"Advisory {advisory_checks}.\n"
                + "\n".join(required_links)
                + "\n",
                encoding="utf-8",
            )

        for check in REQUIRED_STATUS_CHECKS + ADVISORY_STATUS_CHECKS:
            (root / check.workflow_path).write_text(
                textwrap.dedent(
                    f"""\
                    name: {check.workflow_name}
                    on:
                      {check.trigger}
                    """
                ),
                encoding="utf-8",
            )


if __name__ == "__main__":
    unittest.main()
