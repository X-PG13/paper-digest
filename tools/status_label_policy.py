from __future__ import annotations

from tools.issue_form_policy import (
    STATUS_LABEL_ISSUE_FORM_GROUP,
    issue_form_labels_for_group,
)
from tools.label_policy_base import (
    ArtifactContract,
    LabelPolicySpec,
    collect_artifact_snippets_by_path,
    collect_issue_triage_snippets,
    collect_label_descriptions,
    collect_label_taxonomy_snippets,
    collect_release_note_excluded_labels,
    validate_label_policy_specs,
)
from tools.label_registry import (
    TRIAGE_STATUS_CATEGORY,
    get_label_category,
    get_label_description,
)
from tools.saved_reply_policy import get_saved_reply

NEEDS_INFO_LABEL = "needs-info"
NEEDS_REPRO_LABEL = "needs-repro"
STALE_LABEL = "stale"
OPS_REVIEW_LABEL = "ops-review"
RELEASE_PREP_LABEL = "release-prep"
RELEASE_FOLLOW_UP_LABEL = "release-follow-up"

NEEDS_INFO_RULE = (
    "Treat `needs-info` and `needs-repro` as maintainer follow-up labels, not "
    "routing labels."
)
NEEDS_INFO_REPLY_RULE = (
    "Add `needs-info` or `needs-repro` only when the maintainer reply clearly "
    "says what is missing."
)
NEEDS_REPRO_RULE = (
    "Use `needs-repro` when a concrete minimal reproduction is still required "
    "before work can continue."
)
COMMUNITY_TRIAGE_NEEDS_INFO_BUG_RULE = (
    "`.github/workflows/community-triage.yml` adds `needs-info` to bug reports "
    "that still miss the minimum reproducibility fields from the bug template."
)
COMMUNITY_TRIAGE_NEEDS_INFO_SUPPORT_RULE = (
    "The same workflow also adds `needs-info` to support requests that still "
    "miss confirmation that the pre-read docs were checked or the minimum "
    "environment context from the support template."
)
COMMUNITY_TRIAGE_NEEDS_REPRO_RULE = (
    "`needs-repro` remains maintainer-applied after a concrete reproduction "
    "request; community-triage should not add it automatically."
)
COMMUNITY_TRIAGE_STATUS_AUTOMATION_RULE = (
    "`.github/workflows/community-triage.yml` adds `needs-info` to incomplete "
    "bug and support intake, while `needs-repro` remains maintainer-applied "
    "after a concrete reproduction request."
)
STALE_USAGE_RULE = (
    "Use `stale` only for inactivity handling under the documented timer; do "
    "not use it as a substitute for direct triage or closure."
)
STALE_TAXONOMY_RULE = (
    "`stale` is the automation-managed inactivity label and should not replace "
    "direct maintainer triage or closure decisions."
)
STALE_AUTOMATION_RULE = (
    "`.github/workflows/stale.yml` applies `stale` after 21 inactive issue "
    "days and 30 inactive pull-request days, closes issues 7 days later, and "
    "does not auto-close pull requests."
)
STALE_TAXONOMY_AUTOMATION_RULE = (
    "`.github/workflows/stale.yml` uses the taxonomy for inactivity handling"
)
OPS_REVIEW_RULE = (
    "Reserve `ops-review` for scheduled repository-operations review and "
    "access-audit issues."
)
RELEASE_PREP_RULE = (
    "Reserve `release-prep` for maintainer release-preparation tracking issues."
)
RELEASE_FOLLOW_UP_RULE = (
    "Reserve `release-follow-up` for maintainer post-release verification and "
    "immediate follow-up issues."
)
LIFECYCLE_LABEL_EXEMPTION_RULE = (
    "`ops-review`, `release-prep`, and `release-follow-up` are maintainer "
    "lifecycle labels and stay exempt from stale issue closure."
)
LIFECYCLE_LABEL_TAXONOMY_RULE = (
    "`ops-review`, `release-prep`, and `release-follow-up` are reserved for "
    "scheduled maintainer lifecycle issues and stay exempt from stale issue "
    "closure."
)

