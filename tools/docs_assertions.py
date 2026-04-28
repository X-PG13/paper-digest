from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from tools.docs_findings import DocsCheckFinding, finding_for_subject
from tools.docs_sources import TextSourceOrigin


def normalize_text_block(text: str) -> str:
    text = re.sub(r"[`*_~]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def text_contains_all_snippets(text: str, snippets: Sequence[str]) -> bool:
    normalized_text = normalize_text_block(text)
    return all(
        normalize_text_block(snippet) in normalized_text
        for snippet in snippets
    )


def require_expected_fields(
    contract_family: str,
    contract_name: str,
    subject: str,
    actual_fields: dict[str, str],
    expected_fields: Mapping[str, str],
    errors: list[DocsCheckFinding],
    *,
    subject_origins: Mapping[str, TextSourceOrigin] | None = None,
) -> None:
    for label, expected_value in expected_fields.items():
        actual_value = actual_fields.get(label)
        if actual_value is None:
            errors.append(
                build_subject_finding(
                    (
                        f"{contract_family} contract '{contract_name}' "
                        f"missing field '{label}' from {subject}"
                    ),
                    subject,
                    subject_origins=subject_origins,
                )
            )
            continue
        if normalize_text_block(actual_value) != normalize_text_block(expected_value):
            errors.append(
                build_subject_finding(
                    (
                        f"{contract_family} contract '{contract_name}' has unexpected "
                        f"value for '{label}' in {subject}: expected "
                        f"'{expected_value}', found '{actual_value}'"
                    ),
                    subject,
                    subject_origins=subject_origins,
                )
            )


def require_expected_items(
    contract_family: str,
    contract_name: str,
    subject: str,
    actual_items: list[str],
    expected_items: Sequence[str],
    errors: list[DocsCheckFinding],
    *,
    subject_origins: Mapping[str, TextSourceOrigin] | None = None,
) -> None:
    normalized_actual_items = {
        normalize_text_block(item) for item in actual_items if item
    }
    for expected_item in expected_items:
        if normalize_text_block(expected_item) in normalized_actual_items:
            continue
        errors.append(
            build_subject_finding(
                (
                    f"{contract_family} contract '{contract_name}' missing item "
                    f"from {subject}: {expected_item}"
                ),
                subject,
                subject_origins=subject_origins,
            )
        )


def extend_contract_errors(
    contract_family: str,
    text_by_label: dict[str, str],
    contracts: Sequence[Any],
    errors: list[DocsCheckFinding],
    *,
    subject_origins: Mapping[str, TextSourceOrigin] | None = None,
) -> None:
    for contract in contracts:
        for expectation in contract.expectations:
            if text_contains_all_snippets(
                text_by_label[expectation.subject],
                expectation.snippets,
            ):
                continue
            errors.append(
                build_subject_finding(
                    (
                        f"{contract_family} contract '{contract.name}' missing "
                        f"from {expectation.subject}: "
                        f"{', '.join(expectation.snippets)}"
                    ),
                    expectation.subject,
                    subject_origins=subject_origins,
                )
            )


def build_subject_finding(
    message: str,
    subject: str,
    *,
    subject_origins: Mapping[str, TextSourceOrigin] | None = None,
) -> DocsCheckFinding:
    if subject_origins is not None:
        origin = subject_origins.get(subject)
        if origin is not None:
            return DocsCheckFinding(
                message=message,
                path=origin.path,
                line=origin.line,
                end_line=origin.end_line,
            )
    return finding_for_subject(message, subject)
