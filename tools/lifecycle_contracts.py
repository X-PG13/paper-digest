from __future__ import annotations

import json
from dataclasses import dataclass

from tools.docs_contracts import (
    FileTextSource,
    MarkdownSectionSource,
    TextSource,
    WorkflowSectionSource,
)
from tools.issue_form_policy import (
    RELEASE_LIFECYCLE_ISSUE_FORM_GROUP,
    issue_form_paths_for_group,
)

RELEASE_LIFECYCLE_ISSUE_FORM_PATHS = issue_form_paths_for_group(
    RELEASE_LIFECYCLE_ISSUE_FORM_GROUP
)
(
    RELEASE_PREPARATION_FORM_PATH,
    POST_RELEASE_FOLLOW_UP_FORM_PATH,
) = RELEASE_LIFECYCLE_ISSUE_FORM_PATHS


@dataclass(frozen=True)
class IssueFormFieldContract:
    field_id: str
    label: str
    checklist_items: tuple[str, ...] = ()


@dataclass(frozen=True)
class SummaryContract:
    name: str
    doc_heading: str
    doc_prefix_fields: tuple[tuple[str, str], ...]
    doc_fields: tuple[tuple[str, str], ...]
    doc_suffix_fields: tuple[tuple[str, str], ...]
    workflow_prefix_lines: tuple[str, ...]
    workflow_defaults: tuple[tuple[str, str], ...]
    workflow_suffix_lines: tuple[str, ...]
    doc_none_guidance: str
    doc_prefill_guidance_lines: tuple[str, ...]
    guidance_snippets: tuple[str, ...]


@dataclass(frozen=True)
class TextContractExpectation:
    subject: str
    snippets: tuple[str, ...]


@dataclass(frozen=True)
class TextContract:
    name: str
    expectations: tuple[TextContractExpectation, ...]


@dataclass(frozen=True)
class GeneratedManagedBlock:
    path: str
    marker: str
    content: str
    begin_marker_override: str | None = None
    end_marker_override: str | None = None

    @property
    def begin_marker(self) -> str:
        if self.begin_marker_override is not None:
            return self.begin_marker_override
        return f"<!-- BEGIN GENERATED: {self.marker} -->"

    @property
    def end_marker(self) -> str:
        if self.end_marker_override is not None:
            return self.end_marker_override
        return f"<!-- END GENERATED: {self.marker} -->"


def text_contract(
    name: str,
    expectations: dict[str, tuple[str, ...]],
) -> TextContract:
    return TextContract(
        name=name,
        expectations=tuple(
            TextContractExpectation(subject=subject, snippets=snippets)
            for subject, snippets in expectations.items()
        ),
    )


RELEASING_BEFORE_TAGGING_SOURCE = MarkdownSectionSource(
    label="RELEASING.md#Before Tagging",
    path="RELEASING.md",
    heading="Before Tagging",
    visible_only=False,
)
RELEASING_AFTER_RELEASE_SOURCE = MarkdownSectionSource(
    label="RELEASING.md#After Release",
    path="RELEASING.md",
    heading="After Release",
    visible_only=False,
)
RELEASING_DRAFT_RELEASE_NOTES_SOURCE = MarkdownSectionSource(
    label="RELEASING.md#Draft Release Notes",
    path="RELEASING.md",
    heading="Draft Release Notes",
    visible_only=False,
)
RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE = MarkdownSectionSource(
    label="docs/release-lifecycle-runbook.md#Linkage Rules",
    path="docs/release-lifecycle-runbook.md",
    heading="Linkage Rules",
    visible_only=False,
)
RELEASE_LIFECYCLE_PREP_RESPONSIBILITIES_SOURCE = MarkdownSectionSource(
    label="docs/release-lifecycle-runbook.md#Release-Prep Responsibilities",
    path="docs/release-lifecycle-runbook.md",
    heading="Release-Prep Responsibilities",
    visible_only=False,
)
RELEASE_LIFECYCLE_POST_RELEASE_RESPONSIBILITIES_SOURCE = MarkdownSectionSource(
    label="docs/release-lifecycle-runbook.md#Post-Release Responsibilities",
    path="docs/release-lifecycle-runbook.md",
    heading="Post-Release Responsibilities",
    visible_only=False,
)
RELEASE_LIFECYCLE_CLOSE_OUT_SOURCE = MarkdownSectionSource(
    label="docs/release-lifecycle-runbook.md#Issue Close-Out Expectations",
    path="docs/release-lifecycle-runbook.md",
    heading="Issue Close-Out Expectations",
    visible_only=False,
)
QUARTERLY_REVIEW_RELEASE_LINKAGE_SOURCE = MarkdownSectionSource(
    label="docs/quarterly-maintainer-review.md#Release Linkage",
    path="docs/quarterly-maintainer-review.md",
    heading="Release Linkage",
    visible_only=False,
)
QUARTERLY_REVIEW_CLOSE_OUT_SOURCE = MarkdownSectionSource(
    label="docs/quarterly-maintainer-review.md#Close-Out Expectations",
    path="docs/quarterly-maintainer-review.md",
    heading="Close-Out Expectations",
    visible_only=False,
)
QUARTERLY_REVIEW_SUMMARY_SOURCE = MarkdownSectionSource(
    label="docs/quarterly-maintainer-review.md#Review Summary Template",
    path="docs/quarterly-maintainer-review.md",
    heading="Review Summary Template",
    visible_only=False,
)
POST_RELEASE_REPOSITORY_FOLLOW_UP_SOURCE = MarkdownSectionSource(
    label="docs/post-release-checklist.md#Repository Follow-Up",
    path="docs/post-release-checklist.md",
    heading="Repository Follow-Up",
    visible_only=False,
)
POST_RELEASE_CLOSE_OUT_SOURCE = MarkdownSectionSource(
    label="docs/post-release-checklist.md#Close-Out Expectations",
    path="docs/post-release-checklist.md",
    heading="Close-Out Expectations",
    visible_only=False,
)
POST_RELEASE_SUMMARY_SOURCE = MarkdownSectionSource(
    label="docs/post-release-checklist.md#Follow-Up Summary Template",
    path="docs/post-release-checklist.md",
    heading="Follow-Up Summary Template",
    visible_only=False,
)
RELEASE_PREP_FORM_SOURCE = FileTextSource(
    label=RELEASE_PREPARATION_FORM_PATH,
    path=RELEASE_PREPARATION_FORM_PATH,
)
POST_RELEASE_FORM_SOURCE = FileTextSource(
    label=POST_RELEASE_FOLLOW_UP_FORM_PATH,
    path=POST_RELEASE_FOLLOW_UP_FORM_PATH,
)
QUARTERLY_REVIEW_WORKFLOW_FILE_SOURCE = FileTextSource(
    label=".github/workflows/quarterly-maintainer-review.yml",
    path=".github/workflows/quarterly-maintainer-review.yml",
)
POST_RELEASE_WORKFLOW_FILE_SOURCE = FileTextSource(
    label=".github/workflows/post-release-follow-up.yml",
    path=".github/workflows/post-release-follow-up.yml",
)
POST_RELEASE_WORKFLOW_INTRO_SOURCE = WorkflowSectionSource(
    label=".github/workflows/post-release-follow-up.yml#Intro",
    path=".github/workflows/post-release-follow-up.yml",
)
QUARTERLY_REVIEW_WORKFLOW_CLOSE_OUT_SOURCE = WorkflowSectionSource(
    label=".github/workflows/quarterly-maintainer-review.yml#Close-Out",
    path=".github/workflows/quarterly-maintainer-review.yml",
    section="Close-Out",
)
QUARTERLY_REVIEW_WORKFLOW_SUMMARY_SOURCE = WorkflowSectionSource(
    label=".github/workflows/quarterly-maintainer-review.yml#Review Summary",
    path=".github/workflows/quarterly-maintainer-review.yml",
    section="Review Summary",
)
POST_RELEASE_WORKFLOW_SUMMARY_SOURCE = WorkflowSectionSource(
    label=".github/workflows/post-release-follow-up.yml#Post-Release Summary",
    path=".github/workflows/post-release-follow-up.yml",
    section="Post-Release Summary",
)

