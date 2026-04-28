from __future__ import annotations

from pathlib import Path

from tools.docs_assertions import (
    extend_contract_errors,
    normalize_text_block,
    require_expected_fields,
    require_expected_items,
    text_contains_all_snippets,
)
from tools.docs_findings import DocsCheckFinding
from tools.docs_parser import (
    extract_first_fenced_block_lines,
    extract_issue_form_fields,
    find_issue_form_field_by_id,
    parse_bullet_fields,
    parse_checklist_items,
    parse_plain_bullet_items,
)
from tools.docs_sources import (
    TextSourceOrigin,
    collect_text_by_label,
    collect_text_source_origins,
    get_workflow_section_lines,
    read_markdown_section_lines,
    resolve_repository_path,
)
from tools.lifecycle_contracts import (
    ISSUE_CLOSE_OUT_TEXT_CONTRACTS,
    ISSUE_CLOSE_OUT_TEXT_SOURCES,
    ISSUE_LINKAGE_POST_RELEASE_FORM_FIELDS,
    ISSUE_LINKAGE_RELEASE_PREP_FORM_FIELDS,
    ISSUE_LINKAGE_TEXT_CONTRACTS,
    ISSUE_LINKAGE_TEXT_SOURCES,
    ISSUE_SUMMARY_SOURCE_BINDINGS,
    MAINTAINER_ISSUE_TEXT_CONTRACTS,
    MAINTAINER_ISSUE_TEXT_SOURCES,
    POST_RELEASE_CLOSE_OUT_FORM_FIELD,
    POST_RELEASE_FORM_SOURCE,
    QUARTERLY_CLOSE_OUT_WORKFLOW_ITEMS,
    QUARTERLY_REVIEW_WORKFLOW_CLOSE_OUT_SOURCE,
    RELEASE_LIFECYCLE_TEXT_CONTRACTS,
    RELEASE_LIFECYCLE_TEXT_SOURCES,
    RELEASE_PREP_CLOSE_OUT_FORM_FIELD,
    RELEASE_PREP_FORM_SOURCE,
)


def check_release_lifecycle_contract(root: Path) -> list[DocsCheckFinding]:
    root = root.resolve()
    errors: list[DocsCheckFinding] = []
    text_by_label = collect_text_by_label(
        root,
        RELEASE_LIFECYCLE_TEXT_SOURCES,
        errors,
    )
    subject_origins = collect_text_source_origins(root, RELEASE_LIFECYCLE_TEXT_SOURCES)
    if errors:
        return errors

    extend_contract_errors(
        "release lifecycle",
        text_by_label,
        RELEASE_LIFECYCLE_TEXT_CONTRACTS,
        errors,
        subject_origins=subject_origins,
    )

    return errors


def check_maintainer_issue_contract(root: Path) -> list[DocsCheckFinding]:
    root = root.resolve()
    errors: list[DocsCheckFinding] = []
    text_by_label = collect_text_by_label(
        root,
        MAINTAINER_ISSUE_TEXT_SOURCES,
        errors,
    )
    subject_origins = collect_text_source_origins(root, MAINTAINER_ISSUE_TEXT_SOURCES)
    if errors:
        return errors

    extend_contract_errors(
        "maintainer issue",
        text_by_label,
        MAINTAINER_ISSUE_TEXT_CONTRACTS,
        errors,
        subject_origins=subject_origins,
    )

    return errors


