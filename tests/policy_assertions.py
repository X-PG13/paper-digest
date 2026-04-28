from __future__ import annotations

import json
import re
import unittest
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StaleExemptLabels:
    issues: frozenset[str]
    pull_requests: frozenset[str]


@dataclass(frozen=True)
class ReleaseNoteCategory:
    title: str
    labels: frozenset[str]


@dataclass(frozen=True)
class ReleaseNoteConfig:
    excluded_labels: frozenset[str]
    categories: tuple[ReleaseNoteCategory, ...]


@dataclass(frozen=True)
class IssueTemplateContactLink:
    name: str
    url: str
    about: str


@dataclass(frozen=True)
class IssueFormField:
    key: str
    label: str
    required: bool
    options: frozenset[str]


@dataclass(frozen=True)
class IssueFormMetadata:
    name: str
    title: str
    fields: dict[str, IssueFormField]


class StaleExemptionSpec(Protocol):
    label: str
    stale_exempt_issues: bool
    stale_exempt_prs: bool


class ContactLinkSpec(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def target(self) -> str: ...

    @property
    def about(self) -> str: ...


class IssueFormFieldSpec(Protocol):
    @property
    def key(self) -> str: ...

    @property
    def label(self) -> str: ...

    @property
    def required(self) -> bool: ...


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def load_label_descriptions(path: str | Path = ".github/labels.json") -> dict[str, str]:
    label_definitions = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        definition["name"]: definition["description"]
        for definition in label_definitions
    }


def assert_label_descriptions(
    testcase: unittest.TestCase,
    required_descriptions: Mapping[str, str],
    *,
    path: str | Path = ".github/labels.json",
) -> None:
    descriptions = load_label_descriptions(path)
    for label, description in required_descriptions.items():
        testcase.assertEqual(descriptions[label], description)


def parse_comma_separated_labels(value: str) -> frozenset[str]:
    return frozenset(label.strip() for label in value.split(",") if label.strip())


def strip_yaml_scalar_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "'\"":
        return stripped[1:-1]
    return stripped


def load_stale_exempt_labels(
    path: str | Path = ".github/workflows/stale.yml",
) -> StaleExemptLabels:
    workflow_path = Path(path)
    workflow_text = workflow_path.read_text(encoding="utf-8")
    return StaleExemptLabels(
        issues=_extract_stale_exempt_labels(
            workflow_text,
            "exempt-issue-labels",
            workflow_path,
        ),
        pull_requests=_extract_stale_exempt_labels(
            workflow_text,
            "exempt-pr-labels",
            workflow_path,
        ),
    )


def load_issue_form_labels(path: str | Path) -> frozenset[str]:
    form_path = Path(path)
    lines = form_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("labels:"):
            continue
        value = stripped.removeprefix("labels:").strip()
        if value:
            return frozenset(_parse_yaml_label_value(value))
        base_indent = len(line) - len(line.lstrip())
        labels: list[str] = []
        for child_line in lines[index + 1:]:
            child_stripped = child_line.strip()
            if not child_stripped or child_stripped.startswith("#"):
                continue
            child_indent = len(child_line) - len(child_line.lstrip())
            if child_indent <= base_indent:
                break
            label = _parse_yaml_list_item(child_stripped)
            if label is not None:
                labels.append(label)
        if labels:
            return frozenset(labels)
    raise AssertionError(f"{form_path} is missing issue-form labels")


def load_issue_template_contact_links(
    path: str | Path = ".github/ISSUE_TEMPLATE/config.yml",
) -> dict[str, IssueTemplateContactLink]:
    config_path = Path(path)
    lines = config_path.read_text(encoding="utf-8").splitlines()
    contact_links_indent: int | None = None
    current: dict[str, str] | None = None
    links: list[IssueTemplateContactLink] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if stripped == "contact_links:":
            contact_links_indent = indent
            continue
        if contact_links_indent is None:
            continue
        if indent <= contact_links_indent:
            break
        name = _parse_yaml_mapping_list_item(stripped, "name")
        if name is not None:
            if current is not None:
                links.append(_build_contact_link(current, config_path))
            current = {"name": name}
            continue
        if current is None:
            continue
        key, separator, value = stripped.partition(":")
        if separator and key in {"url", "about"}:
            current[key] = strip_yaml_scalar_quotes(value)

    if current is not None:
        links.append(_build_contact_link(current, config_path))
    if not links:
        raise AssertionError(f"{config_path} is missing contact_links")
    return {link.name: link for link in links}


