from __future__ import annotations

from dataclasses import dataclass

from tools import issue_form_policy as _issue_form_policy
from tools.intake_policy_base import (
    ContactLinkSpec,
    DocPathSpec,
    KeyLabelSpec,
    validate_contact_link_specs,
    validate_unique_doc_paths,
    validate_unique_key_labels,
)

SUPPORT_LABEL = "support"
SUPPORT_CONTACT_LINK = ContactLinkSpec(
    name="Support Expectations",
    target="SUPPORT.md",
    about="Read this before opening a usage or setup question.",
)
SUPPORT_CONTACT_LINK_NAME = SUPPORT_CONTACT_LINK.name
SUPPORT_CONTACT_LINK_TARGET = SUPPORT_CONTACT_LINK.target
SUPPORT_CONTACT_LINK_ABOUT = SUPPORT_CONTACT_LINK.about
SUPPORT_REQUEST_FORM_PATH = _issue_form_policy.SUPPORT_REQUEST_FORM_PATH
SUPPORT_REQUEST_FORM_NAME = _issue_form_policy.SUPPORT_REQUEST_FORM_NAME
SUPPORT_REQUEST_FORM_TITLE = _issue_form_policy.SUPPORT_REQUEST_FORM_TITLE
SUPPORT_REQUEST_FORM_INTRO_LINES = (
    "Use this form only after checking the linked docs.",
    "Security problems still belong in `SECURITY.md`.",
)
SUPPORT_REQUEST_CHECKLIST_LABEL = "What you already checked"
SUPPORT_REQUEST_QUESTION_LABEL = "Question"
SUPPORT_REQUEST_COMMAND_LABEL = "Command or workflow path"
SUPPORT_REQUEST_MINIMAL_CONFIG_LABEL = "Minimal config snippet"
SUPPORT_REQUEST_OBSERVED_BEHAVIOR_LABEL = "Error or confusing behavior"
SUPPORT_TRIAGE_MARKER = "<!-- community-triage-support-needs-info -->"
SUPPORT_TRIAGE_COMMENT_HEADER = (
    "Thanks for the question. This support request is missing some of the "
    "minimum context the maintainer policy asks for before routing can continue:"
)
SUPPORT_TRIAGE_COMMENT_FOOTER = (
    "Please edit the issue with the missing details and the automation will "
    "clear this reminder on the next update."
)
SUPPORT_PRECHECK_MISSING_MESSAGE = (
    "confirmation that the pre-read support docs were checked"
)


SupportDocSpec = DocPathSpec


@dataclass(frozen=True)
class SupportFieldSpec(KeyLabelSpec):
    required: bool
    missing_message: str | None = None
    support_md_bullet: str | None = None


SUPPORT_PRECHECK_DOCS = (
    SupportDocSpec(path="README.md"),
    SupportDocSpec(path="config.example.toml"),
    SupportDocSpec(path="docs/config-recipes.md"),
    SupportDocSpec(path="docs/compatibility-matrix.md"),
    SupportDocSpec(path="docs/discussions-policy.md"),
)

SUPPORT_REQUEST_FIELDS = (
    SupportFieldSpec(
        key="question",
        label=SUPPORT_REQUEST_QUESTION_LABEL,
        required=True,
        missing_message="what you are trying to do and where you are blocked",
        support_md_bullet="What you are trying to do, and where you are blocked.",
    ),
    SupportFieldSpec(
        key="os",
        label="OS",
        required=True,
        missing_message="the operating system",
        support_md_bullet="The Python version and operating system.",
    ),
    SupportFieldSpec(
        key="python_version",
        label="Python version",
        required=True,
        missing_message="the Python version",
    ),
    SupportFieldSpec(
        key="project_version",
        label="Project version or commit",
        required=True,
        missing_message="the Paper Digest version, tag, or commit",
        support_md_bullet="The project version, tag, or commit hash.",
    ),
    SupportFieldSpec(
        key="command_or_workflow",
        label=SUPPORT_REQUEST_COMMAND_LABEL,
        required=True,
        missing_message="the exact command or workflow path",
        support_md_bullet="The exact command you ran.",
    ),
    SupportFieldSpec(
        key="minimal_config",
        label=SUPPORT_REQUEST_MINIMAL_CONFIG_LABEL,
        required=False,
        support_md_bullet="A minimal config snippet with secrets removed.",
    ),
    SupportFieldSpec(
        key="observed_behavior",
        label=SUPPORT_REQUEST_OBSERVED_BEHAVIOR_LABEL,
        required=False,
        support_md_bullet=(
            "The exact error output or the smallest observable incorrect behavior."
        ),
    ),
)


def required_support_request_form_snippets() -> tuple[str, ...]:
    return SUPPORT_REQUEST_FORM_INTRO_LINES


def required_support_request_form_fields() -> tuple[SupportFieldSpec, ...]:
    return SUPPORT_REQUEST_FIELDS


def required_support_request_precheck_options() -> tuple[str, ...]:
    return tuple(doc.path for doc in SUPPORT_PRECHECK_DOCS)


def required_support_md_snippets() -> tuple[str, ...]:
    snippets = [f"- [`{doc.path}`](./{doc.path})" for doc in SUPPORT_PRECHECK_DOCS]
    snippets.extend(
        f"- {field.support_md_bullet}"
        for field in SUPPORT_REQUEST_FIELDS
        if field.support_md_bullet is not None
    )
    return tuple(snippets)


def required_issue_template_contact_links() -> tuple[ContactLinkSpec, ...]:
    return (SUPPORT_CONTACT_LINK,)


def validate_support_contract() -> None:
    validate_contact_link_specs(
        required_issue_template_contact_links(),
        duplicate_name_error_prefix="duplicate support contact link",
    )
    validate_unique_doc_paths(
        SUPPORT_PRECHECK_DOCS,
        duplicate_error_prefix="duplicate support doc path",
    )
    validate_unique_key_labels(
        SUPPORT_REQUEST_FIELDS,
        duplicate_key_error_prefix="duplicate support field key",
        duplicate_label_error_prefix="duplicate support field label",
    )
    for field in SUPPORT_REQUEST_FIELDS:
        if field.support_md_bullet is not None and not field.support_md_bullet.endswith(
            "."
        ):
            raise ValueError(
                "support markdown bullets must end with a period: " + field.key
            )
        if field.required and field.missing_message is None:
            raise ValueError(
                "required support field must define a missing message: " + field.key
            )

    if not SUPPORT_REQUEST_FORM_INTRO_LINES:
        raise ValueError("support request form intro lines must not be empty")
