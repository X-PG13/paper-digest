from __future__ import annotations

from tools.label_policy_base import (
    LabelPolicySpec,
    collect_issue_triage_snippets,
    collect_label_descriptions,
    collect_label_taxonomy_snippets,
    collect_release_note_categories,
    collect_release_note_excluded_labels,
    validate_label_policy_specs,
)
from tools.label_registry import (
    RESOLUTION_CATEGORY,
    ROUTING_CATEGORY,
    TRIAGE_STATUS_CATEGORY,
    get_label_category,
    get_label_description,
)
from tools.saved_reply_policy import get_saved_reply

DOCUMENTATION_LABEL = "documentation"
DUPLICATE_LABEL = "duplicate"
INVALID_LABEL = "invalid"
BLOCKED_LABEL = "blocked"
RELEASE_NOTE_LABEL = "release-note"
WONTFIX_LABEL = "wontfix"

MANUAL_RESOLUTION_LABELS = (
    DUPLICATE_LABEL,
    INVALID_LABEL,
    WONTFIX_LABEL,
)

DOCUMENTATION_AUTOMATION_RULE = (
    "`documentation` may be applied automatically to pull requests that touch "
    "public docs or Markdown entry points, and maintainers should also use it "
    "for docs-only follow-up work."
)
MANUAL_RESOLUTION_LABEL_RULE = (
    "`duplicate` and `wontfix` are manual resolution labels. Automation "
    "should not add them; maintainers should apply them when closing with the "
    "canonical tracking link or the relevant scope or policy reason."
)
DUPLICATE_CLOSE_RULE = (
    "Use `duplicate` when closing a report that is already tracked elsewhere, "
    "and link the canonical issue or pull request in the closing reply."
)
WONTFIX_CLOSE_RULE = (
    "Use `wontfix` when maintainers intentionally decide not to plan a report "
    "after scope or product review, and link the relevant scope or policy "
    "reason in the closing reply."
)
DIRECT_CLOSE_INSTEAD_OF_STALE_RULE = (
    "Reports already resolved as `duplicate` or `wontfix` should be closed "
    "directly instead of being left open for `stale`."
)
DOCUMENTATION_STALE_RULE = (
    "`documentation` follow-up issues still use the standard stale timer "
    "unless another exempt maintainer-work label applies."
)
INVALID_RESOLUTION_LABEL_RULE = (
    "`invalid` is a manual resolution label. Automation should not add it; use "
    "it only when a report is not actionable as filed and the concrete reason "
    "or correct intake path has already been explained."
)
INVALID_CLOSE_RULE = (
    "Use `invalid` only when a report is not actionable as filed and the "
    "correct reason or intake path has already been explained; do not use it "
    "as a substitute for `needs-info`."
)
BLOCKED_LABEL_RULE = (
    "Use `blocked` when maintainers cannot proceed because an external "
    "dependency or explicit maintainer decision is still pending, and the "
    "blocker should be linked."
)
BLOCKED_STALE_RULE = (
    "`blocked` stays exempt from stale on both issues and pull requests until "
    "the blocker is cleared."
)
BLOCKED_AND_RELEASE_NOTE_STALE_RULE = (
    "`blocked` and `release-note` stay exempt from stale on both issues and "
    "pull requests until the label is cleared."
)
RELEASE_NOTE_LABEL_RULE = (
    "Add `release-note` when the eventual change should be called out in both "
    "`CHANGELOG.md` and the generated GitHub release notes."
)
RELEASE_NOTE_LABEL_TAXONOMY_RULE = (
    "`release-note` means the change should appear in both `CHANGELOG.md` and "
    "the generated GitHub release notes, and `.github/release.yml` should stay "
    "aligned with that label."
)
RELEASE_NOTE_AUTOMATION_RULE = (
    "`.github/release.yml` should continue to map `release-note` into the "
    "generated GitHub release-note categories, while `invalid` stays excluded "
    "from generated notes."
)
RELEASE_NOTE_STALE_RULE = (
    "`release-note` stays exempt from stale on both issues and pull requests "
    "until the label is cleared."
)

LabelBehaviorSpec = LabelPolicySpec


