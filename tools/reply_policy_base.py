from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ReplyContractSpec:
    slug: str
    header: str
    body_lines: tuple[str, ...]
    bullet_items: tuple[str, ...] = ()
    footer_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReplySnippetPolicySpec:
    reply_slug: str
    issue_triage_snippets: tuple[str, ...]
    label_taxonomy_snippets: tuple[str, ...]


def get_reply_spec_by_slug(
    specs: Iterable[ReplyContractSpec],
    slug: str,
    *,
    unknown_error_prefix: str,
) -> ReplyContractSpec:
    for spec in specs:
        if spec.slug == slug:
            return spec
    raise KeyError(f"{unknown_error_prefix}: {slug}")


def collect_saved_reply_snippets(
    specs: Iterable[ReplyContractSpec],
    *slugs: str,
) -> tuple[str, ...]:
    requested_slugs = slugs or tuple(spec.slug for spec in specs)
    snippets: list[str] = []
    for slug in requested_slugs:
        spec = get_reply_spec_by_slug(
            specs,
            slug,
            unknown_error_prefix="unknown saved reply slug",
        )
        snippets.append(f"## `{spec.slug}`")
        snippets.append(spec.header)
        snippets.extend(spec.body_lines)
        snippets.extend(f"- {item}" for item in spec.bullet_items)
        snippets.extend(spec.footer_lines)
    return tuple(snippets)


def collect_issue_triage_snippets(
    specs: Iterable[ReplySnippetPolicySpec],
) -> tuple[str, ...]:
    snippets: list[str] = []
    for spec in specs:
        snippets.extend(spec.issue_triage_snippets)
    return tuple(snippets)


def collect_label_taxonomy_snippets(
    specs: Iterable[ReplySnippetPolicySpec],
) -> tuple[str, ...]:
    snippets: list[str] = []
    for spec in specs:
        snippets.extend(spec.label_taxonomy_snippets)
    return tuple(snippets)


def validate_reply_contract_specs(
    specs: Iterable[ReplyContractSpec],
    *,
    duplicate_error_prefix: str,
    missing_header_error_prefix: str,
    empty_reply_error_prefix: str,
    empty_body_error_prefix: str,
    empty_bullet_error_prefix: str,
    empty_footer_error_prefix: str,
) -> None:
    seen_slugs: set[str] = set()
    for spec in specs:
        if spec.slug in seen_slugs:
            raise ValueError(f"{duplicate_error_prefix}: {spec.slug}")
        seen_slugs.add(spec.slug)
        if not spec.header:
            raise ValueError(f"{missing_header_error_prefix}: {spec.slug}")
        if not spec.body_lines and not spec.bullet_items and not spec.footer_lines:
            raise ValueError(f"{empty_reply_error_prefix}: {spec.slug}")
        if any(not line for line in spec.body_lines):
            raise ValueError(f"{empty_body_error_prefix}: {spec.slug}")
        if any(not item for item in spec.bullet_items):
            raise ValueError(f"{empty_bullet_error_prefix}: {spec.slug}")
        if any(not line for line in spec.footer_lines):
            raise ValueError(f"{empty_footer_error_prefix}: {spec.slug}")


def validate_reply_snippet_policy_specs(
    specs: Iterable[ReplySnippetPolicySpec],
    *,
    duplicate_error_prefix: str,
    missing_issue_triage_error_prefix: str,
    missing_label_taxonomy_error_prefix: str,
    reply_lookup: Callable[[str], object],
) -> None:
    seen_slugs: set[str] = set()
    for spec in specs:
        if spec.reply_slug in seen_slugs:
            raise ValueError(f"{duplicate_error_prefix}: {spec.reply_slug}")
        seen_slugs.add(spec.reply_slug)
        reply_lookup(spec.reply_slug)
        if not spec.issue_triage_snippets:
            raise ValueError(
                f"{missing_issue_triage_error_prefix}: {spec.reply_slug}"
            )
        if not spec.label_taxonomy_snippets:
            raise ValueError(
                f"{missing_label_taxonomy_error_prefix}: {spec.reply_slug}"
            )