StatusArtifactContract = ArtifactContract
StatusLabelSpec = LabelPolicySpec

STATUS_LABEL_SPECS = (
    StatusLabelSpec(
        label=NEEDS_INFO_LABEL,
        label_json_description=get_label_description(NEEDS_INFO_LABEL),
        issue_triage_snippets=(
            NEEDS_INFO_RULE,
            NEEDS_INFO_REPLY_RULE,
            COMMUNITY_TRIAGE_NEEDS_INFO_BUG_RULE,
            COMMUNITY_TRIAGE_NEEDS_INFO_SUPPORT_RULE,
        ),
        label_taxonomy_snippets=(
            "| `needs-info` | The report is missing required context |",
            (
                "4. `needs-info` and `needs-repro` should be paired with a "
                "concrete maintainer"
            ),
            COMMUNITY_TRIAGE_STATUS_AUTOMATION_RULE,
        ),
        artifact_contracts=(
            StatusArtifactContract(
                path=".github/workflows/community-triage.yml",
                snippets=(
                    "- name: Sync needs-info label",
                    "--ensure needs-info",
                    "--remove needs-info",
                ),
            ),
        ),
        reply_slug=NEEDS_INFO_LABEL,
        release_note_excluded=True,
    ),
    StatusLabelSpec(
        label=NEEDS_REPRO_LABEL,
        label_json_description=get_label_description(NEEDS_REPRO_LABEL),
        issue_triage_snippets=(
            NEEDS_INFO_RULE,
            NEEDS_REPRO_RULE,
            COMMUNITY_TRIAGE_NEEDS_REPRO_RULE,
        ),
        label_taxonomy_snippets=(
            "| `needs-repro` | The report needs a minimal reproduction |",
            (
                "4. `needs-info` and `needs-repro` should be paired with a "
                "concrete maintainer"
            ),
            COMMUNITY_TRIAGE_STATUS_AUTOMATION_RULE,
        ),
        reply_slug=NEEDS_REPRO_LABEL,
        release_note_excluded=True,
    ),
    StatusLabelSpec(
        label=STALE_LABEL,
        label_json_description=get_label_description(STALE_LABEL),
        issue_triage_snippets=(
            STALE_USAGE_RULE,
            "Issues may be marked `stale` after 21 days without activity.",
            "Stale issues may be closed 7 days later if no new information arrives.",
            (
                "Pull requests may be marked `stale` after 30 days without "
                "activity, but they are not auto-closed by default."
            ),
        ),
        label_taxonomy_snippets=(
            "| `stale` | No recent activity after the documented grace period |",
            STALE_TAXONOMY_RULE,
            STALE_TAXONOMY_AUTOMATION_RULE,
        ),
        artifact_contracts=(
            StatusArtifactContract(
                path=".github/workflows/stale.yml",
                snippets=(
                    "stale-issue-label: stale",
                    "stale-pr-label: stale",
                    "days-before-issue-stale: 21",
                    "days-before-issue-close: 7",
                    "days-before-pr-stale: 30",
                    "days-before-pr-close: -1",
                ),
            ),
        ),
        release_note_excluded=True,
    ),
    StatusLabelSpec(
        label=OPS_REVIEW_LABEL,
        label_json_description=get_label_description(OPS_REVIEW_LABEL),
        issue_triage_snippets=(
            OPS_REVIEW_RULE,
            LIFECYCLE_LABEL_EXEMPTION_RULE,
        ),
        label_taxonomy_snippets=(
            (
                "| `ops-review` | Scheduled repository-operations review and "
                "access-audit work |"
            ),
            LIFECYCLE_LABEL_TAXONOMY_RULE,
            (
                "`.github/workflows/quarterly-maintainer-review.yml` uses "
                "`maintenance` and `ops-review` for scheduled maintainer "
                "review issues."
            ),
        ),
        artifact_contracts=(
            StatusArtifactContract(
                path=".github/workflows/quarterly-maintainer-review.yml",
                snippets=(
                    'labels: "ops-review",',
                    'labels: ["maintenance", "ops-review"],',
                ),
            ),
        ),
        stale_exempt_issues=True,
    ),
    StatusLabelSpec(
        label=RELEASE_PREP_LABEL,
        label_json_description=get_label_description(RELEASE_PREP_LABEL),
        issue_triage_snippets=(
            RELEASE_PREP_RULE,
            LIFECYCLE_LABEL_EXEMPTION_RULE,
        ),
        label_taxonomy_snippets=(
            (
                "| `release-prep` | Maintainer release-preparation tracking "
                "work |"
            ),
            LIFECYCLE_LABEL_TAXONOMY_RULE,
            (
                "`.github/ISSUE_TEMPLATE/release_preparation.yml` keeps "
                "`release-prep` aligned with the maintainer release "
                "lifecycle."
            ),
        ),
        stale_exempt_issues=True,
    ),
    StatusLabelSpec(
        label=RELEASE_FOLLOW_UP_LABEL,
        label_json_description=get_label_description(RELEASE_FOLLOW_UP_LABEL),
        issue_triage_snippets=(
            RELEASE_FOLLOW_UP_RULE,
            LIFECYCLE_LABEL_EXEMPTION_RULE,
        ),
        label_taxonomy_snippets=(
            (
                "| `release-follow-up` | Maintainer post-release verification "
                "and follow-up work |"
            ),
            LIFECYCLE_LABEL_TAXONOMY_RULE,
            (
                "`.github/ISSUE_TEMPLATE/post_release_follow_up.yml` and "
                "`.github/workflows/post-release-follow-up.yml` keep "
                "`release-follow-up` aligned with the maintainer release "
                "lifecycle."
            ),
        ),
        artifact_contracts=(
            StatusArtifactContract(
                path=".github/workflows/post-release-follow-up.yml",
                snippets=(
                    'labels: "release-follow-up",',
                    'labels: ["maintenance", "release-follow-up"],',
                ),
            ),
        ),
        stale_exempt_issues=True,
    ),
)


