from __future__ import annotations

from tools.issue_form_policy import (
    CONTRIBUTOR_RELEASE_LABEL_ISSUE_FORM_GROUP,
    issue_form_labels_for_group,
)
from tools.label_policy_base import (
    ArtifactContract,
    LabelPolicySpec,
    collect_artifact_snippets_by_path,
    collect_issue_triage_snippets,
    collect_label_descriptions,
    collect_label_taxonomy_snippets,
    collect_release_note_categories,
    validate_label_policy_specs,
)
from tools.label_registry import (
    CONTRIBUTION_CATEGORY,
    ROUTING_CATEGORY,
    TRIAGE_STATUS_CATEGORY,
    get_label_category,
    get_label_description,
)

ENHANCEMENT_LABEL = "enhancement"
MAINTENANCE_LABEL = "maintenance"
BREAKING_LABEL = "breaking"
GOOD_FIRST_ISSUE_LABEL = "good first issue"
HELP_WANTED_LABEL = "help wanted"

CONTRIBUTOR_DISCOVERY_LABELS = (
    GOOD_FIRST_ISSUE_LABEL,
    HELP_WANTED_LABEL,
)
RELEASE_FACING_LABELS = (
    ENHANCEMENT_LABEL,
    MAINTENANCE_LABEL,
    BREAKING_LABEL,
)

ENHANCEMENT_RULE = (
    "Use `enhancement` for scoped new capabilities, product improvements, or "
    "workflow changes that do not need proposal-level scoping."
)
ENHANCEMENT_FORM_RULE = (
    "`.github/ISSUE_TEMPLATE/feature_request.yml` uses `enhancement`, and "
    "`.github/ISSUE_TEMPLATE/proposal.yml` keeps `enhancement` plus "
    "`proposal` aligned for larger design work."
)
ENHANCEMENT_TAXONOMY_RULE = (
    "`enhancement` is the routing label for scoped feature work that does not "
    "need proposal-level scoping, and the feature-request and proposal forms "
    "should keep that label aligned."
)
MAINTENANCE_RULE = (
    "Use `maintenance` for CI, tooling, dependency, or repository-health work, "
    "including scheduled maintainer operations or release-tracking issues."
)
MAINTENANCE_AUTOMATION_RULE = (
    "`.github/workflows/community-triage.yml` path-based PR intake uses "
    "`maintenance` for workflow, tooling, and repository-health changes."
)
MAINTENANCE_LIFECYCLE_RULE = (
    "`.github/workflows/quarterly-maintainer-review.yml`, "
    "`.github/workflows/post-release-follow-up.yml`, and the maintainer "
    "lifecycle issue forms keep scheduled repository-health work under "
    "`maintenance`."
)
MAINTENANCE_TAXONOMY_RULE = (
    "`maintenance` covers CI, tooling, dependency, and repository-health work, "
    "including scheduled maintainer review and post-release follow-up issues."
)
MAINTENANCE_QUARTERLY_AUTOMATION_RULE = (
    "`.github/workflows/quarterly-maintainer-review.yml` uses `maintenance` "
    "and `ops-review` for scheduled maintainer review issues."
)
MAINTENANCE_POST_RELEASE_AUTOMATION_RULE = (
    "`.github/workflows/post-release-follow-up.yml` uses `maintenance` and "
    "`release-follow-up` for post-release verification issues."
)
BREAKING_RULE = (
    "Add `breaking` when a change alters documented behavior, compatibility, "
    "or workflow expectations and needs explicit upgrade guidance."
)
BREAKING_RELEASE_RULE = (
    "Pair `breaking` with `release-note` when the shipped change must be "
    "called out publicly in `CHANGELOG.md` and release notes."
)
BREAKING_TAXONOMY_RULE = (
    "`breaking` should be used only when compatibility or workflow behavior "
    "changes require explicit upgrade guidance; pair it with `release-note` "
    "when the shipped change must be called out publicly."
)
CONTRIBUTOR_DISCOVERY_RULE = (
    "`good first issue` and `help wanted` are manual contributor-facing "
    "labels. Use them only when scope, acceptance criteria, and relevant docs "
    "are explicit."
)
GOOD_FIRST_ISSUE_RULE = (
    "Use `good first issue` only for deliberately small, well-scoped "
    "contributions that are suitable for a first external contribution."
)
HELP_WANTED_RULE = (
    "Use `help wanted` when maintainers welcome outside implementation help "
    "but the task may still require more repository context."
)
CONTRIBUTOR_DISCOVERY_STALE_RULE = (
    "`good first issue` and `help wanted` stay exempt from stale on issues so "
    "curated contributor entry points remain visible."
)
GOOD_FIRST_ISSUE_TAXONOMY_RULE = (
    "`good first issue` and `help wanted` are manual contributor-facing "
    "labels. Use `good first issue` only when the task is intentionally "
    "small, well-scoped, and suitable for a first external contribution."
)
HELP_WANTED_TAXONOMY_RULE = (
    "`help wanted` should mark work where maintainers welcome outside "
    "implementation help even if the task still needs more repository context."
)
CONTRIBUTOR_DISCOVERY_TAXONOMY_STALE_RULE = (
    "`good first issue` and `help wanted` stay exempt from stale on issues so "
    "curated contributor entry points remain discoverable."
)