RELEASE_LIFECYCLE_TEXT_SOURCES = (
    RELEASING_BEFORE_TAGGING_SOURCE,
    RELEASING_AFTER_RELEASE_SOURCE,
    RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE,
    RELEASE_LIFECYCLE_PREP_RESPONSIBILITIES_SOURCE,
    RELEASE_LIFECYCLE_POST_RELEASE_RESPONSIBILITIES_SOURCE,
    RELEASE_PREP_FORM_SOURCE,
    POST_RELEASE_FORM_SOURCE,
)

MAINTAINER_ISSUE_TEXT_SOURCES = (
    RELEASING_DRAFT_RELEASE_NOTES_SOURCE,
    QUARTERLY_REVIEW_CLOSE_OUT_SOURCE,
    QUARTERLY_REVIEW_SUMMARY_SOURCE,
    POST_RELEASE_CLOSE_OUT_SOURCE,
    POST_RELEASE_SUMMARY_SOURCE,
    QUARTERLY_REVIEW_WORKFLOW_FILE_SOURCE,
    POST_RELEASE_WORKFLOW_FILE_SOURCE,
    RELEASE_PREP_FORM_SOURCE,
    POST_RELEASE_FORM_SOURCE,
)

ISSUE_LINKAGE_TEXT_SOURCES = (
    RELEASING_BEFORE_TAGGING_SOURCE,
    RELEASING_AFTER_RELEASE_SOURCE,
    RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE,
    QUARTERLY_REVIEW_RELEASE_LINKAGE_SOURCE,
    POST_RELEASE_REPOSITORY_FOLLOW_UP_SOURCE,
    POST_RELEASE_WORKFLOW_INTRO_SOURCE,
)

ISSUE_CLOSE_OUT_TEXT_SOURCES = (
    RELEASING_AFTER_RELEASE_SOURCE,
    RELEASE_LIFECYCLE_CLOSE_OUT_SOURCE,
    QUARTERLY_REVIEW_CLOSE_OUT_SOURCE,
    POST_RELEASE_CLOSE_OUT_SOURCE,
)


ISSUE_LINKAGE_TEXT_CONTRACTS = (
    text_contract(
        "quarterly review handoff",
        {
            QUARTERLY_REVIEW_RELEASE_LINKAGE_SOURCE.label: (
                "latest quarterly review issue",
                "release-preparation pull request",
                "maintainer notes",
            ),
            RELEASING_BEFORE_TAGGING_SOURCE.label: (
                "latest quarterly review issue is current",
            ),
        },
    ),
    text_contract(
        "release-prep linkage fields",
        {
            RELEASING_BEFORE_TAGGING_SOURCE.label: (
                "release-preparation issue linked",
                "release-preparation pull request",
            ),
            RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE.label: (
                (
                    "release-preparation issue should link the latest "
                    "quarterly review issue"
                ),
                (
                    "release-preparation pull request should link the "
                    "release-preparation issue"
                ),
            ),
        },
    ),
    text_contract(
        "post-release linkage fields",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: (
                "Post-release follow-up",
                "linked from the release-preparation issue",
            ),
            RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE.label: (
                (
                    "post-release follow-up issue should link the "
                    "release-preparation issue"
                ),
                "update the release-preparation issue",
            ),
            POST_RELEASE_WORKFLOW_INTRO_SOURCE.label: (
                "Release: ${releaseUrl}",
                "linked release-preparation issue",
            ),
        },
    ),
    text_contract(
        "post-release quarterly review linkage",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: (
                "quarterly review issue",
                "repository-operations changes",
            ),
            RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE.label: (
                "quarterly review issue",
                "repository-operations changes",
            ),
            POST_RELEASE_REPOSITORY_FOLLOW_UP_SOURCE.label: (
                "quarterly maintainer review linkage remains valid",
            ),
            POST_RELEASE_WORKFLOW_INTRO_SOURCE.label: (
                "quarterly review issue",
                "repository-operations changes",
            ),
        },
    ),
)

ISSUE_LINKAGE_RELEASE_PREP_FORM_FIELDS = (
    IssueFormFieldContract(
        field_id="quarterly_review",
        label="Latest quarterly review issue",
    ),
    IssueFormFieldContract(
        field_id="follow_up",
        label="Release and post-release follow-up",
        checklist_items=(
            "Release-preparation PR linked here.",
            "Post-release follow-up issue linked after publication.",
        ),
    ),
)

ISSUE_LINKAGE_POST_RELEASE_FORM_FIELDS = (
    IssueFormFieldContract(
        field_id="release_prep_issue",
        label="Release-preparation issue",
    ),
    IssueFormFieldContract(
        field_id="published_release_url",
        label="Published release URL",
    ),
    IssueFormFieldContract(
        field_id="quarterly_review_issue",
        label="Latest quarterly review issue",
    ),
)

