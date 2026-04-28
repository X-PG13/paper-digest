from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IssueFormFieldSpec:
    key: str
    label: str
    required: bool = True


@dataclass(frozen=True)
class IssueFormSpec:
    path: str
    name: str
    title: str
    labels: tuple[str, ...]
    fields: tuple[IssueFormFieldSpec, ...]


@dataclass(frozen=True)
class IssueFormGroupSpec:
    key: str
    paths: tuple[str, ...]


class IssueFormFieldLike(Protocol):
    @property
    def key(self) -> str: ...

    @property
    def label(self) -> str: ...

    @property
    def required(self) -> bool: ...


BUG_REPORT_FORM_PATH = ".github/ISSUE_TEMPLATE/bug_report.yml"
BUG_REPORT_FORM_NAME = "Bug report"
BUG_REPORT_FORM_TITLE = "[Bug] "
BUG_REPORT_FORM_LABELS = ("bug",)
SUPPORT_REQUEST_FORM_PATH = ".github/ISSUE_TEMPLATE/support_request.yml"
SUPPORT_REQUEST_FORM_NAME = "Support request"
SUPPORT_REQUEST_FORM_TITLE = "[Support] "
SUPPORT_REQUEST_FORM_LABELS = ("support",)
FEATURE_REQUEST_FORM_PATH = ".github/ISSUE_TEMPLATE/feature_request.yml"
FEATURE_REQUEST_FORM_NAME = "Feature request"
FEATURE_REQUEST_FORM_TITLE = "[Feature] "
FEATURE_REQUEST_FORM_LABELS = ("enhancement",)
PROPOSAL_FORM_PATH = ".github/ISSUE_TEMPLATE/proposal.yml"
PROPOSAL_FORM_NAME = "Proposal"
PROPOSAL_FORM_TITLE = "[Proposal] "
PROPOSAL_FORM_LABELS = ("enhancement", "proposal")
RELEASE_PREPARATION_FORM_PATH = ".github/ISSUE_TEMPLATE/release_preparation.yml"
RELEASE_PREPARATION_FORM_NAME = "Release preparation"
RELEASE_PREPARATION_FORM_TITLE = "[Release] v"
RELEASE_PREPARATION_FORM_LABELS = ("maintenance", "release-prep")
POST_RELEASE_FOLLOW_UP_FORM_PATH = ".github/ISSUE_TEMPLATE/post_release_follow_up.yml"
POST_RELEASE_FOLLOW_UP_FORM_NAME = "Post-release follow-up"
POST_RELEASE_FOLLOW_UP_FORM_TITLE = "[Post Release] v"
POST_RELEASE_FOLLOW_UP_FORM_LABELS = ("maintenance", "release-follow-up")

ROUTING_LABEL_ISSUE_FORM_GROUP = "routing-labels"
CONTRIBUTOR_RELEASE_LABEL_ISSUE_FORM_GROUP = "contributor-release-labels"
STATUS_LABEL_ISSUE_FORM_GROUP = "status-labels"
RELEASE_LIFECYCLE_ISSUE_FORM_GROUP = "release-lifecycle"

ISSUE_FORM_GROUP_SPECS = (
    IssueFormGroupSpec(
        key=ROUTING_LABEL_ISSUE_FORM_GROUP,
        paths=(
            BUG_REPORT_FORM_PATH,
            SUPPORT_REQUEST_FORM_PATH,
            PROPOSAL_FORM_PATH,
        ),
    ),
    IssueFormGroupSpec(
        key=CONTRIBUTOR_RELEASE_LABEL_ISSUE_FORM_GROUP,
        paths=(
            FEATURE_REQUEST_FORM_PATH,
            PROPOSAL_FORM_PATH,
            RELEASE_PREPARATION_FORM_PATH,
            POST_RELEASE_FOLLOW_UP_FORM_PATH,
        ),
    ),
    IssueFormGroupSpec(
        key=STATUS_LABEL_ISSUE_FORM_GROUP,
        paths=(
            RELEASE_PREPARATION_FORM_PATH,
            POST_RELEASE_FOLLOW_UP_FORM_PATH,
        ),
    ),
    IssueFormGroupSpec(
        key=RELEASE_LIFECYCLE_ISSUE_FORM_GROUP,
        paths=(
            RELEASE_PREPARATION_FORM_PATH,
            POST_RELEASE_FOLLOW_UP_FORM_PATH,
        ),
    ),
)


FEATURE_REQUEST_FORM_FIELDS = (
    IssueFormFieldSpec(
        key="problem",
        label="Problem",
    ),
    IssueFormFieldSpec(
        key="proposed_solution",
        label="Proposed solution",
    ),
    IssueFormFieldSpec(
        key="alternatives",
        label="Alternatives considered",
        required=False,
    ),
    IssueFormFieldSpec(
        key="scope_notes",
        label="Scope notes",
        required=False,
    ),
)

