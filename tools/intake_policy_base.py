from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class DocPathSpec:
    path: str


@dataclass(frozen=True)
class KeyLabelSpec:
    key: str
    label: str


@dataclass(frozen=True)
class ContactLinkSpec:
    name: str
    target: str
    about: str


def collect_spec_snippets(
    *spec_groups: Iterable[object],
    attribute: str,
) -> tuple[str, ...]:
    snippets: list[str] = []
    for specs in spec_groups:
        for spec in specs:
            snippets.extend(getattr(spec, attribute))
    return tuple(snippets)


def validate_unique_doc_paths(
    specs: Iterable[DocPathSpec],
    *,
    duplicate_error_prefix: str,
) -> None:
    seen_paths: set[str] = set()
    for spec in specs:
        if spec.path in seen_paths:
            raise ValueError(f"{duplicate_error_prefix}: {spec.path}")
        seen_paths.add(spec.path)


def validate_unique_key_labels(
    specs: Iterable[KeyLabelSpec],
    *,
    duplicate_key_error_prefix: str,
    duplicate_label_error_prefix: str,
) -> None:
    seen_keys: set[str] = set()
    seen_labels: set[str] = set()
    for spec in specs:
        if spec.key in seen_keys:
            raise ValueError(f"{duplicate_key_error_prefix}: {spec.key}")
        seen_keys.add(spec.key)
        if spec.label in seen_labels:
            raise ValueError(f"{duplicate_label_error_prefix}: {spec.label}")
        seen_labels.add(spec.label)


def validate_contact_link_specs(
    specs: Iterable[ContactLinkSpec],
    *,
    duplicate_name_error_prefix: str,
) -> None:
    seen_names: set[str] = set()
    for spec in specs:
        if not spec.name:
            raise ValueError("contact link name must not be empty")
        if not spec.target:
            raise ValueError("contact link target must not be empty: " + spec.name)
        if not spec.about:
            raise ValueError("contact link about must not be empty: " + spec.name)
        if spec.name in seen_names:
            raise ValueError(f"{duplicate_name_error_prefix}: {spec.name}")
        seen_names.add(spec.name)
