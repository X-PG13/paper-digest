from __future__ import annotations

from tools.intake_policy_base import ContactLinkSpec, validate_contact_link_specs
from tools.issue_form_policy import (
    BUG_REPORT_FORM_PATH,
    ROUTING_LABEL_ISSUE_FORM_GROUP,
    SUPPORT_REQUEST_FORM_PATH,
    issue_form_labels_for_group,
)
from tools.issue_intake_policy import BUG_LABEL
from tools.label_policy_base import (
    ArtifactContract,
    LabelPolicySpec,
    collect_artifact_snippets_by_path,
    collect_issue_triage_snippets,
    collect_label_descriptions,
    collect_label_taxonomy_snippets,
    collect_release_note_categories,
    collect_release_note_excluded_labels,
    validate_label_policy_specs,
)
from tools.label_registry import (
    PLANNING_CATEGORY,
    ROUTING_CATEGORY,
    get_label_category,
    get_label_description,
)
from tools.support_policy import (
    SUPPORT_CONTACT_LINK,
    SUPPORT_LABEL,
)

PROPOSAL_LABEL = "proposal"
DEPENDENCIES_LABEL = "dependencies"
SECURITY_LABEL = "security"

SECURITY_CONTACT_LINK = ContactLinkSpec(
    name="Security Policy",
    target="SECURITY.md",
    about=(
        "Report suspected vulnerabilities privately instead of opening a public issue."
    ),
)
SECURITY_CONTACT_LINK_NAME = SECURITY_CONTACT_LINK.name
SECURITY_CONTACT_LINK_TARGET = SECURITY_CONTACT_LINK.target
SECURITY_CONTACT_LINK_ABOUT = SECURITY_CONTACT_LINK.about
PROPOSAL_CONTACT_LINK = ContactLinkSpec(
    name="Proposal And Discussion Policy",
    target="docs/discussions-policy.md",
    about=(
        "Use this when deciding between support, feature, proposal, or future "
        "discussion paths."
    ),
)
PROPOSAL_CONTACT_LINK_NAME = PROPOSAL_CONTACT_LINK.name
PROPOSAL_CONTACT_LINK_TARGET = PROPOSAL_CONTACT_LINK.target
PROPOSAL_CONTACT_LINK_ABOUT = PROPOSAL_CONTACT_LINK.about

RoutingArtifactContract = ArtifactContract
RoutingLabelSpec = LabelPolicySpec