PROPOSAL_FORM_FIELDS = (
    IssueFormFieldSpec(
        key="summary",
        label="Summary",
    ),
    IssueFormFieldSpec(
        key="problem",
        label="Problem or opportunity",
    ),
    IssueFormFieldSpec(
        key="scope_fit",
        label="Scope fit",
    ),
    IssueFormFieldSpec(
        key="proposed_approach",
        label="Proposed approach",
    ),
    IssueFormFieldSpec(
        key="impact",
        label="Compatibility and maintenance impact",
    ),
    IssueFormFieldSpec(
        key="alternatives",
        label="Alternatives considered",
        required=False,
    ),
    IssueFormFieldSpec(
        key="rollout",
        label="Rollout notes",
        required=False,
    ),
)

RELEASE_PREPARATION_FORM_FIELDS = (
    IssueFormFieldSpec(
        key="version",
        label="Release version",
    ),
    IssueFormFieldSpec(
        key="release_type",
        label="Release type",
    ),
    IssueFormFieldSpec(
        key="target_tag",
        label="Target tag",
    ),
    IssueFormFieldSpec(
        key="quarterly_review",
        label="Latest quarterly review issue",
    ),
    IssueFormFieldSpec(
        key="scope_summary",
        label="Scope summary",
    ),
    IssueFormFieldSpec(
        key="compatibility_and_repo_ops",
        label="Compatibility and repository-operations checks",
    ),
    IssueFormFieldSpec(
        key="changelog_and_notes",
        label="Changelog and release-notes intent",
    ),
    IssueFormFieldSpec(
        key="validation",
        label="Validation checklist",
    ),
    IssueFormFieldSpec(
        key="follow_up",
        label="Release and post-release follow-up",
        required=False,
    ),
    IssueFormFieldSpec(
        key="close_out",
        label="Close-out handoff",
        required=False,
    ),
)

POST_RELEASE_FOLLOW_UP_FORM_FIELDS = (
    IssueFormFieldSpec(
        key="release_version",
        label="Release version",
    ),
    IssueFormFieldSpec(
        key="release_prep_issue",
        label="Release-preparation issue",
    ),
    IssueFormFieldSpec(
        key="published_release_url",
        label="Published release URL",
        required=False,
    ),
    IssueFormFieldSpec(
        key="quarterly_review_issue",
        label="Latest quarterly review issue",
        required=False,
    ),
    IssueFormFieldSpec(
        key="immediate_validation",
        label="Immediate validation",
    ),
    IssueFormFieldSpec(
        key="next_cycle",
        label="Next-cycle setup",
    ),
    IssueFormFieldSpec(
        key="retrospective",
        label="Release retrospective",
        required=False,
    ),
    IssueFormFieldSpec(
        key="close_out",
        label="Close-out summary",
        required=False,
    ),
)


def required_issue_form_specs() -> tuple[IssueFormSpec, ...]:
    from tools.issue_intake_policy import required_bug_report_form_fields
    from tools.support_policy import required_support_request_form_fields

    return (
        IssueFormSpec(
            path=BUG_REPORT_FORM_PATH,
            name=BUG_REPORT_FORM_NAME,
            title=BUG_REPORT_FORM_TITLE,
            labels=BUG_REPORT_FORM_LABELS,
            fields=_copy_field_specs(required_bug_report_form_fields()),
        ),
        IssueFormSpec(
            path=SUPPORT_REQUEST_FORM_PATH,
            name=SUPPORT_REQUEST_FORM_NAME,
            title=SUPPORT_REQUEST_FORM_TITLE,
            labels=SUPPORT_REQUEST_FORM_LABELS,
            fields=_copy_field_specs(required_support_request_form_fields()),
        ),
        IssueFormSpec(
            path=FEATURE_REQUEST_FORM_PATH,
            name=FEATURE_REQUEST_FORM_NAME,
            title=FEATURE_REQUEST_FORM_TITLE,
            labels=FEATURE_REQUEST_FORM_LABELS,
            fields=FEATURE_REQUEST_FORM_FIELDS,
        ),
        IssueFormSpec(
            path=PROPOSAL_FORM_PATH,
            name=PROPOSAL_FORM_NAME,
            title=PROPOSAL_FORM_TITLE,
            labels=PROPOSAL_FORM_LABELS,
            fields=PROPOSAL_FORM_FIELDS,
        ),
        IssueFormSpec(
            path=RELEASE_PREPARATION_FORM_PATH,
            name=RELEASE_PREPARATION_FORM_NAME,
            title=RELEASE_PREPARATION_FORM_TITLE,
            labels=RELEASE_PREPARATION_FORM_LABELS,
            fields=RELEASE_PREPARATION_FORM_FIELDS,
        ),
        IssueFormSpec(
            path=POST_RELEASE_FOLLOW_UP_FORM_PATH,
            name=POST_RELEASE_FOLLOW_UP_FORM_NAME,
            title=POST_RELEASE_FOLLOW_UP_FORM_TITLE,
            labels=POST_RELEASE_FOLLOW_UP_FORM_LABELS,
            fields=POST_RELEASE_FOLLOW_UP_FORM_FIELDS,
        ),
    )