LABEL_BEHAVIOR_SPECS = (
    LabelBehaviorSpec(
        label=DOCUMENTATION_LABEL,
        label_json_description=get_label_description(DOCUMENTATION_LABEL),
        issue_triage_snippets=(
            "- Documentation: missing, ambiguous, or outdated public guidance.",
            DOCUMENTATION_AUTOMATION_RULE,
            DOCUMENTATION_STALE_RULE,
        ),
        label_taxonomy_snippets=(
            "| `documentation` | Missing, unclear, or outdated docs |",
            DOCUMENTATION_AUTOMATION_RULE,
            DOCUMENTATION_STALE_RULE,
        ),
        reply_slug="docs-follow-up",
        auto_pr_routing_paths=("README.md", "docs/issue-triage.md"),
        release_note_category="Documentation",
    ),
    LabelBehaviorSpec(
        label=DUPLICATE_LABEL,
        label_json_description=get_label_description(DUPLICATE_LABEL),
        issue_triage_snippets=(
            "- The report is a duplicate.",
            DUPLICATE_CLOSE_RULE,
            DIRECT_CLOSE_INSTEAD_OF_STALE_RULE,
        ),
        label_taxonomy_snippets=(
            "| `duplicate` | Covered by another tracked issue or pull request |",
            MANUAL_RESOLUTION_LABEL_RULE,
        ),
        reply_slug="duplicate",
        manual_only=True,
        release_note_excluded=True,
    ),
    LabelBehaviorSpec(
        label=INVALID_LABEL,
        label_json_description=get_label_description(INVALID_LABEL),
        issue_triage_snippets=(
            INVALID_CLOSE_RULE,
            "- The report is not actionable as filed and the correct path or reason",
        ),
        label_taxonomy_snippets=(
            "| `invalid` | Not actionable as filed |",
            INVALID_RESOLUTION_LABEL_RULE,
        ),
        manual_only=True,
        release_note_excluded=True,
    ),
    LabelBehaviorSpec(
        label=BLOCKED_LABEL,
        label_json_description=get_label_description(BLOCKED_LABEL),
        issue_triage_snippets=(
            BLOCKED_LABEL_RULE,
            BLOCKED_STALE_RULE,
        ),
        label_taxonomy_snippets=(
            "| `blocked` | Maintainers cannot proceed yet |",
            BLOCKED_LABEL_RULE,
            BLOCKED_AND_RELEASE_NOTE_STALE_RULE,
        ),
        stale_exempt_issues=True,
        stale_exempt_prs=True,
    ),
    LabelBehaviorSpec(
        label=RELEASE_NOTE_LABEL,
        label_json_description=get_label_description(RELEASE_NOTE_LABEL),
        issue_triage_snippets=(
            RELEASE_NOTE_LABEL_RULE,
            RELEASE_NOTE_AUTOMATION_RULE,
            RELEASE_NOTE_STALE_RULE,
        ),
        label_taxonomy_snippets=(
            "| `release-note` | The change should be called out in release notes |",
            RELEASE_NOTE_LABEL_TAXONOMY_RULE,
            BLOCKED_AND_RELEASE_NOTE_STALE_RULE,
        ),
        stale_exempt_issues=True,
        stale_exempt_prs=True,
        release_note_category="Features",
    ),
    LabelBehaviorSpec(
        label=WONTFIX_LABEL,
        label_json_description=get_label_description(WONTFIX_LABEL),
        issue_triage_snippets=(
            WONTFIX_CLOSE_RULE,
            DIRECT_CLOSE_INSTEAD_OF_STALE_RULE,
        ),
        label_taxonomy_snippets=(
            "| `wontfix` | Intentionally not planned |",
            MANUAL_RESOLUTION_LABEL_RULE,
        ),
        reply_slug="out-of-scope",
        manual_only=True,
        release_note_excluded=True,
    ),
)


def get_label_behavior(label: str) -> LabelBehaviorSpec:
    for behavior in LABEL_BEHAVIOR_SPECS:
        if behavior.label == label:
            return behavior
    raise KeyError(f"unknown label behavior: {label}")


def required_issue_triage_snippets() -> tuple[str, ...]:
    return collect_issue_triage_snippets(LABEL_BEHAVIOR_SPECS)


def required_label_taxonomy_snippets() -> tuple[str, ...]:
    return collect_label_taxonomy_snippets(LABEL_BEHAVIOR_SPECS)


def required_label_descriptions() -> dict[str, str]:
    return collect_label_descriptions(LABEL_BEHAVIOR_SPECS)


def required_release_note_categories() -> dict[str, tuple[str, ...]]:
    return collect_release_note_categories(LABEL_BEHAVIOR_SPECS)


def required_release_note_excluded_labels() -> tuple[str, ...]:
    return collect_release_note_excluded_labels(LABEL_BEHAVIOR_SPECS)


def validate_label_behavior_policy() -> None:
    validate_label_policy_specs(
        LABEL_BEHAVIOR_SPECS,
        duplicate_error_prefix="duplicate label behavior",
        missing_issue_triage_error_prefix=(
            "label behavior must define issue-triage snippets"
        ),
        missing_label_taxonomy_error_prefix=(
            "label behavior must define label-taxonomy snippets"
        ),
        manual_only_auto_error_prefix=(
            "manual-only label must not define automated PR routing paths"
        ),
        reply_lookup=get_saved_reply,
    )
    for behavior in LABEL_BEHAVIOR_SPECS:
        if get_label_category(behavior.label) not in (
            ROUTING_CATEGORY,
            TRIAGE_STATUS_CATEGORY,
            RESOLUTION_CATEGORY,
        ):
            raise ValueError(
                "label behavior must stay in "
                "routing/triage-status/resolution categories: "
                + behavior.label
            )