ISSUE_CLOSE_OUT_TEXT_CONTRACTS = (
    text_contract(
        "quarterly review close-out rule",
        {
            RELEASE_LIFECYCLE_CLOSE_OUT_SOURCE.label: (
                "Close quarterly maintainer review issues",
                "none explicitly",
            ),
            QUARTERLY_REVIEW_CLOSE_OUT_SOURCE.label: (
                "short summary",
                "no changes were",
                "follow-up work explicitly",
            ),
        },
    ),
    text_contract(
        "release-preparation close-out rule",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: (
                "Close the release-preparation issue",
                "remaining immediate follow-up work",
                "none",
            ),
            RELEASE_LIFECYCLE_CLOSE_OUT_SOURCE.label: (
                "Close release-preparation issues",
                "post-release follow-up issue is linked",
                "none explicitly",
            ),
        },
    ),
    text_contract(
        "post-release close-out rule",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: (
                "post-release issue before closing it",
                "remaining work",
                "none",
            ),
            RELEASE_LIFECYCLE_CLOSE_OUT_SOURCE.label: (
                "Close post-release follow-up issues",
                "remaining follow-up work",
                "none explicitly",
            ),
            POST_RELEASE_CLOSE_OUT_SOURCE.label: (
                "short summary of what was verified or changed",
                "follow-up pull request or maintenance issue",
                "no additional work was needed",
            ),
        },
    ),
)

RELEASE_LIFECYCLE_TEXT_CONTRACTS = (
    text_contract(
        "release prep changelog",
        {
            RELEASING_BEFORE_TAGGING_SOURCE.label: ("CHANGELOG.md",),
            RELEASE_PREP_FORM_SOURCE.label: (
                "CHANGELOG.md updated",
            ),
        },
    ),
    text_contract(
        "release prep version confirmation",
        {
            RELEASING_BEFORE_TAGGING_SOURCE.label: ("paper_digest/__about__.py",),
            RELEASE_PREP_FORM_SOURCE.label: (
                "paper_digest/__about__.py",
            ),
        },
    ),
    text_contract(
        "release prep verification suite",
        {
            RELEASING_BEFORE_TAGGING_SOURCE.label: (
                "make check",
                "make build",
                "make release-check",
            ),
            RELEASE_PREP_FORM_SOURCE.label: (
                "make check",
                "make build",
                "make release-check",
            ),
        },
    ),
    text_contract(
        "quarterly review currency",
        {
            RELEASING_BEFORE_TAGGING_SOURCE.label: (
                "latest quarterly review issue is current",
            ),
            RELEASE_LIFECYCLE_PREP_RESPONSIBILITIES_SOURCE.label: (
                "latest quarterly review is still current",
            ),
            RELEASE_PREP_FORM_SOURCE.label: (
                "latest quarterly maintainer review issue is current",
            ),
        },
    ),
    text_contract(
        "release-prep issue linkage",
        {
            RELEASING_BEFORE_TAGGING_SOURCE.label: ("release-preparation issue",),
            RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE.label: (
                "release-preparation issue",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "release-preparation issue",
            ),
        },
    ),
    text_contract(
        "release-prep pr linkage",
        {
            RELEASING_BEFORE_TAGGING_SOURCE.label: (
                "release-preparation pull request",
            ),
            RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE.label: (
                "release-preparation pull request",
            ),
            RELEASE_PREP_FORM_SOURCE.label: (
                "Release-preparation PR linked here",
            ),
        },
    ),
    text_contract(
        "post-release issue linkage",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: (
                "Post-release follow-up",
                "linked",
            ),
            RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE.label: (
                "post-release follow-up issue",
            ),
            RELEASE_PREP_FORM_SOURCE.label: (
                "Post-release follow-up issue linked after publication",
            ),
        },
    ),
    text_contract(
        "artifact verification",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: ("wheel and source archive",),
            RELEASE_LIFECYCLE_POST_RELEASE_RESPONSIBILITIES_SOURCE.label: (
                "published release artifacts",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "GitHub release artifacts verified",
            ),
        },
    ),
    text_contract(
        "release notes verification",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: (
                "generated release notes",
                "CHANGELOG.md",
            ),
            RELEASE_LIFECYCLE_POST_RELEASE_RESPONSIBILITIES_SOURCE.label: (
                "release notes",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "Generated release notes match",
                "CHANGELOG.md",
            ),
        },
    ),
    text_contract(
        "compatibility verification",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: (
                "README.md",
                "docs/compatibility-matrix.md",
            ),
            RELEASE_LIFECYCLE_POST_RELEASE_RESPONSIBILITIES_SOURCE.label: (
                "compatibility claims",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "README.md",
                "docs/compatibility-matrix.md",
            ),
        },
    ),
    text_contract(
        "next-cycle version bump",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: ("Bump the version",),
            RELEASE_LIFECYCLE_POST_RELEASE_RESPONSIBILITIES_SOURCE.label: (
                "next-cycle setup",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "Next development-cycle version bump",
            ),
        },
    ),
    text_contract(
        "unreleased reset",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: ("Unreleased",),
            RELEASE_LIFECYCLE_POST_RELEASE_RESPONSIBILITIES_SOURCE.label: (
                "next-cycle setup",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "Unreleased",
            ),
        },
    ),
    text_contract(
        "operations history update",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: ("docs/operations-history.md",),
            RELEASE_LIFECYCLE_LINKAGE_RULES_SOURCE.label: (
                "docs/operations-history.md",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "docs/operations-history.md updated",
            ),
        },
    ),
    text_contract(
        "retrospective capture",
        {
            RELEASING_AFTER_RELEASE_SOURCE.label: ("release retrospective",),
            RELEASE_LIFECYCLE_POST_RELEASE_RESPONSIBILITIES_SOURCE.label: (
                "retrospective",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "Release retrospective",
            ),
        },
    ),
)