ContributorReleaseArtifactContract = ArtifactContract
ContributorReleaseLabelSpec = LabelPolicySpec

CONTRIBUTOR_RELEASE_LABEL_SPECS = (
    ContributorReleaseLabelSpec(
        label=ENHANCEMENT_LABEL,
        label_json_description=get_label_description(ENHANCEMENT_LABEL),
        issue_triage_snippets=(
            ENHANCEMENT_RULE,
            ENHANCEMENT_FORM_RULE,
        ),
        label_taxonomy_snippets=(
            (
                "| `enhancement` | New capabilities, workflow changes, or "
                "product improvements |"
            ),
            ENHANCEMENT_TAXONOMY_RULE,
            (
                "`.github/ISSUE_TEMPLATE/feature_request.yml` uses "
                "`enhancement`, and `.github/ISSUE_TEMPLATE/proposal.yml` "
                "keeps `enhancement` plus `proposal` aligned for design-first "
                "work."
            ),
        ),
        release_note_category="Features",
    ),
    ContributorReleaseLabelSpec(
        label=MAINTENANCE_LABEL,
        label_json_description=get_label_description(MAINTENANCE_LABEL),
        issue_triage_snippets=(
            MAINTENANCE_RULE,
            MAINTENANCE_AUTOMATION_RULE,
            MAINTENANCE_LIFECYCLE_RULE,
        ),
        label_taxonomy_snippets=(
            "| `maintenance` | Tooling, CI, dependency, or repository-health work |",
            MAINTENANCE_TAXONOMY_RULE,
            MAINTENANCE_AUTOMATION_RULE,
            MAINTENANCE_QUARTERLY_AUTOMATION_RULE,
            MAINTENANCE_POST_RELEASE_AUTOMATION_RULE,
        ),
        artifact_contracts=(
            ContributorReleaseArtifactContract(
                path=".github/workflows/quarterly-maintainer-review.yml",
                snippets=(
                    'labels: ["maintenance", "ops-review"],',
                ),
            ),
            ContributorReleaseArtifactContract(
                path=".github/workflows/post-release-follow-up.yml",
                snippets=(
                    'labels: ["maintenance", "release-follow-up"],',
                ),
            ),
        ),
        auto_pr_routing_paths=(
            ".github/workflows/ci.yml",
            "Makefile",
        ),
        release_note_category="Maintenance",
    ),
    ContributorReleaseLabelSpec(
        label=BREAKING_LABEL,
        label_json_description=get_label_description(BREAKING_LABEL),
        issue_triage_snippets=(
            BREAKING_RULE,
            BREAKING_RELEASE_RULE,
        ),
        label_taxonomy_snippets=(
            (
                "| `breaking` | Behavior or compatibility changes that require "
                "extra release-note attention |"
            ),
            BREAKING_TAXONOMY_RULE,
            (
                "`.github/release.yml` uses `breaking`, `enhancement`, "
                "`maintenance`, and `release-note` to keep generated GitHub "
                "release-note categories aligned."
            ),
        ),
        artifact_contracts=(
            ContributorReleaseArtifactContract(
                path="docs/release-cadence-policy.md",
                snippets=(
                    (
                        "Major releases: reserve for explicit `breaking` "
                        "changes with visible upgrade"
                    ),
                ),
            ),
            ContributorReleaseArtifactContract(
                path="docs/roadmap-policy.md",
                snippets=(
                    "Use `release-note` and, when appropriate, `breaking`.",
                ),
            ),
        ),
        release_note_category="Breaking Changes",
    ),
    ContributorReleaseLabelSpec(
        label=GOOD_FIRST_ISSUE_LABEL,
        label_json_description=get_label_description(GOOD_FIRST_ISSUE_LABEL),
        issue_triage_snippets=(
            CONTRIBUTOR_DISCOVERY_RULE,
            GOOD_FIRST_ISSUE_RULE,
            CONTRIBUTOR_DISCOVERY_STALE_RULE,
        ),
        label_taxonomy_snippets=(
            "| `good first issue` | Suitable for a first contribution |",
            GOOD_FIRST_ISSUE_TAXONOMY_RULE,
            CONTRIBUTOR_DISCOVERY_TAXONOMY_STALE_RULE,
        ),
        manual_only=True,
        stale_exempt_issues=True,
    ),
    ContributorReleaseLabelSpec(
        label=HELP_WANTED_LABEL,
        label_json_description=get_label_description(HELP_WANTED_LABEL),
        issue_triage_snippets=(
            CONTRIBUTOR_DISCOVERY_RULE,
            HELP_WANTED_RULE,
            CONTRIBUTOR_DISCOVERY_STALE_RULE,
        ),
        label_taxonomy_snippets=(
            "| `help wanted` | Maintainers welcome external implementation help |",
            HELP_WANTED_TAXONOMY_RULE,
            CONTRIBUTOR_DISCOVERY_TAXONOMY_STALE_RULE,
        ),
        manual_only=True,
        stale_exempt_issues=True,
    ),
)


