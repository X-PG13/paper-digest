from __future__ import annotations

from dataclasses import dataclass

PR_HYGIENE_MARKER = "<!-- pr-hygiene-reminder -->"
PR_TEMPLATE_LINKED_ISSUE_LABEL = "Linked issue or proposal"
PR_TEMPLATE_NO_LINKED_ISSUE_LABEL = "No linked issue needed."
PR_TEMPLATE_NO_CHANGELOG_LABEL = "No changelog entry needed."
PR_TEMPLATE_NO_DOCS_LABEL = "No doc update needed."

PR_HYGIENE_COMMENT_HEADER = (
    "This PR likely needs a docs, changelog, or context acknowledgement before "
    "merge:"
)
PR_HYGIENE_COMMENT_FOOTER = (
    "Update the relevant files or check the matching `No ... needed.` box in "
    "the PR template if the omission is intentional."
)


@dataclass(frozen=True)
class PrHygieneReminderSpec:
    key: str
    checkbox_label: str
    message: str


PR_HYGIENE_REMINDERS = (
    PrHygieneReminderSpec(
        key="changelog",
        checkbox_label=PR_TEMPLATE_NO_CHANGELOG_LABEL,
        message=(
            "This PR changes runtime, workflow, or repository-operational files "
            "but does not update `CHANGELOG.md` and does not check "
            f"`{PR_TEMPLATE_NO_CHANGELOG_LABEL}` in the PR template."
        ),
    ),
    PrHygieneReminderSpec(
        key="docs",
        checkbox_label=PR_TEMPLATE_NO_DOCS_LABEL,
        message=(
            "This PR changes runtime, workflow, or repository-operational files "
            "but does not update any public docs and does not check "
            f"`{PR_TEMPLATE_NO_DOCS_LABEL}` in the PR template."
        ),
    ),
    PrHygieneReminderSpec(
        key="linked_issue",
        checkbox_label=PR_TEMPLATE_NO_LINKED_ISSUE_LABEL,
        message=(
            "This PR changes runtime, workflow, or repository-operational files "
            "but does not link an issue or proposal and does not check "
            f"`{PR_TEMPLATE_NO_LINKED_ISSUE_LABEL}` in the PR template."
        ),
    ),
)


def get_pr_hygiene_reminder(key: str) -> PrHygieneReminderSpec:
    for reminder in PR_HYGIENE_REMINDERS:
        if reminder.key == key:
            return reminder
    raise KeyError(f"unknown PR hygiene reminder key: {key}")


def required_pull_request_template_lines() -> tuple[str, ...]:
    return (
        f"- {PR_TEMPLATE_LINKED_ISSUE_LABEL}:",
        f"- [ ] {PR_TEMPLATE_NO_LINKED_ISSUE_LABEL}",
        f"- [ ] {PR_TEMPLATE_NO_CHANGELOG_LABEL}",
        f"- [ ] {PR_TEMPLATE_NO_DOCS_LABEL}",
    )


def validate_pr_hygiene_contract() -> None:
    seen_keys: set[str] = set()
    seen_checkboxes: set[str] = set()
    for reminder in PR_HYGIENE_REMINDERS:
        if reminder.key in seen_keys:
            raise ValueError(f"duplicate PR hygiene reminder key: {reminder.key}")
        seen_keys.add(reminder.key)
        if reminder.checkbox_label in seen_checkboxes:
            raise ValueError(
                "duplicate PR hygiene checkbox label: " + reminder.checkbox_label
            )
        seen_checkboxes.add(reminder.checkbox_label)
        if not reminder.checkbox_label.endswith("."):
            raise ValueError(
                "PR hygiene checkbox label must end with a period: "
                + reminder.checkbox_label
            )
        if f"`{reminder.checkbox_label}`" not in reminder.message:
            raise ValueError(
                "PR hygiene reminder must mention its checkbox label: " + reminder.key
            )
