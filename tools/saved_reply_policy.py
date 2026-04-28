from __future__ import annotations

from tools.reply_policy_base import (
    ReplyContractSpec,
    collect_saved_reply_snippets,
    get_reply_spec_by_slug,
    validate_reply_contract_specs,
)
from tools.support_policy import SUPPORT_REQUEST_FIELDS

NEEDS_INFO_REPLY_HEADER = (
    "Thanks for the report. This issue is still missing some of the minimum "
    "context required for deeper triage."
)
NEEDS_INFO_REPLY_INTRO = "Please update the issue with:"
NEEDS_INFO_REPLY_ITEMS = (
    "the exact command or workflow path",
    "a minimal config snippet with secrets removed",
    "the observed result and expected result",
    "Python version, OS, and project version or commit",
)
NEEDS_INFO_REPLY_FOOTER = (
    "Once that context is added, maintainers can evaluate the report on a "
    "supported path."
)

NEEDS_REPRO_REPLY_HEADER = (
    "Thanks for the report. Maintainers still need a minimal reproduction "
    "before this can move forward."
)
NEEDS_REPRO_REPLY_LINES = (
    "Please narrow the report to the smallest config, command, or workflow "
    "path that still shows the problem, and include the exact output you see.",
)

SUPPORT_REDIRECT_REPLY_HEADER = (
    "This looks more like a usage or configuration question than a confirmed defect."
)
SUPPORT_REDIRECT_REPLY_INTRO = (
    "Please continue through the support path in `SUPPORT.md` after checking "
    "the pre-read docs listed there, and include:"
)
SUPPORT_REDIRECT_REPLY_FOOTER = (
    "If the behavior turns out to be a reproducible bug on a supported path, "
    "we can reopen or convert it."
)

SECURITY_REDIRECT_REPLY_HEADER = "Please do not continue this report in public."
SECURITY_REDIRECT_REPLY_LINES = (
    (
        "Potential security issues should follow the private reporting path "
        "documented in `SECURITY.md`."
    ),
    (
        "If you can still edit the public issue, remove any exploit details, "
        "secrets, tokens, or private configuration before maintainers continue."
    ),
)

DUPLICATE_REPLY_HEADER = (
    "Thanks for the report. This is being tracked elsewhere, so I am closing "
    "this as a duplicate."
)
DUPLICATE_REPLY_LINES = ("Canonical tracking issue or pull request:",)
DUPLICATE_REPLY_ITEMS = ("link here",)
DUPLICATE_REPLY_FOOTER = (
    "If you have new reproduction details that are not already covered there, "
    "add them on the canonical thread."
)

OUT_OF_SCOPE_REPLY_HEADER = (
    "Thanks for the proposal. This is outside the current documented scope of "
    "Paper Digest, so maintainers are not planning to take it on right now."
)
OUT_OF_SCOPE_REPLY_LINES = (
    "If the repository scope changes later, or if you want to prototype the "
    "idea in a fork first, a future proposal can link back to that work.",
)

DOCS_FOLLOW_UP_REPLY_HEADER = (
    "Thanks. This surfaced a docs gap even if the immediate report is being "
    "closed or redirected."
)
DOCS_FOLLOW_UP_REPLY_LINES = ("Maintainers should either:",)
DOCS_FOLLOW_UP_REPLY_ITEMS = (
    "update the relevant public docs in this cycle, or",
    "file/link a follow-up documentation issue so the gap stays tracked.",
)


SavedReplySpec = ReplyContractSpec


SAVED_REPLY_SPECS = (
    SavedReplySpec(
        slug="needs-info",
        header=NEEDS_INFO_REPLY_HEADER,
        body_lines=(NEEDS_INFO_REPLY_INTRO,),
        bullet_items=NEEDS_INFO_REPLY_ITEMS,
        footer_lines=(NEEDS_INFO_REPLY_FOOTER,),
    ),
    SavedReplySpec(
        slug="support-redirect",
        header=SUPPORT_REDIRECT_REPLY_HEADER,
        body_lines=(SUPPORT_REDIRECT_REPLY_INTRO,),
        bullet_items=tuple(
            field.support_md_bullet
            for field in SUPPORT_REQUEST_FIELDS
            if field.support_md_bullet is not None
        ),
        footer_lines=(SUPPORT_REDIRECT_REPLY_FOOTER,),
    ),
    SavedReplySpec(
        slug="security-redirect",
        header=SECURITY_REDIRECT_REPLY_HEADER,
        body_lines=SECURITY_REDIRECT_REPLY_LINES,
    ),
    SavedReplySpec(
        slug="needs-repro",
        header=NEEDS_REPRO_REPLY_HEADER,
        body_lines=NEEDS_REPRO_REPLY_LINES,
    ),
    SavedReplySpec(
        slug="duplicate",
        header=DUPLICATE_REPLY_HEADER,
        body_lines=DUPLICATE_REPLY_LINES,
        bullet_items=DUPLICATE_REPLY_ITEMS,
        footer_lines=(DUPLICATE_REPLY_FOOTER,),
    ),
    SavedReplySpec(
        slug="out-of-scope",
        header=OUT_OF_SCOPE_REPLY_HEADER,
        body_lines=OUT_OF_SCOPE_REPLY_LINES,
    ),
    SavedReplySpec(
        slug="docs-follow-up",
        header=DOCS_FOLLOW_UP_REPLY_HEADER,
        body_lines=DOCS_FOLLOW_UP_REPLY_LINES,
        bullet_items=DOCS_FOLLOW_UP_REPLY_ITEMS,
    ),
)


def get_saved_reply(slug: str) -> SavedReplySpec:
    return get_reply_spec_by_slug(
        SAVED_REPLY_SPECS,
        slug,
        unknown_error_prefix="unknown saved reply slug",
    )


def required_saved_reply_snippets(*slugs: str) -> tuple[str, ...]:
    return collect_saved_reply_snippets(SAVED_REPLY_SPECS, *slugs)


def validate_saved_reply_contract() -> None:
    validate_reply_contract_specs(
        SAVED_REPLY_SPECS,
        duplicate_error_prefix="duplicate saved reply slug",
        missing_header_error_prefix="saved reply must define a header",
        empty_reply_error_prefix="saved reply must not be empty",
        empty_body_error_prefix="saved reply body lines must not be empty",
        empty_bullet_error_prefix="saved reply bullet items must not be empty",
        empty_footer_error_prefix="saved reply footer lines must not be empty",
    )