def required_issue_triage_snippets() -> tuple[str, ...]:
    return collect_issue_triage_snippets(STATUS_LABEL_SPECS)


def required_label_taxonomy_snippets() -> tuple[str, ...]:
    return collect_label_taxonomy_snippets(STATUS_LABEL_SPECS)


def required_label_descriptions() -> dict[str, str]:
    return collect_label_descriptions(STATUS_LABEL_SPECS)


def required_artifact_snippets_by_path() -> dict[str, tuple[str, ...]]:
    return collect_artifact_snippets_by_path(STATUS_LABEL_SPECS)


def required_issue_form_labels_by_path() -> dict[str, tuple[str, ...]]:
    return issue_form_labels_for_group(STATUS_LABEL_ISSUE_FORM_GROUP)


def required_release_note_excluded_labels() -> tuple[str, ...]:
    return collect_release_note_excluded_labels(STATUS_LABEL_SPECS)


def validate_status_label_policy() -> None:
    issue_form_labels_for_group(STATUS_LABEL_ISSUE_FORM_GROUP)
    validate_label_policy_specs(
        STATUS_LABEL_SPECS,
        duplicate_error_prefix="duplicate status label",
        missing_issue_triage_error_prefix=(
            "status label must define issue-triage snippets"
        ),
        missing_label_taxonomy_error_prefix=(
            "status label must define label-taxonomy snippets"
        ),
        manual_only_auto_error_prefix=(
            "manual-only status label must not define automated PR routing paths"
        ),
        reply_lookup=get_saved_reply,
    )
    for spec in STATUS_LABEL_SPECS:
        if get_label_category(spec.label) != TRIAGE_STATUS_CATEGORY:
            raise ValueError(
                "status label must stay in triage-status category: " + spec.label
            )
