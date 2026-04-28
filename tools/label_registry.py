from __future__ import annotations

from dataclasses import dataclass

ROUTING_CATEGORY = "routing"
PLANNING_CATEGORY = "planning"
TRIAGE_STATUS_CATEGORY = "triage-status"
CONTRIBUTION_CATEGORY = "contribution"
RESOLUTION_CATEGORY = "resolution"

LABEL_CATEGORIES = (
    ROUTING_CATEGORY,
    PLANNING_CATEGORY,
    TRIAGE_STATUS_CATEGORY,
    CONTRIBUTION_CATEGORY,
    RESOLUTION_CATEGORY,
)

ROUTING_SECTION = "Routing Labels"
PLANNING_SECTION = "Planning Labels"
TRIAGE_STATUS_SECTION = "Triage Status Labels"
CONTRIBUTION_SECTION = "Contribution Labels"
RESOLUTION_SECTION = "Resolution Labels"

CATEGORY_TO_SECTION = {
    ROUTING_CATEGORY: ROUTING_SECTION,
    PLANNING_CATEGORY: PLANNING_SECTION,
    TRIAGE_STATUS_CATEGORY: TRIAGE_STATUS_SECTION,
    CONTRIBUTION_CATEGORY: CONTRIBUTION_SECTION,
    RESOLUTION_CATEGORY: RESOLUTION_SECTION,
}


@dataclass(frozen=True)
class LabelRegistryEntry:
    label: str
    description: str
    category: str
    taxonomy_purpose: str | None = None

    @property
    def taxonomy_section(self) -> str:
        return CATEGORY_TO_SECTION[self.category]

    @property
    def taxonomy_row(self) -> str:
        purpose = self.taxonomy_purpose or self.description
        return f"| `{self.label}` | {purpose} |"


LABEL_REGISTRY = (
    LabelRegistryEntry(
        label="bug",
        description="Confirmed or suspected defects on supported paths",
        category=ROUTING_CATEGORY,
    ),
    LabelRegistryEntry(
        label="enhancement",
        description="New capabilities, workflow changes, or product improvements",
        category=ROUTING_CATEGORY,
    ),
    LabelRegistryEntry(
        label="support",
        description="Usage or configuration questions",
        category=ROUTING_CATEGORY,
        taxonomy_purpose="Usage and setup questions",
    ),
    LabelRegistryEntry(
        label="documentation",
        description="Missing, unclear, or outdated documentation",
        category=ROUTING_CATEGORY,
        taxonomy_purpose="Missing, unclear, or outdated docs",
    ),
    LabelRegistryEntry(
        label="maintenance",
        description="CI, tooling, dependency, or repository-health work",
        category=ROUTING_CATEGORY,
        taxonomy_purpose="Tooling, CI, dependency, or repository-health work",
    ),
    LabelRegistryEntry(
        label="security",
        description="Security-sensitive work",
        category=ROUTING_CATEGORY,
        taxonomy_purpose=(
            "Security-sensitive work that should stay private unless cleared"
        ),
    ),
    LabelRegistryEntry(
        label="proposal",
        description="Larger design, workflow, governance, or roadmap proposals",
        category=PLANNING_CATEGORY,
    ),
    LabelRegistryEntry(
        label="dependencies",
        description="Dependency updates and ecosystem maintenance",
        category=PLANNING_CATEGORY,
        taxonomy_purpose="Dependency updates and ecosystem-maintenance changes",
    ),
    LabelRegistryEntry(
        label="breaking",
        description=(
            "Behavior or compatibility changes that require extra "
            "release-note attention"
        ),
        category=TRIAGE_STATUS_CATEGORY,
    ),
    LabelRegistryEntry(
        label="needs-info",
        description="Missing information required for triage",
        category=TRIAGE_STATUS_CATEGORY,
        taxonomy_purpose="The report is missing required context",
    ),
    LabelRegistryEntry(
        label="needs-repro",
        description="Needs a minimal reproduction before work can continue",
        category=TRIAGE_STATUS_CATEGORY,
        taxonomy_purpose="The report needs a minimal reproduction",
    ),
    LabelRegistryEntry(
        label="blocked",
        description="Cannot proceed until an external dependency or decision changes",
        category=TRIAGE_STATUS_CATEGORY,
        taxonomy_purpose="Maintainers cannot proceed yet",
    ),
    LabelRegistryEntry(
        label="stale",
        description="Marked stale after prolonged inactivity",
        category=TRIAGE_STATUS_CATEGORY,
        taxonomy_purpose="No recent activity after the documented grace period",
    ),
    LabelRegistryEntry(
        label="ops-review",
        description="Scheduled repository-operations review and access-audit work",
        category=TRIAGE_STATUS_CATEGORY,
    ),
    LabelRegistryEntry(
        label="release-prep",
        description="Maintainer release-preparation tracking work",
        category=TRIAGE_STATUS_CATEGORY,
    ),
    LabelRegistryEntry(
        label="release-follow-up",
        description="Maintainer post-release verification and follow-up work",
        category=TRIAGE_STATUS_CATEGORY,
    ),
    LabelRegistryEntry(
        label="release-note",
        description="Should be called out in release notes",
        category=TRIAGE_STATUS_CATEGORY,
        taxonomy_purpose="The change should be called out in release notes",
    ),
    LabelRegistryEntry(
        label="good first issue",
        description="Suitable for a first contribution",
        category=CONTRIBUTION_CATEGORY,
    ),
    LabelRegistryEntry(
        label="help wanted",
        description="Maintainers welcome outside implementation help",
        category=CONTRIBUTION_CATEGORY,
        taxonomy_purpose="Maintainers welcome external implementation help",
    ),
    LabelRegistryEntry(
        label="duplicate",
        description="Tracked elsewhere already",
        category=RESOLUTION_CATEGORY,
        taxonomy_purpose="Covered by another tracked issue or pull request",
    ),
    LabelRegistryEntry(
        label="invalid",
        description="Not actionable as filed",
        category=RESOLUTION_CATEGORY,
    ),
    LabelRegistryEntry(
        label="wontfix",
        description="Intentionally not planned",
        category=RESOLUTION_CATEGORY,
    ),
)


def get_label_registry_entry(label: str) -> LabelRegistryEntry:
    for entry in LABEL_REGISTRY:
        if entry.label == label:
            return entry
    raise KeyError(f"unknown label registry entry: {label}")


def get_label_description(label: str) -> str:
    return get_label_registry_entry(label).description


def get_label_category(label: str) -> str:
    return get_label_registry_entry(label).category


def labels_for_category(category: str) -> tuple[str, ...]:
    return tuple(entry.label for entry in LABEL_REGISTRY if entry.category == category)


def required_label_descriptions() -> dict[str, str]:
    return {entry.label: entry.description for entry in LABEL_REGISTRY}


def required_label_taxonomy_rows() -> dict[str, tuple[str, ...]]:
    rows_by_section: dict[str, list[str]] = {}
    for entry in LABEL_REGISTRY:
        rows_by_section.setdefault(entry.taxonomy_section, []).append(
            entry.taxonomy_row
        )
    return {
        section: tuple(rows)
        for section, rows in rows_by_section.items()
    }


def validate_label_registry() -> None:
    seen_labels: set[str] = set()
    for entry in LABEL_REGISTRY:
        if entry.label in seen_labels:
            raise ValueError("duplicate label registry entry: " + entry.label)
        seen_labels.add(entry.label)
        if entry.category not in LABEL_CATEGORIES:
            raise ValueError("unknown label category: " + entry.category)
        if not entry.description:
            raise ValueError("label description must not be empty: " + entry.label)