MAINTAINER_ISSUE_TEXT_CONTRACTS = (
    text_contract(
        "release-prep scope summary",
        {
            RELEASING_DRAFT_RELEASE_NOTES_SOURCE.label: (
                "Highlights:",
                "Config or workflow changes:",
                "Compatibility notes:",
                "Upgrade notes:",
                "Repository-operations notes:",
            ),
            RELEASE_PREP_FORM_SOURCE.label: (
                "Highlights:",
                "Config or workflow changes:",
                "Compatibility notes:",
                "Upgrade notes:",
                "Repository-operations notes:",
            ),
        },
    ),
    text_contract(
        "quarterly review close-out",
        {
            QUARTERLY_REVIEW_CLOSE_OUT_SOURCE.label: (
                "short summary",
                "no changes were",
                "follow-up work explicitly",
            ),
            QUARTERLY_REVIEW_WORKFLOW_FILE_SOURCE.label: (
                "## Close-Out",
                "Link any follow-up issue or pull request here.",
                "If no changes were needed, say so explicitly before closing.",
            ),
        },
    ),
    text_contract(
        "quarterly review summary template",
        {
            QUARTERLY_REVIEW_SUMMARY_SOURCE.label: (
                "## Review Summary",
                "- Review date:",
                "- Reviewed by:",
                "- Access changes:",
                "- Repository-settings drift:",
                "- Docs updated:",
                "- Follow-up work:",
                "- Release impact:",
                "- Next review due:",
            ),
            QUARTERLY_REVIEW_WORKFLOW_FILE_SOURCE.label: (
                "## Review Summary",
                "- Review date:",
                "- Reviewed by:",
                "- Access changes:",
                "- Repository-settings drift:",
                "- Docs updated:",
                "- Follow-up work:",
                "- Release impact:",
                "- Next review due:",
            ),
        },
    ),
    text_contract(
        "post-release close-out",
        {
            POST_RELEASE_CLOSE_OUT_SOURCE.label: (
                "short summary of what was verified or changed",
                "follow-up pull request or maintenance issue",
                "no additional work was needed",
            ),
            POST_RELEASE_FORM_SOURCE.label: (
                "Close-out summary",
                "Post-release summary added.",
                "Follow-up PRs or issues linked.",
                (
                    "No remaining immediate post-release work, or remaining "
                    "work is explicitly tracked."
                ),
            ),
        },
    ),
    text_contract(
        "post-release summary template",
        {
            POST_RELEASE_SUMMARY_SOURCE.label: (
                "## Post-Release Summary",
                "- Release:",
                "- Verified by:",
                "- Artifacts and release notes:",
                "- Compatibility and docs drift:",
                "- Next-cycle setup:",
                "- Retro follow-up:",
                "- Additional repository-operations follow-up:",
            ),
            POST_RELEASE_WORKFLOW_FILE_SOURCE.label: (
                "## Post-Release Summary",
                "- Release:",
                "- Verified by:",
                "- Artifacts and release notes:",
                "- Compatibility and docs drift:",
                "- Next-cycle setup:",
                "- Retro follow-up:",
                "- Additional repository-operations follow-up:",
            ),
        },
    ),
)

QUARTERLY_CLOSE_OUT_WORKFLOW_ITEMS = (
    "Link any follow-up issue or pull request here.",
    "If no changes were needed, say so explicitly before closing.",
)

QUARTERLY_CLOSE_OUT_DOC_ITEMS = (
    (
        "close the issue with a short summary of what changed or that no "
        "changes were needed"
    ),
    "update any affected docs in the same pull request if drift was found",
    "mention follow-up work explicitly if the review uncovered deferred cleanup",
)

RELEASE_PREP_SCOPE_SUMMARY_PLACEHOLDER_LINES = (
    "- Highlights:",
    "- Config or workflow changes:",
    "- Compatibility notes:",
    "- Upgrade notes:",
    "- Repository-operations notes:",
)

RELEASE_PREP_COMPATIBILITY_AND_REPO_OPS_FORM_FIELD = IssueFormFieldContract(
    field_id="compatibility_and_repo_ops",
    label="Compatibility and repository-operations checks",
    checklist_items=(
        "`docs/compatibility-matrix.md` reviewed.",
        "README compatibility summary still matches the supported surface.",
        (
            "`docs/branch-protection-policy.md`, "
            "`docs/ruleset-policy.md`, and "
            "`docs/repository-settings-checklist.md` still match the "
            "intended GitHub configuration."
        ),
        (
            "The latest quarterly maintainer review issue is current, or "
            "any deferral is explained here."
        ),
    ),
)

RELEASE_PREP_CHANGELOG_AND_NOTES_FORM_FIELD = IssueFormFieldContract(
    field_id="changelog_and_notes",
    label="Changelog and release-notes intent",
    checklist_items=(
        "`CHANGELOG.md` updated.",
        "Release-note-worthy changes identified.",
        (
            "Compatibility, workflow, or operator-facing changes called out "
            "explicitly."
        ),
        (
            "Generated GitHub release-note categories still match the labels "
            "used in this cycle."
        ),
    ),
)

RELEASE_PREP_VALIDATION_FORM_FIELD = IssueFormFieldContract(
    field_id="validation",
    label="Validation checklist",
    checklist_items=(
        "`make check`",
        "`make build`",
        "`make release-check`",
        "Version in `paper_digest/__about__.py` confirmed.",
    ),
)

RELEASE_PREP_FOLLOW_UP_FORM_ITEMS = (
    "Release-preparation PR linked here.",
    "Post-release follow-up issue linked after publication.",
    "Tag pushed.",
    "GitHub release artifacts verified.",
    "Next development-cycle version bump or follow-up issue noted.",
)

RELEASE_PREP_CLOSE_OUT_FORM_FIELD = IssueFormFieldContract(
    field_id="close_out",
    label="Close-out handoff",
    checklist_items=(
        "Post-release follow-up issue linked here.",
        (
            "Any remaining immediate follow-up work is linked there, or "
            "`none` is stated explicitly."
        ),
        "Release-preparation summary or maintainer notes are complete.",
    ),
)

POST_RELEASE_CLOSE_OUT_FORM_FIELD = IssueFormFieldContract(
    field_id="close_out",
    label="Close-out summary",
    checklist_items=(
        "Post-release summary added.",
        "Follow-up PRs or issues linked.",
        (
            "No remaining immediate post-release work, or remaining work is "
            "explicitly tracked."
        ),
    ),
)

POST_RELEASE_CLOSE_OUT_DOC_ITEMS = (
    "close the issue with a short summary of what was verified or changed",
    "link any follow-up pull request or maintenance issue",
    "note explicitly if no additional work was needed",
)