ROUTING_LABEL_SPECS = (
    RoutingLabelSpec(
        label=BUG_LABEL,
        label_json_description=get_label_description(BUG_LABEL),
        issue_triage_snippets=(
            "- Bug: a supported-path behavior regression or defect with a "
            "reproducible case.",
            (
                "`.github/workflows/community-triage.yml` adds `needs-info` to "
                "bug reports that still miss the minimum reproducibility "
                "fields from the bug template."
            ),
        ),
        label_taxonomy_snippets=(
            "| `bug` | Confirmed or suspected defects on supported paths |",
        ),
        artifact_contracts=(
            RoutingArtifactContract(
                path=BUG_REPORT_FORM_PATH,
                snippets=(
                    "Security reports belong in `SECURITY.md`",
                ),
            ),
        ),
        release_note_category="Fixes",
    ),
    RoutingLabelSpec(
        label=SUPPORT_LABEL,
        label_json_description=get_label_description(SUPPORT_LABEL),
        issue_triage_snippets=(
            (
                "- Support: a usage, setup, or configuration question that is "
                "not yet a confirmed bug."
            ),
            (
                "`.github/ISSUE_TEMPLATE/config.yml` routes security, support, "
                "and proposal contact links to the correct public policy docs."
            ),
            (
                "The same workflow also adds `needs-info` to support requests "
                "that still miss confirmation that the pre-read docs were "
                "checked or the minimum environment context from the support "
                "template."
            ),
        ),
        label_taxonomy_snippets=(
            "| `support` | Usage and setup questions |",
            (
                "`.github/ISSUE_TEMPLATE/config.yml` keeps security, support, "
                "and proposal contact links aligned with the public routing docs."
            ),
        ),
        artifact_contracts=(
            RoutingArtifactContract(
                path=SUPPORT_REQUEST_FORM_PATH,
                snippets=(
                    "Security problems still belong in `SECURITY.md`.",
                ),
            ),
            RoutingArtifactContract(
                path="docs/discussions-policy.md",
                snippets=(
                    "- `Q&A` -> support request.",
                ),
            ),
        ),
        release_note_excluded=True,
    ),
    RoutingLabelSpec(
        label=PROPOSAL_LABEL,
        label_json_description=get_label_description(PROPOSAL_LABEL),
        issue_triage_snippets=(
            (
                "- Proposal: a larger product, workflow, or governance change "
                "that needs scoped discussion before implementation."
            ),
            (
                "- Add `proposal` when an issue is intended to shape roadmap, "
                "governance, or a larger design direction before "
                "implementation starts."
            ),
            (
                "The same workflow applies `documentation`, `maintenance`, "
                "`dependencies`, and `proposal` to pull requests based on "
                "changed paths and actor metadata."
            ),
            (
                "`.github/ISSUE_TEMPLATE/config.yml` routes security, support, "
                "and proposal contact links to the correct public policy docs."
            ),
        ),
        label_taxonomy_snippets=(
            (
                "| `proposal` | Larger design, workflow, governance, or roadmap "
                "proposals |"
            ),
            (
                "`.github/ISSUE_TEMPLATE/config.yml` keeps security, support, "
                "and proposal contact links aligned with the public routing docs."
            ),
        ),
        artifact_contracts=(
            RoutingArtifactContract(
                path="docs/discussions-policy.md",
                snippets=(
                    (
                        "Concrete feature or workflow proposals should use the "
                        "proposal or feature issue templates so they can be "
                        "tracked and labeled."
                    ),
                    "- `Ideas` -> feature request or proposal issue.",
                ),
            ),
        ),
        auto_pr_routing_paths=("docs/roadmap-policy.md",),
    ),
    RoutingLabelSpec(
        label=DEPENDENCIES_LABEL,
        label_json_description=get_label_description(DEPENDENCIES_LABEL),
        issue_triage_snippets=(
            (
                "- Add `dependencies` to dependency-update PRs or issues that "
                "exist mainly to track ecosystem maintenance."
            ),
            (
                "The same workflow applies `documentation`, `maintenance`, "
                "`dependencies`, and `proposal` to pull requests based on "
                "changed paths and actor metadata."
            ),
            (
                "Dependabot and dependency-review flows use `dependencies` and "
                "`maintenance` for dependency maintenance intake."
            ),
        ),
        label_taxonomy_snippets=(
            "| `dependencies` | Dependency updates and ecosystem-maintenance changes |",
            (
                "`.github/dependabot.yml` and dependency-maintenance workflows "
                "use `dependencies` together with `maintenance` for automated "
                "dependency intake."
            ),
        ),
        artifact_contracts=(
            RoutingArtifactContract(
                path=".github/dependabot.yml",
                snippets=(
                    '- "dependencies"',
                    '- "maintenance"',
                ),
            ),
            RoutingArtifactContract(
                path="docs/dependency-policy.md",
                snippets=(
                    "Dependency pull requests should carry the `dependencies` label",
                    (
                        "`.github/dependabot.yml` is the automated source of "
                        "routine update pull"
                    ),
                ),
            ),
        ),
        auto_pr_routing_paths=(".github/dependabot.yml",),
        auto_pr_routing_actor="dependabot[bot]",
        release_note_category="Dependencies",
    ),
    RoutingLabelSpec(
        label=SECURITY_LABEL,
        label_json_description=get_label_description(SECURITY_LABEL),
        issue_triage_snippets=(
            "- Security: must be redirected to the private path in `SECURITY.md`.",
            (
                "- Reserve `security` for internal coordination after a private "
                "report has already been routed correctly."
            ),
            (
                "`.github/ISSUE_TEMPLATE/config.yml` routes security, support, "
                "and proposal contact links to the correct public policy docs."
            ),
        ),
        label_taxonomy_snippets=(
            (
                "| `security` | Security-sensitive work that should stay private "
                "unless cleared |"
            ),
            (
                "`.github/ISSUE_TEMPLATE/config.yml` keeps security, support, "
                "and proposal contact links aligned with the public routing docs."
            ),
        ),
        artifact_contracts=(
            RoutingArtifactContract(
                path="SECURITY.md",
                snippets=(
                    "Do not open a public issue for a suspected security problem.",
                    "report the issue privately",
                ),
            ),
            RoutingArtifactContract(
                path="docs/discussions-policy.md",
                snippets=(
                    (
                        "- Security reports do not belong in Discussions. "
                        "Follow `SECURITY.md`."
                    ),
                ),
            ),
        ),
    ),
)


def required_issue_triage_snippets() -> tuple[str, ...]:
    return collect_issue_triage_snippets(ROUTING_LABEL_SPECS)


def required_label_taxonomy_snippets() -> tuple[str, ...]:
    return collect_label_taxonomy_snippets(ROUTING_LABEL_SPECS)


def required_label_descriptions() -> dict[str, str]:
    return collect_label_descriptions(ROUTING_LABEL_SPECS)


def required_artifact_snippets_by_path() -> dict[str, tuple[str, ...]]:
    return collect_artifact_snippets_by_path(ROUTING_LABEL_SPECS)


def required_issue_form_labels_by_path() -> dict[str, tuple[str, ...]]:
    return issue_form_labels_for_group(ROUTING_LABEL_ISSUE_FORM_GROUP)


def required_issue_template_contact_links() -> tuple[ContactLinkSpec, ...]:
    return (
        SECURITY_CONTACT_LINK,
        SUPPORT_CONTACT_LINK,
        PROPOSAL_CONTACT_LINK,
    )


def required_release_note_categories() -> dict[str, tuple[str, ...]]:
    return collect_release_note_categories(ROUTING_LABEL_SPECS)


def required_release_note_excluded_labels() -> tuple[str, ...]:
    return collect_release_note_excluded_labels(ROUTING_LABEL_SPECS)


def validate_routing_label_policy() -> None:
    validate_contact_link_specs(
        required_issue_template_contact_links(),
        duplicate_name_error_prefix="duplicate routing contact link",
    )
    issue_form_labels_for_group(ROUTING_LABEL_ISSUE_FORM_GROUP)
    validate_label_policy_specs(
        ROUTING_LABEL_SPECS,
        duplicate_error_prefix="duplicate routing label",
        missing_issue_triage_error_prefix=(
            "routing label must define issue-triage snippets"
        ),
        missing_label_taxonomy_error_prefix=(
            "routing label must define label-taxonomy snippets"
        ),
        manual_only_auto_error_prefix=(
            "manual-only routing label must not define automated PR routing paths"
        ),
    )
    for spec in ROUTING_LABEL_SPECS:
        if get_label_category(spec.label) not in (ROUTING_CATEGORY, PLANNING_CATEGORY):
            raise ValueError(
                "routing label must stay in routing/planning categories: "
                + spec.label
            )
