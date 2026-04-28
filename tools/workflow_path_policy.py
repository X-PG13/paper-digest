from __future__ import annotations

PUBLIC_DOC_ROOTS = {
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "RELEASING.md",
    "CODE_OF_CONDUCT.md",
    "GOVERNANCE.md",
    "config.example.toml",
}

RUNTIME_OR_OPS_ROOTS = {
    ".github/dependabot.yml",
    ".github/release.yml",
    ".github/labels.json",
    ".github/pull_request_template.md",
    ".github/CODEOWNERS",
    "pyproject.toml",
    "Makefile",
}

MAINTENANCE_ROOTS = {
    "Makefile",
    "pyproject.toml",
}

GOVERNANCE_PATHS = {
    "GOVERNANCE.md",
    "docs/roadmap-policy.md",
    "docs/discussions-policy.md",
    "docs/maintainer-rotation.md",
    "docs/review-policy.md",
    "docs/branch-protection-policy.md",
}


def is_public_doc_path(path: str) -> bool:
    return (
        path.startswith("docs/")
        or path.startswith(".github/ISSUE_TEMPLATE/")
        or path in PUBLIC_DOC_ROOTS
    )


def is_changelog_path(path: str) -> bool:
    return path == "CHANGELOG.md"


def is_test_path(path: str) -> bool:
    return path.startswith("tests/")


def is_runtime_or_ops_path(path: str) -> bool:
    return (
        path.startswith("paper_digest/")
        or path.startswith(".github/workflows/")
        or path in RUNTIME_OR_OPS_ROOTS
    )


def is_maintenance_path(path: str) -> bool:
    return path.startswith(".github/") or path in MAINTENANCE_ROOTS


def is_governance_path(path: str) -> bool:
    return path in GOVERNANCE_PATHS or path.startswith("docs/adr/")