POST_RELEASE_IMMEDIATE_VALIDATION_FORM_FIELD = IssueFormFieldContract(
    field_id="immediate_validation",
    label="Immediate validation",
    checklist_items=(
        "GitHub release artifacts verified.",
        "Generated release notes match `CHANGELOG.md`.",
        (
            "Compatibility claims in `README.md` and "
            "`docs/compatibility-matrix.md` still match the published release."
        ),
        (
            "Operator-facing workflow or repository-operations notes were "
            "surfaced in release prep and release notes."
        ),
    ),
)

POST_RELEASE_NEXT_CYCLE_FORM_FIELD = IssueFormFieldContract(
    field_id="next_cycle",
    label="Next-cycle setup",
    checklist_items=(
        "Next development-cycle version bump tracked or completed.",
        "`CHANGELOG.md` has an `Unreleased` section ready for new work.",
        "Deferred release-preparation follow-up work is linked here.",
        "`docs/operations-history.md` updated.",
    ),
)

POST_RELEASE_RETROSPECTIVE_PLACEHOLDER_LINES = (
    "- What went smoothly?",
    "- What was repetitive or unclear?",
    "- What should be automated or documented next?",
)

QUARTERLY_SUMMARY_CONTRACT = SummaryContract(
    name="quarterly summary semantics",
    doc_heading="Review Summary",
    doc_prefix_fields=(
        ("Review date", "YYYY-MM-DD"),
        ("Reviewed by", "@maintainer"),
    ),
    doc_fields=(
        ("Access changes", "none | short summary"),
        ("Repository-settings drift", "none | short summary"),
        ("Docs updated", "none | PR or file list"),
        ("Follow-up work", "none | issue or PR links"),
        ("Release impact", "none | operator-facing note"),
    ),
    doc_suffix_fields=(("Next review due", "YYYY-MM-DD"),),
    workflow_prefix_lines=(
        "- Review date:",
        "- Reviewed by:",
    ),
    workflow_defaults=(
        ("Access changes", "none"),
        ("Repository-settings drift", "none"),
        ("Docs updated", "none"),
        ("Follow-up work", "none"),
        ("Release impact", "none"),
    ),
    workflow_suffix_lines=("- Next review due:",),
    doc_none_guidance="Write `none` explicitly when no changes were required.",
    doc_prefill_guidance_lines=(
        "The scheduled workflow should prefill the mutable summary fields with `none`;",
        "replace `none` with a short summary, file list, or issue/PR links only where",
        "the review changed something.",
    ),
    guidance_snippets=("prefill the mutable summary fields with `none`",),
)

POST_RELEASE_SUMMARY_CONTRACT = SummaryContract(
    name="post-release summary semantics",
    doc_heading="Post-Release Summary",
    doc_prefix_fields=(
        ("Release", "vX.Y.Z"),
        ("Verified by", "@maintainer"),
    ),
    doc_fields=(
        ("Artifacts and release notes", "confirmed | short summary"),
        ("Compatibility and docs drift", "none | short summary"),
        ("Next-cycle setup", "complete | short summary"),
        ("Retro follow-up", "none | issue or PR links"),
        ("Additional repository-operations follow-up", "none | short summary"),
    ),
    doc_suffix_fields=(),
    workflow_prefix_lines=(
        "- Release: ${tag}",
        "- Verified by:",
    ),
    workflow_defaults=(
        ("Artifacts and release notes", "confirmed"),
        ("Compatibility and docs drift", "none"),
        ("Next-cycle setup", "complete"),
        ("Retro follow-up", "none"),
        ("Additional repository-operations follow-up", "none"),
    ),
    workflow_suffix_lines=(),
    doc_none_guidance=(
        "Write `none` explicitly when no additional work was required."
    ),
    doc_prefill_guidance_lines=(
        "The release-triggered workflow should prefill the mutable status fields as",
        "`confirmed`, `none`, `complete`, `none`, and `none`; replace those defaults",
        "with a short summary or issue/PR links only where follow-up exists.",
    ),
    guidance_snippets=(
        (
            "prefill the mutable status fields as `confirmed`, `none`, "
            "`complete`, `none`, and `none`"
        ),
    ),
)


@dataclass(frozen=True)
class SummarySourceBinding:
    contract: SummaryContract
    doc_source: MarkdownSectionSource
    workflow_source: WorkflowSectionSource


SUMMARY_CONTRACTS = (
    QUARTERLY_SUMMARY_CONTRACT,
    POST_RELEASE_SUMMARY_CONTRACT,
)

ISSUE_SUMMARY_SOURCE_BINDINGS = (
    SummarySourceBinding(
        contract=QUARTERLY_SUMMARY_CONTRACT,
        doc_source=QUARTERLY_REVIEW_SUMMARY_SOURCE,
        workflow_source=QUARTERLY_REVIEW_WORKFLOW_SUMMARY_SOURCE,
    ),
    SummarySourceBinding(
        contract=POST_RELEASE_SUMMARY_CONTRACT,
        doc_source=POST_RELEASE_SUMMARY_SOURCE,
        workflow_source=POST_RELEASE_WORKFLOW_SUMMARY_SOURCE,
    ),
)


def render_markdown_bullets(items: tuple[str, ...]) -> str:
    return "\n".join(f"- {item}" for item in items)


def render_summary_doc_block(contract: SummaryContract) -> str:
    lines = ["```md", f"## {contract.doc_heading}", ""]
    field_rows = (
        contract.doc_prefix_fields
        + contract.doc_fields
        + contract.doc_suffix_fields
    )
    lines.extend(f"- {label}: {value}" for label, value in field_rows)
    lines.extend(
        [
            "```",
            "",
            contract.doc_none_guidance,
            *contract.doc_prefill_guidance_lines,
        ]
    )
    return "\n".join(lines)


def render_summary_workflow_lines(contract: SummaryContract) -> tuple[str, ...]:
    return (
        contract.workflow_prefix_lines
        + tuple(
            f"- {label}: {value}" for label, value in contract.workflow_defaults
        )
        + contract.workflow_suffix_lines
    )


def render_issue_form_literal_block(
    key: str,
    lines: tuple[str, ...],
    *,
    indent: str = "      ",
) -> str:
    rendered_lines = [f"{indent}{key}: |"]
    rendered_lines.extend(f"{indent}  {line}" for line in lines)
    return "\n".join(rendered_lines)


def render_issue_form_checklist_block(
    items: tuple[str, ...],
    *,
    indent: str = "      ",
) -> str:
    return render_issue_form_literal_block(
        "value",
        tuple(f"- [ ] {item}" for item in items),
        indent=indent,
    )


