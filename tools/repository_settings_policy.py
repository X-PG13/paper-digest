from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RequiredStatusCheckSpec:
    name: str
    workflow_path: str
    workflow_name: str
    trigger: str
    check_context: str


REQUIRED_STATUS_CHECKS = (
    RequiredStatusCheckSpec(
        name="CI",
        workflow_path=".github/workflows/ci.yml",
        workflow_name="CI",
        trigger="pull_request:",
        check_context="verify / verify",
    ),
    RequiredStatusCheckSpec(
        name="Dependency Review",
        workflow_path=".github/workflows/dependency-review.yml",
        workflow_name="Dependency Review",
        trigger="pull_request:",
        check_context="dependency-review",
    ),
    RequiredStatusCheckSpec(
        name="Workflow Lint",
        workflow_path=".github/workflows/workflow-lint.yml",
        workflow_name="Workflow Lint",
        trigger="pull_request:",
        check_context="actionlint",
    ),
)

ADVISORY_STATUS_CHECKS = (
    RequiredStatusCheckSpec(
        name="PR Hygiene",
        workflow_path=".github/workflows/pr-hygiene.yml",
        workflow_name="PR Hygiene",
        trigger="pull_request_target:",
        check_context="hygiene",
    ),
)

PR_FACING_STATUS_CHECKS = REQUIRED_STATUS_CHECKS + ADVISORY_STATUS_CHECKS

REQUIRED_STATUS_CHECK_DOCS = (
    "docs/branch-protection-policy.md",
    "docs/repository-settings-checklist.md",
    "docs/ruleset-policy.md",
)

REPOSITORY_SETTINGS_DOC_LINKS = {
    "docs/branch-protection-policy.md": (
        "docs/review-policy.md",
        "docs/repository-settings-checklist.md",
        "docs/ruleset-policy.md",
    ),
    "docs/repository-settings-checklist.md": (
        "docs/branch-protection-policy.md",
        "docs/ruleset-policy.md",
        "docs/quarterly-maintainer-review.md",
    ),
    "docs/ruleset-policy.md": (
        "docs/branch-protection-policy.md",
        "docs/repository-settings-checklist.md",
    ),
}


def _strip_yaml_scalar_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "'\"":
        return stripped[1:-1]
    return stripped


def _read_text(root: Path, relative_path: str) -> str | None:
    path = root / relative_path
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _extract_workflow_name(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("name:"):
            return _strip_yaml_scalar_quotes(line.removeprefix("name:"))
    return None


def _contains_workflow_trigger(text: str, trigger: str) -> bool:
    return any(line.strip() == trigger for line in text.splitlines())


def required_status_check_names() -> tuple[str, ...]:
    return tuple(check.name for check in REQUIRED_STATUS_CHECKS)


def advisory_status_check_names() -> tuple[str, ...]:
    return tuple(check.name for check in ADVISORY_STATUS_CHECKS)


def pr_facing_status_check_names() -> tuple[str, ...]:
    return tuple(check.name for check in PR_FACING_STATUS_CHECKS)


def required_status_check_contexts() -> tuple[str, ...]:
    return tuple(check.check_context for check in REQUIRED_STATUS_CHECKS)


def required_status_check_workflow_paths() -> tuple[str, ...]:
    return tuple(check.workflow_path for check in REQUIRED_STATUS_CHECKS)


def validate_repository_settings_policy(root: Path | None = None) -> tuple[str, ...]:
    repo_root = REPO_ROOT if root is None else root
    errors: list[str] = []

    check_names = required_status_check_names()
    if len(check_names) != len(set(check_names)):
        errors.append("repository settings policy: duplicate required check names")

    check_contexts = required_status_check_contexts()
    if len(check_contexts) != len(set(check_contexts)):
        errors.append("repository settings policy: duplicate required check contexts")

    workflow_paths = tuple(check.workflow_path for check in PR_FACING_STATUS_CHECKS)
    if len(workflow_paths) != len(set(workflow_paths)):
        errors.append("repository settings policy: duplicate workflow paths")

    for check in PR_FACING_STATUS_CHECKS:
        workflow_text = _read_text(repo_root, check.workflow_path)
        if workflow_text is None:
            errors.append(f"{check.workflow_path}: missing workflow file")
            continue

        workflow_name = _extract_workflow_name(workflow_text)
        if workflow_name != check.workflow_name:
            errors.append(
                f"{check.workflow_path}: workflow name must be "
                f"`{check.workflow_name}`"
            )
        if not _contains_workflow_trigger(workflow_text, check.trigger):
            errors.append(
                f"{check.workflow_path}: missing trigger `{check.trigger}`"
            )

    for doc_path in REQUIRED_STATUS_CHECK_DOCS:
        doc_text = _read_text(repo_root, doc_path)
        if doc_text is None:
            errors.append(f"{doc_path}: missing repository-settings policy doc")
            continue

        for check_name in check_names:
            if f"`{check_name}`" not in doc_text:
                errors.append(
                    f"{doc_path}: missing required status check `{check_name}`"
                )
        for check_context in check_contexts:
            if f"`{check_context}`" not in doc_text:
                errors.append(
                    f"{doc_path}: missing required status check context "
                    f"`{check_context}`"
                )
        for check_name in advisory_status_check_names():
            if f"`{check_name}`" not in doc_text:
                errors.append(
                    f"{doc_path}: missing advisory status check `{check_name}`"
                )

    for doc_path, required_links in REPOSITORY_SETTINGS_DOC_LINKS.items():
        doc_text = _read_text(repo_root, doc_path)
        if doc_text is None:
            continue
        for required_link in required_links:
            if required_link not in doc_text:
                errors.append(
                    f"{doc_path}: missing repository-settings link "
                    f"`{required_link}`"
                )

    return tuple(errors)
