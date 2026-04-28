from __future__ import annotations

import re
import unittest

from tools.docs_contracts import (
    DOCS_CHECKER_CONFIG,
    MAINTAINER_DOC_REGISTRY_CONTRACT,
    build_repository_reference_pattern,
    validate_docs_contract_schema,
)


class DocsContractTests(unittest.TestCase):
    def test_validate_docs_contract_schema_accepts_repository_contracts(
        self,
    ) -> None:
        self.assertEqual(validate_docs_contract_schema(), [])

    def test_maintainer_doc_registry_contract_uses_expected_sources(self) -> None:
        self.assertEqual(
            (
                MAINTAINER_DOC_REGISTRY_CONTRACT.readme_source.label,
                MAINTAINER_DOC_REGISTRY_CONTRACT.readme_source.path,
                MAINTAINER_DOC_REGISTRY_CONTRACT.readme_source.heading,
            ),
            ("README.md#Docs Map", "README.md", "Docs Map"),
        )
        self.assertEqual(
            (
                MAINTAINER_DOC_REGISTRY_CONTRACT.registry_source.label,
                MAINTAINER_DOC_REGISTRY_CONTRACT.registry_source.path,
                MAINTAINER_DOC_REGISTRY_CONTRACT.registry_source.heading,
            ),
            (
                "docs/maintainer-operations-hub.md#Source-Of-Truth Map",
                "docs/maintainer-operations-hub.md",
                "Source-Of-Truth Map",
            ),
        )
        self.assertEqual(
            (
                MAINTAINER_DOC_REGISTRY_CONTRACT.guide_source.label,
                MAINTAINER_DOC_REGISTRY_CONTRACT.guide_source.path,
                MAINTAINER_DOC_REGISTRY_CONTRACT.guide_source.heading,
            ),
            (
                "docs/maintainer-guide.md#Governance Documents",
                "docs/maintainer-guide.md",
                "Governance Documents",
            ),
        )
        self.assertEqual(
            MAINTAINER_DOC_REGISTRY_CONTRACT.required_readme_targets,
            ("docs/maintainer-operations-hub.md",),
        )

    def test_docs_checker_config_uses_expected_repository_boundaries(
        self,
    ) -> None:
        self.assertEqual(
            DOCS_CHECKER_CONFIG.root_reference_files,
            (
                ".pre-commit-config.yaml",
                "CHANGELOG.md",
                "CODE_OF_CONDUCT.md",
                "CONTRIBUTING.md",
                "GOVERNANCE.md",
                "LICENSE",
                "Makefile",
                "README.md",
                "RELEASING.md",
                "SECURITY.md",
                "SUPPORT.md",
                "config.example.toml",
                "pyproject.toml",
            ),
        )
        self.assertEqual(
            DOCS_CHECKER_CONFIG.repository_reference_roots,
            ("docs", ".github", "paper_digest", "tools", "tests"),
        )
        self.assertEqual(
            DOCS_CHECKER_CONFIG.repository_reference_literals,
            (".github/CODEOWNERS",),
        )
        self.assertEqual(
            DOCS_CHECKER_CONFIG.github_metadata_root,
            ".github",
        )
        self.assertEqual(
            DOCS_CHECKER_CONFIG.github_metadata_globs,
            ("*.yml", "*.yaml"),
        )
        self.assertIn(".venv", DOCS_CHECKER_CONFIG.skip_dirs)
        self.assertIn("dist", DOCS_CHECKER_CONFIG.skip_dirs)
        self.assertIn("reports", DOCS_CHECKER_CONFIG.skip_dirs)

    def test_build_repository_reference_pattern_matches_expected_targets(self) -> None:
        pattern = re.compile(build_repository_reference_pattern(DOCS_CHECKER_CONFIG))
        for target in (
            "README.md",
            "./docs/guide.md#overview",
            ".github/CODEOWNERS",
            "tools/check_docs.py",
            "tests/test_docs_contracts.py",
        ):
            self.assertIsNotNone(pattern.search(target), target)
        self.assertIsNone(pattern.search("docs"))
        self.assertIsNone(pattern.search("scripts/bootstrap.sh"))


if __name__ == "__main__":
    unittest.main()