def render_workflow_body_items(
    lines: tuple[str, ...],
    *,
    indent: str = "              ",
    raw_lines: dict[int, str] | None = None,
) -> str:
    raw_lines = {} if raw_lines is None else raw_lines
    rendered_lines: list[str] = []
    for index, line in enumerate(lines):
        source = raw_lines.get(index, json.dumps(line))
        rendered_lines.append(f"{indent}{source},")
    return "\n".join(rendered_lines)


def managed_markdown_block(
    path: str,
    marker: str,
    content: str,
) -> GeneratedManagedBlock:
    return GeneratedManagedBlock(path=path, marker=marker, content=content)


def managed_yaml_block(
    path: str,
    marker: str,
    content: str,
    *,
    indent: str = "      ",
) -> GeneratedManagedBlock:
    return GeneratedManagedBlock(
        path=path,
        marker=marker,
        content=content,
        begin_marker_override=f"{indent}# BEGIN GENERATED: {marker}",
        end_marker_override=f"{indent}# END GENERATED: {marker}",
    )


def managed_workflow_block(
    path: str,
    marker: str,
    content: str,
    *,
    indent: str = "              ",
) -> GeneratedManagedBlock:
    return GeneratedManagedBlock(
        path=path,
        marker=marker,
        content=content,
        begin_marker_override=f"{indent}// BEGIN GENERATED: {marker}",
        end_marker_override=f"{indent}// END GENERATED: {marker}",
    )


def iter_generated_lifecycle_blocks() -> tuple[GeneratedManagedBlock, ...]:
    return (
        managed_markdown_block(
            "docs/quarterly-maintainer-review.md",
            "quarterly-review-close-out",
            render_markdown_bullets(QUARTERLY_CLOSE_OUT_DOC_ITEMS),
        ),
        managed_markdown_block(
            "docs/quarterly-maintainer-review.md",
            "quarterly-review-summary",
            render_summary_doc_block(QUARTERLY_SUMMARY_CONTRACT),
        ),
        managed_markdown_block(
            "docs/post-release-checklist.md",
            "post-release-close-out",
            render_markdown_bullets(POST_RELEASE_CLOSE_OUT_DOC_ITEMS),
        ),
        managed_markdown_block(
            "docs/post-release-checklist.md",
            "post-release-summary",
            render_summary_doc_block(POST_RELEASE_SUMMARY_CONTRACT),
        ),
        managed_yaml_block(
            RELEASE_PREPARATION_FORM_PATH,
            "release-prep-form-scope-summary",
            render_issue_form_literal_block(
                "placeholder",
                RELEASE_PREP_SCOPE_SUMMARY_PLACEHOLDER_LINES,
            ),
        ),
        managed_yaml_block(
            RELEASE_PREPARATION_FORM_PATH,
            "release-prep-form-compatibility",
            render_issue_form_checklist_block(
                RELEASE_PREP_COMPATIBILITY_AND_REPO_OPS_FORM_FIELD.checklist_items,
            ),
        ),
        managed_yaml_block(
            RELEASE_PREPARATION_FORM_PATH,
            "release-prep-form-changelog",
            render_issue_form_checklist_block(
                RELEASE_PREP_CHANGELOG_AND_NOTES_FORM_FIELD.checklist_items,
            ),
        ),
        managed_yaml_block(
            RELEASE_PREPARATION_FORM_PATH,
            "release-prep-form-validation",
            render_issue_form_checklist_block(
                RELEASE_PREP_VALIDATION_FORM_FIELD.checklist_items,
            ),
        ),
        managed_yaml_block(
            RELEASE_PREPARATION_FORM_PATH,
            "release-prep-form-follow-up",
            render_issue_form_checklist_block(RELEASE_PREP_FOLLOW_UP_FORM_ITEMS),
        ),
        managed_yaml_block(
            RELEASE_PREPARATION_FORM_PATH,
            "release-prep-form-close-out",
            render_issue_form_checklist_block(
                RELEASE_PREP_CLOSE_OUT_FORM_FIELD.checklist_items,
            ),
        ),
        managed_yaml_block(
            POST_RELEASE_FOLLOW_UP_FORM_PATH,
            "post-release-form-immediate-validation",
            render_issue_form_checklist_block(
                POST_RELEASE_IMMEDIATE_VALIDATION_FORM_FIELD.checklist_items,
            ),
        ),
        managed_yaml_block(
            POST_RELEASE_FOLLOW_UP_FORM_PATH,
            "post-release-form-next-cycle",
            render_issue_form_checklist_block(
                POST_RELEASE_NEXT_CYCLE_FORM_FIELD.checklist_items,
            ),
        ),
        managed_yaml_block(
            POST_RELEASE_FOLLOW_UP_FORM_PATH,
            "post-release-form-retrospective",
            render_issue_form_literal_block(
                "placeholder",
                POST_RELEASE_RETROSPECTIVE_PLACEHOLDER_LINES,
            ),
        ),
        managed_yaml_block(
            POST_RELEASE_FOLLOW_UP_FORM_PATH,
            "post-release-form-close-out",
            render_issue_form_checklist_block(
                POST_RELEASE_CLOSE_OUT_FORM_FIELD.checklist_items,
            ),
        ),
        managed_workflow_block(
            ".github/workflows/quarterly-maintainer-review.yml",
            "quarterly-review-workflow-close-out",
            render_workflow_body_items(
                tuple(f"- {item}" for item in QUARTERLY_CLOSE_OUT_WORKFLOW_ITEMS),
            ),
        ),
        managed_workflow_block(
            ".github/workflows/quarterly-maintainer-review.yml",
            "quarterly-review-workflow-summary",
            render_workflow_body_items(
                render_summary_workflow_lines(QUARTERLY_SUMMARY_CONTRACT),
            ),
        ),
        managed_workflow_block(
            ".github/workflows/post-release-follow-up.yml",
            "post-release-workflow-summary",
            render_workflow_body_items(
                render_summary_workflow_lines(POST_RELEASE_SUMMARY_CONTRACT),
                raw_lines={0: "`- Release: ${tag}`"},
            ),
        ),
    )


def iter_generated_lifecycle_doc_blocks() -> tuple[GeneratedManagedBlock, ...]:
    return tuple(
        block
        for block in iter_generated_lifecycle_blocks()
        if block.path.endswith(".md")
    )


