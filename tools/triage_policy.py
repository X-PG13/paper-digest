from __future__ import annotations

from tools.reply_policy_base import (
    ReplySnippetPolicySpec,
    collect_issue_triage_snippets,
    collect_label_taxonomy_snippets,
    validate_reply_snippet_policy_specs,
)
from tools.saved_reply_policy import get_saved_reply

DOCS_FOLLOW_UP_POLICY_LINE = (
    "If a report is closed or redirected but still exposes a docs gap, update "
    "the relevant public docs or file/link a follow-up documentation issue."
)
DOCUMENTATION_LABEL_FOLLOW_UP_RULE = (
    "`documentation` should be used for docs-only follow-up work, including "
    "gaps surfaced by a closed or redirected report."
)


TriageReplyPolicySpec = ReplySnippetPolicySpec


TRIAGE_REPLY_POLICY_SPECS = (
    TriageReplyPolicySpec(
        reply_slug="needs-info",
        issue_triage_snippets=(
            '"needs-repro" or "needs-info" by maintainers',
            (
                "Add `needs-info` or `needs-repro` only when the maintainer "
                "reply clearly says what is missing."
            ),
        ),
        label_taxonomy_snippets=(
            "| `needs-info` | The report is missing required context |",
            (
                "4. `needs-info` and `needs-repro` should be paired with a "
                "concrete maintainer"
            ),
        ),
    ),
    TriageReplyPolicySpec(
        reply_slug="needs-repro",
        issue_triage_snippets=(
            '"needs-repro" or "needs-info" by maintainers',
            "The reporter does not provide requested reproduction details after a",
        ),
        label_taxonomy_snippets=(
            "| `needs-repro` | The report needs a minimal reproduction |",
            (
                "4. `needs-info` and `needs-repro` should be paired with a "
                "concrete maintainer"
            ),
        ),
    ),
    TriageReplyPolicySpec(
        reply_slug="support-redirect",
        issue_triage_snippets=(
            "- Support: a usage, setup, or configuration question that is not yet a",
            "- The report is actually a support question and the documented answer was",
        ),
        label_taxonomy_snippets=(
            "| `support` | Usage and setup questions |",
        ),
    ),
    TriageReplyPolicySpec(
        reply_slug="security-redirect",
        issue_triage_snippets=(
            "- Security: must be redirected to the private path in `SECURITY.md`.",
            "- Reserve `security` for internal coordination after a private report has",
        ),
        label_taxonomy_snippets=(
            (
                "| `security` | Security-sensitive work that should stay private "
                "unless cleared |"
            ),
            "6. `security` should not be used for public disclosure of unpatched",
        ),
    ),
    TriageReplyPolicySpec(
        reply_slug="duplicate",
        issue_triage_snippets=(
            "- The report is a duplicate.",
        ),
        label_taxonomy_snippets=(
            "| `duplicate` | Covered by another tracked issue or pull request |",
        ),
    ),
    TriageReplyPolicySpec(
        reply_slug="out-of-scope",
        issue_triage_snippets=(
            "- The request is outside the project scope documented in `README.md` and",
        ),
        label_taxonomy_snippets=(
            "| `wontfix` | Intentionally not planned |",
        ),
    ),
    TriageReplyPolicySpec(
        reply_slug="docs-follow-up",
        issue_triage_snippets=(DOCS_FOLLOW_UP_POLICY_LINE,),
        label_taxonomy_snippets=(
            "| `documentation` | Missing, unclear, or outdated docs |",
            DOCUMENTATION_LABEL_FOLLOW_UP_RULE,
        ),
    ),
)


def required_issue_triage_snippets() -> tuple[str, ...]:
    return collect_issue_triage_snippets(TRIAGE_REPLY_POLICY_SPECS)


def required_label_taxonomy_snippets() -> tuple[str, ...]:
    return collect_label_taxonomy_snippets(TRIAGE_REPLY_POLICY_SPECS)


def validate_triage_reply_policy() -> None:
    validate_reply_snippet_policy_specs(
        TRIAGE_REPLY_POLICY_SPECS,
        duplicate_error_prefix="duplicate triage reply policy slug",
        missing_issue_triage_error_prefix=(
            "triage reply policy must define issue-triage snippets"
        ),
        missing_label_taxonomy_error_prefix=(
            "triage reply policy must define label-taxonomy snippets"
        ),
        reply_lookup=get_saved_reply,
    )