def required_issue_form_paths() -> frozenset[str]:
    return frozenset(spec.path for spec in required_issue_form_specs())


def required_issue_form_group_specs() -> tuple[IssueFormGroupSpec, ...]:
    return ISSUE_FORM_GROUP_SPECS


def get_issue_form_spec(path: str) -> IssueFormSpec:
    for spec in required_issue_form_specs():
        if spec.path == path:
            return spec
    raise KeyError(f"unknown issue form path: {path}")


def get_issue_form_group_spec(key: str) -> IssueFormGroupSpec:
    for spec in required_issue_form_group_specs():
        if spec.key == key:
            return spec
    raise KeyError(f"unknown issue form group: {key}")


def issue_form_paths_for_group(key: str) -> tuple[str, ...]:
    return get_issue_form_group_spec(key).paths


def issue_form_labels_by_path(paths: Iterable[str]) -> dict[str, tuple[str, ...]]:
    return {
        path: get_issue_form_spec(path).labels
        for path in paths
    }


def issue_form_labels_for_group(key: str) -> dict[str, tuple[str, ...]]:
    return issue_form_labels_by_path(issue_form_paths_for_group(key))


def validate_issue_form_policy() -> None:
    specs = required_issue_form_specs()
    _validate_unique(
        (spec.path for spec in specs),
        duplicate_error_prefix="duplicate issue form path",
    )
    _validate_unique(
        (spec.name for spec in specs),
        duplicate_error_prefix="duplicate issue form name",
    )
    for spec in specs:
        if not spec.path:
            raise ValueError("issue form path must not be empty")
        if not spec.name:
            raise ValueError("issue form name must not be empty: " + spec.path)
        if not spec.title:
            raise ValueError("issue form title must not be empty: " + spec.path)
        if not spec.fields:
            raise ValueError("issue form must define field contracts: " + spec.path)
        if not spec.labels:
            raise ValueError("issue form must define labels: " + spec.path)
        _validate_unique(
            spec.labels,
            duplicate_error_prefix="duplicate issue form label",
        )
        _validate_unique(
            (field.key for field in spec.fields),
            duplicate_error_prefix="duplicate issue form field key",
        )
        _validate_unique(
            (field.label for field in spec.fields),
            duplicate_error_prefix="duplicate issue form field label",
        )
        for field in spec.fields:
            if not field.key:
                raise ValueError("issue form field key must not be empty: " + spec.path)
            if not field.label:
                raise ValueError(
                    "issue form field label must not be empty: " + spec.path
                )
        for label in spec.labels:
            if not label:
                raise ValueError("issue form label must not be empty: " + spec.path)
    _validate_issue_form_groups(
        required_issue_form_group_specs(),
        registered_paths=frozenset(spec.path for spec in specs),
    )


def _copy_field_specs(
    fields: Iterable[IssueFormFieldLike],
) -> tuple[IssueFormFieldSpec, ...]:
    return tuple(
        IssueFormFieldSpec(
            key=field.key,
            label=field.label,
            required=field.required,
        )
        for field in fields
    )


def _validate_unique(
    values: Iterable[str],
    *,
    duplicate_error_prefix: str,
) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"{duplicate_error_prefix}: {value}")
        seen.add(value)


def _validate_issue_form_groups(
    specs: Iterable[IssueFormGroupSpec],
    *,
    registered_paths: frozenset[str],
) -> None:
    _validate_unique(
        (spec.key for spec in specs),
        duplicate_error_prefix="duplicate issue form group",
    )
    for spec in specs:
        if not spec.key:
            raise ValueError("issue form group key must not be empty")
        if not spec.paths:
            raise ValueError("issue form group must define paths: " + spec.key)
        _validate_unique(
            spec.paths,
            duplicate_error_prefix="duplicate issue form group path",
        )
        for path in spec.paths:
            if path not in registered_paths:
                raise ValueError(
                    "issue form group references unknown path: "
                    + spec.key
                    + " -> "
                    + path
                )