def _validate_text_sources(
    collection_name: str,
    sources: tuple[TextSource, ...],
) -> list[str]:
    errors: list[str] = []
    labels = [source.label for source in sources]
    if len(labels) != len(set(labels)):
        errors.append(f"{collection_name}: duplicate source labels")
    for source in sources:
        if not source.label:
            errors.append(f"{collection_name}: empty source label")
        if not source.path:
            errors.append(f"{collection_name}: empty source path for {source.label}")
        if isinstance(source, MarkdownSectionSource) and not source.heading:
            errors.append(
                f"{collection_name}: empty heading for markdown source "
                f"{source.label}"
            )
        if isinstance(source, WorkflowSectionSource) and source.section == "":
            errors.append(
                f"{collection_name}: empty workflow section for {source.label}"
            )
    return errors


def _validate_contract_source_alignment(
    collection_name: str,
    sources: tuple[TextSource, ...],
    contracts: tuple[TextContract, ...],
) -> list[str]:
    errors: list[str] = []
    source_labels = {source.label for source in sources}
    referenced_labels = {
        expectation.subject
        for contract in contracts
        for expectation in contract.expectations
    }
    missing_labels = sorted(referenced_labels - source_labels)
    if missing_labels:
        errors.append(
            f"{collection_name}: missing sources for labels "
            + ", ".join(missing_labels)
        )
    unused_labels = sorted(source_labels - referenced_labels)
    if unused_labels:
        errors.append(
            f"{collection_name}: unused sources for labels "
            + ", ".join(unused_labels)
        )
    return errors


def _validate_summary_source_bindings(
    bindings: tuple[SummarySourceBinding, ...],
) -> list[str]:
    errors: list[str] = []
    contract_names = [binding.contract.name for binding in bindings]
    if len(contract_names) != len(set(contract_names)):
        errors.append("issue summary source bindings: duplicate contract names")
    doc_labels = [binding.doc_source.label for binding in bindings]
    if len(doc_labels) != len(set(doc_labels)):
        errors.append("issue summary source bindings: duplicate doc sources")
    workflow_labels = [binding.workflow_source.label for binding in bindings]
    if len(workflow_labels) != len(set(workflow_labels)):
        errors.append("issue summary source bindings: duplicate workflow sources")
    for binding in bindings:
        if binding.workflow_source.section is None:
            errors.append(
                "issue summary source bindings: workflow source missing section "
                f"for {binding.contract.name}"
            )
    return errors


def _validate_field_contracts(
    collection_name: str,
    fields: tuple[IssueFormFieldContract, ...],
) -> list[str]:
    errors: list[str] = []
    field_ids = [field.field_id for field in fields]
    if len(field_ids) != len(set(field_ids)):
        errors.append(f"{collection_name}: duplicate field ids")
    for field in fields:
        if not field.field_id:
            errors.append(f"{collection_name}: empty field id")
        if not field.label:
            errors.append(f"{collection_name}: empty label for {field.field_id}")
        if len(field.checklist_items) != len(set(field.checklist_items)):
            errors.append(
                f"{collection_name}: duplicate checklist items for "
                f"{field.field_id}"
            )
        if any(not item for item in field.checklist_items):
            errors.append(
                f"{collection_name}: empty checklist item for {field.field_id}"
            )
    return errors


def _validate_text_contracts(
    collection_name: str,
    contracts: tuple[TextContract, ...],
) -> list[str]:
    errors: list[str] = []
    contract_names = [contract.name for contract in contracts]
    if len(contract_names) != len(set(contract_names)):
        errors.append(f"{collection_name}: duplicate contract names")
    for contract in contracts:
        if not contract.name:
            errors.append(f"{collection_name}: empty contract name")
        if not contract.expectations:
            errors.append(
                f"{collection_name}: missing label requirements for {contract.name}"
            )
        labels = [expectation.subject for expectation in contract.expectations]
        if len(labels) != len(set(labels)):
            errors.append(
                f"{collection_name}: duplicate labels in contract {contract.name}"
            )
        for expectation in contract.expectations:
            if not expectation.subject:
                errors.append(
                    f"{collection_name}: empty label in contract {contract.name}"
                )
            if not expectation.snippets:
                errors.append(
                    f"{collection_name}: missing snippets for "
                    f"{contract.name} -> {expectation.subject}"
                )
                continue
            if len(expectation.snippets) != len(set(expectation.snippets)):
                errors.append(
                    f"{collection_name}: duplicate snippets for "
                    f"{contract.name} -> {expectation.subject}"
                )
            if any(not snippet for snippet in expectation.snippets):
                errors.append(
                    f"{collection_name}: empty snippet for "
                    f"{contract.name} -> {expectation.subject}"
                )
    return errors