def load_issue_form_metadata(path: str | Path) -> IssueFormMetadata:
    form_path = Path(path)
    name: str | None = None
    title: str | None = None
    fields: dict[str, IssueFormField] = {}
    current_field: dict[str, object] | None = None
    in_body = False
    in_options = False
    options_indent: int | None = None

    for line in form_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if not in_body:
            if stripped.startswith("name:"):
                name = strip_yaml_scalar_quotes(stripped.removeprefix("name:"))
                continue
            if stripped.startswith("title:"):
                title = strip_yaml_scalar_quotes(stripped.removeprefix("title:"))
                continue
            if stripped == "body:":
                in_body = True
                continue
        elif indent == 0:
            break
        if not in_body:
            continue
        if stripped.startswith("- type:"):
            _add_issue_form_field(fields, current_field)
            current_field = {"required": False, "options": []}
            in_options = False
            options_indent = None
            continue
        if current_field is None:
            continue
        if in_options and options_indent is not None and indent <= options_indent:
            in_options = False
            options_indent = None
        if stripped.startswith("id:"):
            current_field["key"] = strip_yaml_scalar_quotes(
                stripped.removeprefix("id:")
            )
            in_options = False
            options_indent = None
            continue
        if stripped == "options:":
            in_options = True
            options_indent = indent
            continue
        if in_options:
            option_label = _parse_yaml_mapping_list_item(stripped, "label")
            if option_label is not None:
                options = current_field["options"]
                assert isinstance(options, list)
                options.append(option_label)
            continue
        if stripped.startswith("label:"):
            current_field["label"] = strip_yaml_scalar_quotes(
                stripped.removeprefix("label:")
            )
            continue
        if stripped.startswith("required:"):
            current_field["required"] = _parse_yaml_bool(
                stripped.removeprefix("required:")
            )

    _add_issue_form_field(fields, current_field)
    missing = []
    if name is None:
        missing.append("name")
    if title is None:
        missing.append("title")
    if missing:
        raise AssertionError(
            f"{form_path} is missing issue-form {', '.join(missing)}"
        )
    assert name is not None
    assert title is not None
    return IssueFormMetadata(name=name, title=title, fields=fields)


def load_release_note_config(
    path: str | Path = ".github/release.yml",
) -> ReleaseNoteConfig:
    release_path = Path(path)
    excluded_labels: list[str] = []
    categories: list[ReleaseNoteCategory] = []
    current_category_title: str | None = None
    current_category_labels: list[str] = []
    mode: str | None = None

    for line in release_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "categories:":
            if current_category_title is not None:
                categories.append(
                    ReleaseNoteCategory(
                        current_category_title,
                        frozenset(current_category_labels),
                    )
                )
            current_category_title = None
            current_category_labels = []
            mode = "categories"
            continue
        if stripped == "exclude:":
            mode = "exclude"
            continue
        if mode == "exclude" and stripped == "labels:":
            mode = "exclude-labels"
            continue
        if mode == "exclude-labels":
            label = _parse_yaml_list_item(stripped)
            if label is not None:
                excluded_labels.append(label)
                continue
        if mode == "categories":
            title = _parse_yaml_mapping_list_item(stripped, "title")
            if title is not None:
                if current_category_title is not None:
                    categories.append(
                        ReleaseNoteCategory(
                            current_category_title,
                            frozenset(current_category_labels),
                        )
                    )
                current_category_title = title
                current_category_labels = []
                continue
            label = _parse_yaml_list_item(stripped)
            if label is not None and current_category_title is not None:
                current_category_labels.append(label)

    if current_category_title is not None:
        categories.append(
            ReleaseNoteCategory(
                current_category_title,
                frozenset(current_category_labels),
            )
        )
    if not categories:
        raise AssertionError(f"{release_path} is missing changelog categories")
    return ReleaseNoteConfig(
        excluded_labels=frozenset(excluded_labels),
        categories=tuple(categories),
    )


def assert_release_note_categories(
    testcase: unittest.TestCase,
    required_categories: Mapping[str, Iterable[str]],
    *,
    path: str | Path = ".github/release.yml",
) -> None:
    config = load_release_note_config(path)
    labels_by_category = {
        category.title: category.labels
        for category in config.categories
    }
    for title, labels in required_categories.items():
        testcase.assertIn(title, labels_by_category)
        for label in labels:
            testcase.assertIn(label, labels_by_category[title])


def assert_release_note_excluded_labels(
    testcase: unittest.TestCase,
    labels: Iterable[str],
    *,
    path: str | Path = ".github/release.yml",
) -> None:
    config = load_release_note_config(path)
    for label in labels:
        testcase.assertIn(label, config.excluded_labels)


def assert_issue_form_labels(
    testcase: unittest.TestCase,
    labels_by_path: Mapping[str, Iterable[str]],
) -> None:
    for path, labels in labels_by_path.items():
        issue_form_labels = load_issue_form_labels(path)
        for label in labels:
            testcase.assertIn(label, issue_form_labels)


def assert_issue_template_contact_links(
    testcase: unittest.TestCase,
    expected_links: Iterable[ContactLinkSpec],
    *,
    path: str | Path = ".github/ISSUE_TEMPLATE/config.yml",
) -> None:
    contact_links = load_issue_template_contact_links(path)
    for expected in expected_links:
        testcase.assertIn(expected.name, contact_links)
        actual = contact_links[expected.name]
        testcase.assertTrue(
            _contact_link_matches_target(actual.url, expected.target),
            msg=(
                f"{path} contact link {expected.name!r} points to "
                f"{actual.url!r}, expected target {expected.target!r}"
            ),
        )
        testcase.assertEqual(actual.about, expected.about)


