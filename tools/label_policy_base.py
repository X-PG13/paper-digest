from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactContract:
    path: str
    snippets: tuple[str, ...]


@dataclass(frozen=True)
class LabelPolicySpec:
    label: str
    label_json_description: str
    issue_triage_snippets: tuple[str, ...]
    label_taxonomy_snippets: tuple[str, ...]
    artifact_contracts: tuple[ArtifactContract, ...] = ()
    reply_slug: str | None = None
    auto_pr_routing_paths: tuple[str, ...] = ()
    auto_pr_routing_actor: str | None = None
    manual_only: bool = False
    stale_exempt_issues: bool = False
    stale_exempt_prs: bool = False
    release_note_category: str | None = None
    release_note_excluded: bool = False


def collect_issue_triage_snippets(
    specs: Iterable[LabelPolicySpec],
) -> tuple[str, ...]:
    snippets: list[str] = []
    for spec in specs:
        snippets.extend(spec.issue_triage_snippets)
    return tuple(snippets)


def collect_label_taxonomy_snippets(
    specs: Iterable[LabelPolicySpec],
) -> tuple[str, ...]:
    snippets: list[str] = []
    for spec in specs:
        snippets.extend(spec.label_taxonomy_snippets)
    return tuple(snippets)


def collect_label_descriptions(
    specs: Iterable[LabelPolicySpec],
) -> dict[str, str]:
    return {
        spec.label: spec.label_json_description
        for spec in specs
    }


def collect_artifact_snippets_by_path(
    specs: Iterable[LabelPolicySpec],
) -> dict[str, tuple[str, ...]]:
    snippets_by_path: dict[str, list[str]] = {}
    for spec in specs:
        for contract in spec.artifact_contracts:
            snippets_by_path.setdefault(contract.path, []).extend(contract.snippets)
    return {
        path: tuple(snippets)
        for path, snippets in snippets_by_path.items()
    }


def collect_release_note_categories(
    specs: Iterable[LabelPolicySpec],
) -> dict[str, tuple[str, ...]]:
    labels_by_category: dict[str, list[str]] = {}
    for spec in specs:
        if spec.release_note_category is not None:
            labels_by_category.setdefault(spec.release_note_category, []).append(
                spec.label
            )
    return {
        category: tuple(labels)
        for category, labels in labels_by_category.items()
    }


def collect_release_note_excluded_labels(
    specs: Iterable[LabelPolicySpec],
) -> tuple[str, ...]:
    return tuple(
        spec.label
        for spec in specs
        if spec.release_note_excluded
    )


def validate_label_policy_specs(
    specs: Iterable[LabelPolicySpec],
    *,
    duplicate_error_prefix: str,
    missing_issue_triage_error_prefix: str,
    missing_label_taxonomy_error_prefix: str,
    manual_only_auto_error_prefix: str,
    reply_lookup: Callable[[str], object] | None = None,
) -> None:
    seen_labels: set[str] = set()
    for spec in specs:
        if spec.label in seen_labels:
            raise ValueError(f"{duplicate_error_prefix}: {spec.label}")
        seen_labels.add(spec.label)
        if spec.reply_slug is not None and reply_lookup is not None:
            reply_lookup(spec.reply_slug)
        if not spec.issue_triage_snippets:
            raise ValueError(f"{missing_issue_triage_error_prefix}: {spec.label}")
        if not spec.label_taxonomy_snippets:
            raise ValueError(f"{missing_label_taxonomy_error_prefix}: {spec.label}")
        if spec.manual_only and spec.auto_pr_routing_paths:
            raise ValueError(f"{manual_only_auto_error_prefix}: {spec.label}")
        if spec.release_note_category is not None and spec.release_note_excluded:
            raise ValueError(
                "release-note label cannot be both categorized and excluded: "
                + spec.label
            )
        for contract in spec.artifact_contracts:
            if not contract.path:
                raise ValueError("artifact contract path must not be empty")
            if not contract.snippets:
                raise ValueError(
                    "artifact contract must define snippets: " + contract.path
                )
