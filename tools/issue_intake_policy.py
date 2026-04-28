from __future__ import annotations

from dataclasses import dataclass

from tools import issue_form_policy as _issue_form_policy
from tools.intake_policy_base import (
    KeyLabelSpec,
    collect_spec_snippets,
    validate_unique_key_labels,
)

COMMUNITY_TRIAGE_MARKER = "<!-- community-triage-needs-info -->"
BUG_LABEL = "bug"
NEEDS_INFO_LABEL = "needs-info"
BUG_REPORT_FORM_PATH = _issue_form_policy.BUG_REPORT_FORM_PATH
BUG_REPORT_FORM_NAME = _issue_form_policy.BUG_REPORT_FORM_NAME
BUG_REPORT_FORM_TITLE = _issue_form_policy.BUG_REPORT_FORM_TITLE

ISSUE_INTAKE_COMMENT_HEADER = (
    "Thanks for the report. This bug issue is missing some of the minimum "
    "information the maintainer policy asks for before deeper triage can start:"
)
ISSUE_INTAKE_COMMENT_FOOTER = (
    "Please edit the issue with the missing details and the automation will "
    "clear this reminder on the next update."
)


@dataclass(frozen=True)
class IssueIntakeSectionSpec(KeyLabelSpec):
    placeholder_patterns: tuple[str, ...]
    missing_message: str
    required_form_snippets: tuple[str, ...]
    required: bool = True


@dataclass(frozen=True)
class IssueIntakeFieldSpec(KeyLabelSpec):
    missing_message: str
    required: bool = True
    required_form_snippets: tuple[str, ...] = ()


ISSUE_INTAKE_SECTIONS = (
    IssueIntakeSectionSpec(
        key="reproduction",
        label="Reproduction",
        placeholder_patterns=(
            r"^\d+\.\s*Configuration used:\s*$",
            r"^\d+\.\s*Command executed:\s*$",
            r"^\d+\.\s*What happened:\s*$",
        ),
        missing_message="reproduction steps with the exact command or workflow path",
        required_form_snippets=(
            "1. Configuration used:",
            "2. Command executed:",
            "3. What happened:",
        ),
    ),
    IssueIntakeSectionSpec(
        key="minimal_config",
        label="Minimal config snippet",
        placeholder_patterns=(
            r"^Paste the smallest relevant config excerpt with secrets removed\.$",
        ),
        missing_message="a minimal config snippet with secrets removed",
        required_form_snippets=(
            "Paste the smallest relevant config excerpt with secrets removed.",
        ),
    ),
    IssueIntakeSectionSpec(
        key="expected_behavior",
        label="Expected behavior",
        placeholder_patterns=(r"^Describe what you expected instead\.$",),
        missing_message="a clear expected result",
        required_form_snippets=(
            "Describe what you expected instead.",
        ),
    ),
)

ISSUE_INTAKE_FIELDS = (
    IssueIntakeFieldSpec(
        key="os",
        label="OS",
        missing_message="the operating system",
    ),
    IssueIntakeFieldSpec(
        key="python_version",
        label="Python version",
        missing_message="the Python version",
    ),
    IssueIntakeFieldSpec(
        key="project_version",
        label="Project version or commit",
        missing_message="the Paper Digest version, tag, or commit",
    ),
)


def get_issue_intake_section(key: str) -> IssueIntakeSectionSpec:
    for section in ISSUE_INTAKE_SECTIONS:
        if section.key == key:
            return section
    raise KeyError(f"unknown issue intake section key: {key}")


def get_issue_intake_field(key: str) -> IssueIntakeFieldSpec:
    for field in ISSUE_INTAKE_FIELDS:
        if field.key == key:
            return field
    raise KeyError(f"unknown issue intake field key: {key}")


def required_bug_report_form_snippets() -> tuple[str, ...]:
    return collect_spec_snippets(
        ISSUE_INTAKE_SECTIONS,
        attribute="required_form_snippets",
    )


def required_bug_report_form_fields() -> tuple[
    IssueIntakeSectionSpec | IssueIntakeFieldSpec,
    ...,
]:
    return (*ISSUE_INTAKE_SECTIONS, *ISSUE_INTAKE_FIELDS)


def validate_issue_intake_contract() -> None:
    validate_unique_key_labels(
        (*ISSUE_INTAKE_SECTIONS, *ISSUE_INTAKE_FIELDS),
        duplicate_key_error_prefix="duplicate issue intake key",
        duplicate_label_error_prefix="duplicate issue intake label",
    )
    for section in ISSUE_INTAKE_SECTIONS:
        if not section.placeholder_patterns:
            raise ValueError(
                "issue intake section must define placeholder patterns: " + section.key
            )
        if not section.missing_message:
            raise ValueError(
                "issue intake section must define a missing message: " + section.key
            )
    for field in ISSUE_INTAKE_FIELDS:
        if not field.missing_message:
            raise ValueError(
                "issue intake field must define a missing message: " + field.key
            )