def assert_issue_form_metadata(
    testcase: unittest.TestCase,
    path: str | Path,
    *,
    name: str,
    title: str,
) -> None:
    metadata = load_issue_form_metadata(path)
    testcase.assertEqual(metadata.name, name)
    testcase.assertEqual(metadata.title, title)


def assert_issue_form_fields(
    testcase: unittest.TestCase,
    path: str | Path,
    fields: Iterable[IssueFormFieldSpec],
) -> None:
    metadata = load_issue_form_metadata(path)
    for field in fields:
        testcase.assertIn(field.key, metadata.fields)
        actual = metadata.fields[field.key]
        testcase.assertEqual(actual.label, field.label)
        testcase.assertEqual(actual.required, field.required)


def assert_issue_form_checkbox_options(
    testcase: unittest.TestCase,
    path: str | Path,
    field_key: str,
    labels: Iterable[str],
) -> None:
    metadata = load_issue_form_metadata(path)
    testcase.assertIn(field_key, metadata.fields)
    options = metadata.fields[field_key].options
    for label in labels:
        testcase.assertIn(label, options)


def assert_stale_exemptions(
    testcase: unittest.TestCase,
    specs: Iterable[StaleExemptionSpec],
    *,
    path: str | Path = ".github/workflows/stale.yml",
) -> None:
    exempt_labels = load_stale_exempt_labels(path)
    for spec in specs:
        testcase.assertEqual(
            spec.stale_exempt_issues,
            spec.label in exempt_labels.issues,
        )
        testcase.assertEqual(
            spec.stale_exempt_prs,
            spec.label in exempt_labels.pull_requests,
        )


def _extract_stale_exempt_labels(
    workflow_text: str,
    key: str,
    path: Path,
) -> frozenset[str]:
    match = re.search(rf"^\s*{re.escape(key)}:\s*(.+)$", workflow_text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"{path} is missing {key}")
    return parse_comma_separated_labels(match.group(1))


def _parse_yaml_list_item(stripped_line: str) -> str | None:
    if not stripped_line.startswith("- "):
        return None
    return strip_yaml_scalar_quotes(stripped_line[2:])


def _parse_yaml_mapping_list_item(stripped_line: str, key: str) -> str | None:
    prefix = f"- {key}:"
    if not stripped_line.startswith(prefix):
        return None
    return strip_yaml_scalar_quotes(stripped_line[len(prefix):])


def _parse_yaml_label_value(value: str) -> tuple[str, ...]:
    normalized = value.removesuffix(",").strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        return tuple(
            strip_yaml_scalar_quotes(item.strip())
            for item in normalized[1:-1].split(",")
            if item.strip()
        )
    return (strip_yaml_scalar_quotes(normalized),)


def _add_issue_form_field(
    fields: dict[str, IssueFormField],
    current_field: dict[str, object] | None,
) -> None:
    if current_field is None:
        return
    key = current_field.get("key")
    label = current_field.get("label")
    if not isinstance(key, str) or not isinstance(label, str):
        return
    required = current_field.get("required", False)
    options = current_field.get("options", [])
    if not isinstance(required, bool) or not isinstance(options, list):
        raise AssertionError(f"invalid issue-form field metadata for {key}")
    fields[key] = IssueFormField(
        key=key,
        label=label,
        required=required,
        options=frozenset(str(option) for option in options),
    )


def _parse_yaml_bool(value: str) -> bool:
    normalized = strip_yaml_scalar_quotes(value).lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise AssertionError(f"unsupported YAML bool: {value}")


def _build_contact_link(
    values: Mapping[str, str],
    path: Path,
) -> IssueTemplateContactLink:
    missing = {"name", "url", "about"} - values.keys()
    if missing:
        raise AssertionError(
            f"{path} contact link is missing {', '.join(sorted(missing))}"
        )
    return IssueTemplateContactLink(
        name=values["name"],
        url=values["url"],
        about=values["about"],
    )


def _contact_link_matches_target(url: str, target: str) -> bool:
    if target.startswith(("http://", "https://")):
        return url == target
    return url == target or url.endswith(f"/{target.lstrip('/')}")


def assert_file_contains_snippets(
    testcase: unittest.TestCase,
    path: str | Path,
    snippets: Iterable[str],
    *,
    normalize: bool = True,
) -> None:
    file_text = Path(path).read_text(encoding="utf-8")
    haystack = normalize_space(file_text) if normalize else file_text
    for snippet in snippets:
        needle = normalize_space(snippet) if normalize else snippet
        testcase.assertIn(
            needle,
            haystack,
            msg=f"{path} is missing expected snippet: {snippet}",
        )


def assert_files_contain_snippets(
    testcase: unittest.TestCase,
    snippets_by_path: Mapping[str, Iterable[str]],
    *,
    normalize: bool = True,
) -> None:
    for path, snippets in snippets_by_path.items():
        assert_file_contains_snippets(
            testcase,
            path,
            snippets,
            normalize=normalize,
        )