def check_issue_linkage_contract(root: Path) -> list[DocsCheckFinding]:
    root = root.resolve()
    errors: list[DocsCheckFinding] = []
    text_by_label = collect_text_by_label(
        root,
        ISSUE_LINKAGE_TEXT_SOURCES,
        errors,
    )
    subject_origins = collect_text_source_origins(root, ISSUE_LINKAGE_TEXT_SOURCES)
    if errors:
        return errors

    extend_contract_errors(
        "issue linkage",
        text_by_label,
        ISSUE_LINKAGE_TEXT_CONTRACTS,
        errors,
        subject_origins=subject_origins,
    )

    release_prep_fields = extract_issue_form_fields(
        resolve_repository_path(root, RELEASE_PREP_FORM_SOURCE.path)
    )
    for field_contract in ISSUE_LINKAGE_RELEASE_PREP_FORM_FIELDS:
        field = find_issue_form_field_by_id(
            release_prep_fields,
            field_contract.field_id,
        )
        if field is None:
            errors.append(
                DocsCheckFinding(
                    message=(
                        "issue linkage contract "
                        f"'{field_contract.field_id}' missing field "
                        f"'{field_contract.field_id}' from "
                        f"{RELEASE_PREP_FORM_SOURCE.path}"
                    ),
                    path=RELEASE_PREP_FORM_SOURCE.path,
                )
            )
            continue
        if normalize_text_block(field.label or "") != normalize_text_block(
            field_contract.label
        ):
            errors.append(
                DocsCheckFinding(
                    message=(
                        "issue linkage contract "
                        f"'{field_contract.field_id}' has unexpected label for field "
                        f"'{field_contract.field_id}' in "
                        f"{RELEASE_PREP_FORM_SOURCE.path}"
                    ),
                    path=RELEASE_PREP_FORM_SOURCE.path,
                    line=field.line_number,
                    end_line=field.end_line,
                )
            )
        if not field_contract.checklist_items:
            continue
        subject = f"{RELEASE_PREP_FORM_SOURCE.path}#{field_contract.field_id}"
        require_expected_items(
            "issue linkage",
            "release-prep linkage fields",
            subject,
            parse_checklist_items(list(field.value_lines)),
            field_contract.checklist_items,
            errors,
            subject_origins={
                subject: TextSourceOrigin(
                    path=RELEASE_PREP_FORM_SOURCE.path,
                    line=field.line_number,
                    end_line=field.end_line,
                )
            },
        )

    post_release_fields = extract_issue_form_fields(
        resolve_repository_path(root, POST_RELEASE_FORM_SOURCE.path)
    )
    for field_contract in ISSUE_LINKAGE_POST_RELEASE_FORM_FIELDS:
        field = find_issue_form_field_by_id(
            post_release_fields,
            field_contract.field_id,
        )
        if field is None:
            errors.append(
                DocsCheckFinding(
                    message=(
                        "issue linkage contract 'post-release linkage fields' missing "
                        f"field '{field_contract.field_id}' from "
                        f"{POST_RELEASE_FORM_SOURCE.path}"
                    ),
                    path=POST_RELEASE_FORM_SOURCE.path,
                )
            )
            continue
        if normalize_text_block(field.label or "") != normalize_text_block(
            field_contract.label
        ):
            errors.append(
                DocsCheckFinding(
                    message=(
                        "issue linkage contract 'post-release linkage fields' has "
                        f"unexpected label for field '{field_contract.field_id}' in "
                        f"{POST_RELEASE_FORM_SOURCE.path}"
                    ),
                    path=POST_RELEASE_FORM_SOURCE.path,
                    line=field.line_number,
                    end_line=field.end_line,
                )
            )

    return errors


def check_issue_close_out_contract(root: Path) -> list[DocsCheckFinding]:
    root = root.resolve()
    errors: list[DocsCheckFinding] = []
    text_by_label = collect_text_by_label(
        root,
        ISSUE_CLOSE_OUT_TEXT_SOURCES,
        errors,
    )
    subject_origins = collect_text_source_origins(root, ISSUE_CLOSE_OUT_TEXT_SOURCES)
    if errors:
        return errors

    extend_contract_errors(
        "issue close-out",
        text_by_label,
        ISSUE_CLOSE_OUT_TEXT_CONTRACTS,
        errors,
        subject_origins=subject_origins,
    )

    quarterly_close_out_items = parse_plain_bullet_items(
        get_workflow_section_lines(root, QUARTERLY_REVIEW_WORKFLOW_CLOSE_OUT_SOURCE)
    )
    require_expected_items(
        "issue close-out",
        "quarterly review close-out rule",
        QUARTERLY_REVIEW_WORKFLOW_CLOSE_OUT_SOURCE.label,
        quarterly_close_out_items,
        QUARTERLY_CLOSE_OUT_WORKFLOW_ITEMS,
        errors,
        subject_origins=subject_origins,
    )

    release_prep_fields = extract_issue_form_fields(
        resolve_repository_path(root, RELEASE_PREP_FORM_SOURCE.path)
    )
    release_prep_close_out = find_issue_form_field_by_id(
        release_prep_fields,
        RELEASE_PREP_CLOSE_OUT_FORM_FIELD.field_id,
    )
    if release_prep_close_out is None:
        errors.append(
            DocsCheckFinding(
                message=(
                    "issue close-out contract 'release-preparation close-out rule' "
                    f"missing field '{RELEASE_PREP_CLOSE_OUT_FORM_FIELD.field_id}' "
                    f"from {RELEASE_PREP_FORM_SOURCE.path}"
                ),
                path=RELEASE_PREP_FORM_SOURCE.path,
            )
        )
    else:
        if normalize_text_block(
            release_prep_close_out.label or ""
        ) != normalize_text_block(RELEASE_PREP_CLOSE_OUT_FORM_FIELD.label):
            errors.append(
                DocsCheckFinding(
                    message=(
                        "issue close-out contract "
                        "'release-preparation close-out rule' "
                        "has unexpected label for field "
                        f"'{RELEASE_PREP_CLOSE_OUT_FORM_FIELD.field_id}' in "
                        f"{RELEASE_PREP_FORM_SOURCE.path}"
                    ),
                    path=RELEASE_PREP_FORM_SOURCE.path,
                    line=release_prep_close_out.line_number,
                    end_line=release_prep_close_out.end_line,
                )
            )
        subject = (
            f"{RELEASE_PREP_FORM_SOURCE.path}#"
            f"{RELEASE_PREP_CLOSE_OUT_FORM_FIELD.field_id}"
        )
        require_expected_items(
            "issue close-out",
            "release-preparation close-out rule",
            subject,
            parse_checklist_items(list(release_prep_close_out.value_lines)),
            RELEASE_PREP_CLOSE_OUT_FORM_FIELD.checklist_items,
            errors,
            subject_origins={
                subject: TextSourceOrigin(
                    path=RELEASE_PREP_FORM_SOURCE.path,
                    line=release_prep_close_out.line_number,
                    end_line=release_prep_close_out.end_line,
                )
            },
        )

    post_release_fields = extract_issue_form_fields(
        resolve_repository_path(root, POST_RELEASE_FORM_SOURCE.path)
    )
    post_release_close_out = find_issue_form_field_by_id(
        post_release_fields,
        POST_RELEASE_CLOSE_OUT_FORM_FIELD.field_id,
    )
    if post_release_close_out is None:
        errors.append(
            DocsCheckFinding(
                message=(
                    "issue close-out contract 'post-release close-out rule' missing "
                    f"field '{POST_RELEASE_CLOSE_OUT_FORM_FIELD.field_id}' from "
                    f"{POST_RELEASE_FORM_SOURCE.path}"
                ),
                path=POST_RELEASE_FORM_SOURCE.path,
            )
        )
    else:
        if normalize_text_block(
            post_release_close_out.label or ""
        ) != normalize_text_block(POST_RELEASE_CLOSE_OUT_FORM_FIELD.label):
            errors.append(
                DocsCheckFinding(
                    message=(
                        "issue close-out contract 'post-release close-out rule' has "
                        "unexpected label for field "
                        f"'{POST_RELEASE_CLOSE_OUT_FORM_FIELD.field_id}' in "
                        f"{POST_RELEASE_FORM_SOURCE.path}"
                    ),
                    path=POST_RELEASE_FORM_SOURCE.path,
                    line=post_release_close_out.line_number,
                    end_line=post_release_close_out.end_line,
                )
            )
        subject = (
            f"{POST_RELEASE_FORM_SOURCE.path}#"
            f"{POST_RELEASE_CLOSE_OUT_FORM_FIELD.field_id}"
        )
        require_expected_items(
            "issue close-out",
            "post-release close-out rule",
            subject,
            parse_checklist_items(list(post_release_close_out.value_lines)),
            POST_RELEASE_CLOSE_OUT_FORM_FIELD.checklist_items,
            errors,
            subject_origins={
                subject: TextSourceOrigin(
                    path=POST_RELEASE_FORM_SOURCE.path,
                    line=post_release_close_out.line_number,
                    end_line=post_release_close_out.end_line,
                )
            },
        )

    return errors


