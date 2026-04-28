from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TextIO

from tools.issue_intake_policy import (
    BUG_LABEL,
    COMMUNITY_TRIAGE_MARKER,
    ISSUE_INTAKE_COMMENT_FOOTER,
    ISSUE_INTAKE_COMMENT_HEADER,
    ISSUE_INTAKE_FIELDS,
    ISSUE_INTAKE_SECTIONS,
    NEEDS_INFO_LABEL,
)
from tools.support_policy import (
    SUPPORT_LABEL,
    SUPPORT_PRECHECK_DOCS,
    SUPPORT_PRECHECK_MISSING_MESSAGE,
    SUPPORT_REQUEST_CHECKLIST_LABEL,
    SUPPORT_REQUEST_FIELDS,
    SUPPORT_TRIAGE_COMMENT_FOOTER,
    SUPPORT_TRIAGE_COMMENT_HEADER,
    SUPPORT_TRIAGE_MARKER,
)
from tools.workflow_outputs import emit_workflow_outputs

DEFAULT_ISSUE_BODY_ENV = "ISSUE_BODY"
DEFAULT_ISSUE_LABELS_JSON_ENV = "ISSUE_LABELS_JSON"


@dataclass(frozen=True)
class IssueIntakeResult:
    mode: str
    marker: str
    comment_body: str | None
    needs_info_action: str
    missing: tuple[str, ...]


def extract_section(body: str, title: str) -> str:
    escaped = re.escape(title)
    pattern = re.compile(
        rf"#{{2,3}} {escaped}\s*\n([\s\S]*?)(?=\n#{{2,3}} |$)",
        flags=re.IGNORECASE,
    )
    match = pattern.search(body)
    return match.group(1).strip() if match is not None else ""


def section_has_content(section: str, placeholder_patterns: Sequence[str]) -> bool:
    if not section:
        return False
    meaningful_lines = [
        line.strip()
        for line in section.splitlines()
        if line.strip()
        and not any(
            re.search(pattern, line.strip(), flags=re.IGNORECASE)
            for pattern in placeholder_patterns
        )
    ]
    return bool(meaningful_lines)


def section_contains_all_items(section: str, expected_items: Sequence[str]) -> bool:
    if not section:
        return False
    return all(item in section for item in expected_items)


def field_filled(body: str, name: str) -> bool:
    escaped = re.escape(name)
    match = re.search(rf"^- {escaped}:\s*(.+)$", body, flags=re.MULTILINE)
    if match and match.group(1).strip():
        return True
    return section_has_content(
        extract_section(body, name),
        [r"^_No response_$"],
    )


def parse_label_names(labels_payload: str) -> tuple[str, ...]:
    payload = json.loads(labels_payload)
    if not isinstance(payload, list):
        raise ValueError("issue labels payload must be a JSON list")

    label_names: list[str] = []
    for item in payload:
        if isinstance(item, str):
            label_names.append(item)
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            label_names.append(item["name"])
    return tuple(label_names)


def build_intake_result(
    *,
    missing: Sequence[str],
    has_needs_info: bool,
    marker: str,
    header: str,
    footer: str,
) -> IssueIntakeResult:
    if missing:
        comment_body = "\n".join(
            [
                marker,
                header,
                "",
                *[f"- {item}" for item in missing],
                "",
                footer,
            ]
        )
        return IssueIntakeResult(
            mode="upsert",
            marker=marker,
            comment_body=comment_body,
            needs_info_action="none" if has_needs_info else "add",
            missing=tuple(missing),
        )

    return IssueIntakeResult(
        mode="delete",
        marker=marker,
        comment_body=None,
        needs_info_action="remove" if has_needs_info else "none",
        missing=(),
    )


def evaluate_issue_intake(
    body: str,
    label_names: Sequence[str],
    *,
    marker: str = COMMUNITY_TRIAGE_MARKER,
    support_marker: str = SUPPORT_TRIAGE_MARKER,
) -> IssueIntakeResult:
    label_set = set(label_names)
    has_needs_info = NEEDS_INFO_LABEL in label_set

    if BUG_LABEL in label_set:
        missing: list[str] = []
        for section in ISSUE_INTAKE_SECTIONS:
            if not section_has_content(
                extract_section(body, section.label),
                section.placeholder_patterns,
            ):
                missing.append(section.missing_message)

        for issue_field in ISSUE_INTAKE_FIELDS:
            if not field_filled(body, issue_field.label):
                missing.append(issue_field.missing_message)

        return build_intake_result(
            missing=missing,
            has_needs_info=has_needs_info,
            marker=marker,
            header=ISSUE_INTAKE_COMMENT_HEADER,
            footer=ISSUE_INTAKE_COMMENT_FOOTER,
        )

    if SUPPORT_LABEL in label_set:
        missing = []
        docs_checked = extract_section(body, SUPPORT_REQUEST_CHECKLIST_LABEL)
        if not section_contains_all_items(
            docs_checked,
            tuple(doc.path for doc in SUPPORT_PRECHECK_DOCS),
        ):
            missing.append(SUPPORT_PRECHECK_MISSING_MESSAGE)

        for support_field in SUPPORT_REQUEST_FIELDS:
            if support_field.required and not field_filled(body, support_field.label):
                assert support_field.missing_message is not None
                missing.append(support_field.missing_message)

        return build_intake_result(
            missing=missing,
            has_needs_info=has_needs_info,
            marker=support_marker,
            header=SUPPORT_TRIAGE_COMMENT_HEADER,
            footer=SUPPORT_TRIAGE_COMMENT_FOOTER,
        )

    return IssueIntakeResult(
        mode="delete",
        marker=marker,
        comment_body=None,
        needs_info_action="none",
        missing=(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate issue-intake completeness for community triage."
    )
    parser.add_argument(
        "--body-env",
        default=DEFAULT_ISSUE_BODY_ENV,
        help=(
            "Environment variable with the issue body. Defaults to "
            f"{DEFAULT_ISSUE_BODY_ENV}."
        ),
    )
    parser.add_argument(
        "--labels-json-env",
        default=DEFAULT_ISSUE_LABELS_JSON_ENV,
        help=(
            "Environment variable with a JSON array of label names or GitHub "
            f"label objects. Defaults to {DEFAULT_ISSUE_LABELS_JSON_ENV}."
        ),
    )
    return parser


def main(
    *,
    body_env: str = DEFAULT_ISSUE_BODY_ENV,
    labels_json_env: str = DEFAULT_ISSUE_LABELS_JSON_ENV,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    env: dict[str, str] | None = None,
) -> int:
    current_env = os.environ if env is None else env
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    body = current_env.get(body_env, "")
    labels_payload = current_env.get(labels_json_env, "")
    if labels_payload == "":
        print(
            (
                "community triage evaluation failed: missing labels payload in "
                f"{labels_json_env}"
            ),
            file=error_stream,
        )
        return 1

    try:
        result = evaluate_issue_intake(body, parse_label_names(labels_payload))
    except ValueError as exc:
        print(f"community triage evaluation failed: {exc}", file=error_stream)
        return 1

    outputs = {
        "mode": result.mode,
        "marker": result.marker,
        "needs-info-action": result.needs_info_action,
    }
    if result.comment_body is not None:
        outputs["comment-body"] = result.comment_body
    emit_workflow_outputs(outputs, env=current_env, stdout=output_stream)
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(
        body_env=args.body_env,
        labels_json_env=args.labels_json_env,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
