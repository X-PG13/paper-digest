from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FileTextSource:
    label: str
    path: str


@dataclass(frozen=True)
class MarkdownSectionSource:
    label: str
    path: str
    heading: str
    visible_only: bool = True


@dataclass(frozen=True)
class WorkflowSectionSource:
    label: str
    path: str
    section: str | None = None


TextSource = FileTextSource | MarkdownSectionSource | WorkflowSectionSource


@dataclass(frozen=True)
class MaintainerDocRegistryContract:
    readme_source: MarkdownSectionSource
    registry_source: MarkdownSectionSource
    guide_source: MarkdownSectionSource
    required_readme_targets: tuple[str, ...]


@dataclass(frozen=True)
class DocsCheckerConfig:
    root_reference_files: tuple[str, ...]
    repository_reference_roots: tuple[str, ...]
    repository_reference_literals: tuple[str, ...]
    skip_dirs: frozenset[str]
    github_metadata_root: str
    github_metadata_globs: tuple[str, ...]


README_DOCS_MAP_SOURCE = MarkdownSectionSource(
    label="README.md#Docs Map",
    path="README.md",
    heading="Docs Map",
)
MAINTAINER_HUB_SOURCE_OF_TRUTH_SOURCE = MarkdownSectionSource(
    label="docs/maintainer-operations-hub.md#Source-Of-Truth Map",
    path="docs/maintainer-operations-hub.md",
    heading="Source-Of-Truth Map",
)
MAINTAINER_GUIDE_GOVERNANCE_SOURCE = MarkdownSectionSource(
    label="docs/maintainer-guide.md#Governance Documents",
    path="docs/maintainer-guide.md",
    heading="Governance Documents",
)

MAINTAINER_DOC_REGISTRY_CONTRACT = MaintainerDocRegistryContract(
    readme_source=README_DOCS_MAP_SOURCE,
    registry_source=MAINTAINER_HUB_SOURCE_OF_TRUTH_SOURCE,
    guide_source=MAINTAINER_GUIDE_GOVERNANCE_SOURCE,
    required_readme_targets=("docs/maintainer-operations-hub.md",),
)

DOCS_CHECKER_CONFIG = DocsCheckerConfig(
    root_reference_files=(
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
    repository_reference_roots=(
        "docs",
        ".github",
        "paper_digest",
        "tools",
        "tests",
    ),
    repository_reference_literals=(".github/CODEOWNERS",),
    skip_dirs=frozenset(
        {
            ".git",
            ".mypy_cache",
            ".paper-digest-state",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "dist",
            "output",
            "reports",
        }
    ),
    github_metadata_root=".github",
    github_metadata_globs=("*.yml", "*.yaml"),
)


def build_repository_reference_pattern(config: DocsCheckerConfig) -> str:
    repository_roots = "|".join(
        re.escape(root) for root in config.repository_reference_roots
    )
    repository_literals = "|".join(
        re.escape(path) for path in config.repository_reference_literals
    )
    root_files = "|".join(re.escape(name) for name in config.root_reference_files)
    literal_branch = (
        f"|{repository_literals}" if repository_literals else ""
    )
    return (
        r"(?P<target>"
        r"(?:\./)?(?:"
        r"(?:"
        + repository_roots
        + r")/(?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]+"
        + literal_branch
        + r"|"
        + root_files
        + r")"
        r"(?:#[A-Za-z0-9._-]+)?"
        r")"
    )


def _validate_markdown_source(
    collection_name: str,
    source: MarkdownSectionSource,
) -> list[str]:
    errors: list[str] = []
    if not source.label:
        errors.append(f"{collection_name}: empty source label")
    if not source.path:
        errors.append(f"{collection_name}: empty source path for {source.label}")
    if not source.heading:
        errors.append(f"{collection_name}: empty heading for {source.label}")
    return errors


def _validate_string_collection(
    collection_name: str,
    values: tuple[str, ...] | frozenset[str],
) -> list[str]:
    errors: list[str] = []
    normalized_values = tuple(values)
    if not normalized_values:
        errors.append(f"{collection_name}: empty collection")
        return errors
    if len(normalized_values) != len(set(normalized_values)):
        errors.append(f"{collection_name}: duplicate values")
    if any(not value for value in normalized_values):
        errors.append(f"{collection_name}: empty value")
    return errors


def validate_docs_contract_schema() -> list[str]:
    errors: list[str] = []
    sources = (
        MAINTAINER_DOC_REGISTRY_CONTRACT.readme_source,
        MAINTAINER_DOC_REGISTRY_CONTRACT.registry_source,
        MAINTAINER_DOC_REGISTRY_CONTRACT.guide_source,
    )
    labels = [source.label for source in sources]
    if len(labels) != len(set(labels)):
        errors.append("maintainer doc registry contract: duplicate source labels")
    for source in sources:
        errors.extend(
            _validate_markdown_source(
                "maintainer doc registry contract",
                source,
            )
        )

    required_targets = MAINTAINER_DOC_REGISTRY_CONTRACT.required_readme_targets
    if not required_targets:
        errors.append("maintainer doc registry contract: no required README targets")
    if len(required_targets) != len(set(required_targets)):
        errors.append(
            "maintainer doc registry contract: duplicate required README targets"
        )
    if any(not target for target in required_targets):
        errors.append(
            "maintainer doc registry contract: empty required README target"
        )

    errors.extend(
        _validate_string_collection(
            "docs checker root reference files",
            DOCS_CHECKER_CONFIG.root_reference_files,
        )
    )
    errors.extend(
        _validate_string_collection(
            "docs checker repository reference roots",
            DOCS_CHECKER_CONFIG.repository_reference_roots,
        )
    )
    errors.extend(
        _validate_string_collection(
            "docs checker repository reference literals",
            DOCS_CHECKER_CONFIG.repository_reference_literals,
        )
    )
    errors.extend(
        _validate_string_collection(
            "docs checker skip dirs",
            DOCS_CHECKER_CONFIG.skip_dirs,
        )
    )
    if not DOCS_CHECKER_CONFIG.github_metadata_root:
        errors.append("docs checker config: empty github metadata root")
    errors.extend(
        _validate_string_collection(
            "docs checker github metadata globs",
            DOCS_CHECKER_CONFIG.github_metadata_globs,
        )
    )

    return errors