def check_issue_summary_semantics_contract(root: Path) -> list[DocsCheckFinding]:
    root = root.resolve()
    errors: list[DocsCheckFinding] = []
    summary_sources = tuple(
        source
        for binding in ISSUE_SUMMARY_SOURCE_BINDINGS
        for source in (binding.doc_source, binding.workflow_source)
    )
    subject_origins = collect_text_source_origins(root, summary_sources)
    for binding in ISSUE_SUMMARY_SOURCE_BINDINGS:
        summary_lines = read_markdown_section_lines(
            resolve_repository_path(root, binding.doc_source.path),
            binding.doc_source.heading,
            errors,
            label=binding.doc_source.path,
            visible_only=binding.doc_source.visible_only,
        )
        if summary_lines is None:
            continue

        summary_text = "\n".join(summary_lines)
        template_lines = extract_first_fenced_block_lines(summary_lines)
        if template_lines is None:
            errors.append(
                DocsCheckFinding(
                    message=(
                        "issue summary semantics contract "
                        f"'{binding.contract.name}' missing fenced template from "
                        f"{binding.doc_source.label}"
                    ),
                    path=binding.doc_source.path,
                    line=subject_origins[binding.doc_source.label].line,
                    end_line=subject_origins[binding.doc_source.label].end_line,
                )
            )
            continue

        require_expected_fields(
            "issue summary semantics",
            binding.contract.name,
            binding.doc_source.label,
            parse_bullet_fields(template_lines),
            dict(binding.contract.doc_fields),
            errors,
            subject_origins=subject_origins,
        )
        if not text_contains_all_snippets(
            summary_text,
            binding.contract.guidance_snippets,
        ):
            errors.append(
                DocsCheckFinding(
                    message=(
                        "issue summary semantics contract "
                        f"'{binding.contract.name}' missing prefill guidance from "
                        f"{binding.doc_source.label}"
                    ),
                    path=binding.doc_source.path,
                    line=subject_origins[binding.doc_source.label].line,
                    end_line=subject_origins[binding.doc_source.label].end_line,
                )
            )

        require_expected_fields(
            "issue summary semantics",
            binding.contract.name,
            binding.workflow_source.label,
            parse_bullet_fields(
                get_workflow_section_lines(root, binding.workflow_source)
            ),
            dict(binding.contract.workflow_defaults),
            errors,
            subject_origins=subject_origins,
        )

    return errors