def validate_lifecycle_contract_schema() -> list[str]:
    errors: list[str] = []

    errors.extend(
        _validate_text_sources(
            "release lifecycle text sources",
            RELEASE_LIFECYCLE_TEXT_SOURCES,
        )
    )
    errors.extend(
        _validate_contract_source_alignment(
            "release lifecycle text sources",
            RELEASE_LIFECYCLE_TEXT_SOURCES,
            RELEASE_LIFECYCLE_TEXT_CONTRACTS,
        )
    )
    errors.extend(
        _validate_text_sources(
            "maintainer issue text sources",
            MAINTAINER_ISSUE_TEXT_SOURCES,
        )
    )
    errors.extend(
        _validate_contract_source_alignment(
            "maintainer issue text sources",
            MAINTAINER_ISSUE_TEXT_SOURCES,
            MAINTAINER_ISSUE_TEXT_CONTRACTS,
        )
    )
    errors.extend(
        _validate_text_sources(
            "issue linkage text sources",
            ISSUE_LINKAGE_TEXT_SOURCES,
        )
    )
    errors.extend(
        _validate_contract_source_alignment(
            "issue linkage text sources",
            ISSUE_LINKAGE_TEXT_SOURCES,
            ISSUE_LINKAGE_TEXT_CONTRACTS,
        )
    )
    errors.extend(
        _validate_text_sources(
            "issue close-out text sources",
            ISSUE_CLOSE_OUT_TEXT_SOURCES,
        )
    )
    errors.extend(
        _validate_contract_source_alignment(
            "issue close-out text sources",
            ISSUE_CLOSE_OUT_TEXT_SOURCES,
            ISSUE_CLOSE_OUT_TEXT_CONTRACTS,
        )
    )

    errors.extend(
        _validate_text_contracts(
            "issue linkage text contracts",
            ISSUE_LINKAGE_TEXT_CONTRACTS,
        )
    )
    errors.extend(
        _validate_text_contracts(
            "issue close-out text contracts",
            ISSUE_CLOSE_OUT_TEXT_CONTRACTS,
        )
    )
    errors.extend(
        _validate_text_contracts(
            "release lifecycle text contracts",
            RELEASE_LIFECYCLE_TEXT_CONTRACTS,
        )
    )
    errors.extend(
        _validate_text_contracts(
            "maintainer issue text contracts",
            MAINTAINER_ISSUE_TEXT_CONTRACTS,
        )
    )

    errors.extend(
        _validate_field_contracts(
            "issue linkage release-prep form fields",
            ISSUE_LINKAGE_RELEASE_PREP_FORM_FIELDS,
        )
    )
    errors.extend(
        _validate_field_contracts(
            "issue linkage post-release form fields",
            ISSUE_LINKAGE_POST_RELEASE_FORM_FIELDS,
        )
    )
    errors.extend(
        _validate_field_contracts(
            "release-preparation compatibility form field",
            (RELEASE_PREP_COMPATIBILITY_AND_REPO_OPS_FORM_FIELD,),
        )
    )
    errors.extend(
        _validate_field_contracts(
            "release-preparation changelog form field",
            (RELEASE_PREP_CHANGELOG_AND_NOTES_FORM_FIELD,),
        )
    )
    errors.extend(
        _validate_field_contracts(
            "release-preparation validation form field",
            (RELEASE_PREP_VALIDATION_FORM_FIELD,),
        )
    )
    errors.extend(
        _validate_field_contracts(
            "release-preparation close-out form field",
            (RELEASE_PREP_CLOSE_OUT_FORM_FIELD,),
        )
    )
    errors.extend(
        _validate_field_contracts(
            "post-release immediate-validation form field",
            (POST_RELEASE_IMMEDIATE_VALIDATION_FORM_FIELD,),
        )
    )
    errors.extend(
        _validate_field_contracts(
            "post-release next-cycle form field",
            (POST_RELEASE_NEXT_CYCLE_FORM_FIELD,),
        )
    )
    errors.extend(
        _validate_field_contracts(
            "post-release close-out form field",
            (POST_RELEASE_CLOSE_OUT_FORM_FIELD,),
        )
    )

    if len(QUARTERLY_CLOSE_OUT_WORKFLOW_ITEMS) != len(
        set(QUARTERLY_CLOSE_OUT_WORKFLOW_ITEMS)
    ):
        errors.append("quarterly close-out workflow items: duplicate items")
    if any(not item for item in QUARTERLY_CLOSE_OUT_WORKFLOW_ITEMS):
        errors.append("quarterly close-out workflow items: empty item")

    if len(RELEASE_PREP_SCOPE_SUMMARY_PLACEHOLDER_LINES) != len(
        set(RELEASE_PREP_SCOPE_SUMMARY_PLACEHOLDER_LINES)
    ):
        errors.append("release-prep scope summary placeholder: duplicate lines")
    if any(not line for line in RELEASE_PREP_SCOPE_SUMMARY_PLACEHOLDER_LINES):
        errors.append("release-prep scope summary placeholder: empty line")

    if len(RELEASE_PREP_FOLLOW_UP_FORM_ITEMS) != len(
        set(RELEASE_PREP_FOLLOW_UP_FORM_ITEMS)
    ):
        errors.append("release-prep follow-up form items: duplicate items")
    if any(not item for item in RELEASE_PREP_FOLLOW_UP_FORM_ITEMS):
        errors.append("release-prep follow-up form items: empty item")

    if len(POST_RELEASE_RETROSPECTIVE_PLACEHOLDER_LINES) != len(
        set(POST_RELEASE_RETROSPECTIVE_PLACEHOLDER_LINES)
    ):
        errors.append("post-release retrospective placeholder: duplicate lines")
    if any(not line for line in POST_RELEASE_RETROSPECTIVE_PLACEHOLDER_LINES):
        errors.append("post-release retrospective placeholder: empty line")

    summary_names = [contract.name for contract in SUMMARY_CONTRACTS]
    if len(summary_names) != len(set(summary_names)):
        errors.append("summary contracts: duplicate contract names")
    errors.extend(_validate_summary_source_bindings(ISSUE_SUMMARY_SOURCE_BINDINGS))

    for contract in SUMMARY_CONTRACTS:
        if not contract.doc_heading:
            errors.append(f"{contract.name}: empty doc heading")
        doc_labels = [label for label, _ in contract.doc_fields]
        full_doc_labels = [
            label
            for label, _ in (
                contract.doc_prefix_fields
                + contract.doc_fields
                + contract.doc_suffix_fields
            )
        ]
        workflow_labels = [label for label, _ in contract.workflow_defaults]
        if doc_labels != workflow_labels:
            errors.append(
                f"{contract.name}: doc field labels and workflow default labels differ"
            )
        if len(full_doc_labels) != len(set(full_doc_labels)):
            errors.append(f"{contract.name}: duplicate doc field labels")
        if not contract.doc_none_guidance:
            errors.append(f"{contract.name}: missing none guidance")
        if any(not line for line in contract.doc_prefill_guidance_lines):
            errors.append(f"{contract.name}: empty doc prefill guidance line")
        if any(not line for line in contract.workflow_prefix_lines):
            errors.append(f"{contract.name}: empty workflow prefix line")
        if any(not line for line in contract.workflow_suffix_lines):
            errors.append(f"{contract.name}: empty workflow suffix line")
        if not contract.guidance_snippets:
            errors.append(f"{contract.name}: missing guidance snippets")
        if any(not snippet for snippet in contract.guidance_snippets):
            errors.append(f"{contract.name}: empty guidance snippet")

    generated_blocks = iter_generated_lifecycle_blocks()
    block_keys = [(block.path, block.marker) for block in generated_blocks]
    if len(block_keys) != len(set(block_keys)):
        errors.append("generated lifecycle blocks: duplicate path and marker")
    if any(not block.content for block in generated_blocks):
        errors.append("generated lifecycle blocks: empty content")
    if any(not block.begin_marker for block in generated_blocks):
        errors.append("generated lifecycle blocks: empty begin marker")
    if any(not block.end_marker for block in generated_blocks):
        errors.append("generated lifecycle blocks: empty end marker")

    return errors