def required_issue_triage_snippets() -> tuple[str, ...]:
    return collect_issue_triage_snippets(CONTRIBUTOR_RELEASE_LABEL_SPECS)


def required_label_taxonomy_snippets() -> tuple[str, ...]:
    return collect_label_taxonomy_snippets(CONTRIBUTOR_RELEASE_LABEL_SPECS)


def required_label_descriptions() -> dict[str, str]:
    return collect_label_descriptions(CONTRIBUTOR_RELEASE_LABEL_SPECS)


def required_artifact_snippets_by_path() -> dict[str, tuple[str, ...]]:
    return collect_artifact_snippets_by_path(CONTRIBUTOR_RELEASE_LABEL_SPECS)


def required_issue_form_labels_by_path() -> dict[str, tuple[str, ...]]:
    return issue_form_labels_for_group(CONTRIBUTOR_RELEASE_LABEL_ISSUE_FORM_GROUP)


def required_release_note_categories() -> dict[str, tuple[str, ...]]:
    return collect_release_note_categories(CONTRIBUTOR_RELEASE_LABEL_SPECS)


def validate_contributor_release_label_policy() -> None:
    issue_form_labels_for_group(CONTRIBUTOR_RELEASE_LABEL_ISSUE_FORM_GROUP)
    validate_label_policy_specs(
        CONTRIBUTOR_RELEASE_LABEL_SPECS,
        duplicate_error_prefix="duplicate contributor/release label",
        missing_issue_triage_error_prefix=(
            "missing issue-triage snippets for contributor/release label"
        ),
        missing_label_taxonomy_error_prefix=(
            "missing label-taxonomy snippets for contributor/release label"
        ),
        manual_only_auto_error_prefix=(
            "manual-only contributor/release label must not auto-route"
        ),
    )
    for spec in CONTRIBUTOR_RELEASE_LABEL_SPECS:
        if get_label_category(spec.label) not in (
            ROUTING_CATEGORY,
            TRIAGE_STATUS_CATEGORY,
            CONTRIBUTION_CATEGORY,
        ):
            raise ValueError(
                "contributor/release label must stay in "
                "routing/triage-status/contribution categories: "
                + spec.label
            )
    if tuple(spec.label for spec in CONTRIBUTOR_RELEASE_LABEL_SPECS[-2:]) != (
        GOOD_FIRST_ISSUE_LABEL,
        HELP_WANTED_LABEL,
    ):
        raise ValueError("contributor discovery labels must remain ordered")
