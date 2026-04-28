from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from tools.docs_findings import DocsCheckFinding
from tools.docs_pipeline import (
    DOCS_CHECK_COMMAND,
    DocsCheckReport,
    docs_check_report_from_payload,
    format_docs_check_markdown_report_from_report,
)


@dataclass(frozen=True)
class DocsCheckAnnotationCommand:
    expected_schema_version: str
    error_level: str
    warning_level: str
    preflight_title_template: str
    failed_check_title_template: str
    skipped_check_title_template: str
    skipped_check_message_template: str


@dataclass(frozen=True)
class DocsCheckCommentCommand:
    expected_schema_version: str
    comment_marker: str
    title: str
    passed_summary_template: str
    failed_summary_template: str
    preflight_failed_summary_template: str
    failed_check_heading_template: str
    skipped_checks_heading: str
    preflight_heading: str
    failed_checks_heading: str


DOCS_CHECK_ANNOTATION_COMMAND = DocsCheckAnnotationCommand(
    expected_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
    error_level="error",
    warning_level="warning",
    preflight_title_template="Docs check preflight",
    failed_check_title_template="Docs check [{check_id}]: {check_label}",
    skipped_check_title_template="Docs check skipped [{check_id}]: {check_label}",
    skipped_check_message_template=(
        "{check_label} did not run because docs check failed before execution."
    ),
)

DOCS_CHECK_COMMENT_COMMAND = DocsCheckCommentCommand(
    expected_schema_version=DOCS_CHECK_COMMAND.report_schema_version,
    comment_marker="<!-- docs-check-report-comment -->",
    title="## Docs Check",
    passed_summary_template=(
        "Docs check passed for {markdown_count} Markdown files and "
        "{github_metadata_count} GitHub metadata files."
    ),
    failed_summary_template=(
        "Docs check failed in {failed_check_count} of {check_count} checks."
    ),
    preflight_failed_summary_template=(
        "Docs check failed before execution with {preflight_error_count} "
        "preflight findings."
    ),
    failed_check_heading_template="#### `{check_id}` · {check_label}",
    skipped_checks_heading="### Skipped Checks",
    preflight_heading="### Preflight Findings",
    failed_checks_heading="### Failed Checks",
)


def validate_docs_check_annotation_command(
    command: DocsCheckAnnotationCommand = DOCS_CHECK_ANNOTATION_COMMAND,
) -> list[str]:
    errors: list[str] = []
    if not command.expected_schema_version:
        errors.append("docs check annotation command: empty expected schema version")
    if not command.error_level:
        errors.append("docs check annotation command: empty error level")
    if not command.warning_level:
        errors.append("docs check annotation command: empty warning level")
    if "{check_label}" not in command.failed_check_title_template:
        errors.append(
            "docs check annotation command: failed check title template missing "
            "'{check_label}' placeholder"
        )
    if "{check_id}" not in command.failed_check_title_template:
        errors.append(
            "docs check annotation command: failed check title template missing "
            "'{check_id}' placeholder"
        )
    if "{check_label}" not in command.skipped_check_title_template:
        errors.append(
            "docs check annotation command: skipped check title template missing "
            "'{check_label}' placeholder"
        )
    if "{check_id}" not in command.skipped_check_title_template:
        errors.append(
            "docs check annotation command: skipped check title template missing "
            "'{check_id}' placeholder"
        )
    if "{check_label}" not in command.skipped_check_message_template:
        errors.append(
            "docs check annotation command: skipped check message template missing "
            "'{check_label}' placeholder"
        )
    return errors


def validate_docs_check_comment_command(
    command: DocsCheckCommentCommand = DOCS_CHECK_COMMENT_COMMAND,
) -> list[str]:
    errors: list[str] = []
    if not command.expected_schema_version:
        errors.append("docs check comment command: empty expected schema version")
    if not command.comment_marker:
        errors.append("docs check comment command: empty comment marker")
    if not command.title:
        errors.append("docs check comment command: empty title")
    if "{markdown_count}" not in command.passed_summary_template:
        errors.append(
            "docs check comment command: passed summary template missing "
            "'{markdown_count}' placeholder"
        )
    if "{github_metadata_count}" not in command.passed_summary_template:
        errors.append(
            "docs check comment command: passed summary template missing "
            "'{github_metadata_count}' placeholder"
        )
    if "{failed_check_count}" not in command.failed_summary_template:
        errors.append(
            "docs check comment command: failed summary template missing "
            "'{failed_check_count}' placeholder"
        )
    if "{check_count}" not in command.failed_summary_template:
        errors.append(
            "docs check comment command: failed summary template missing "
            "'{check_count}' placeholder"
        )
    if "{preflight_error_count}" not in command.preflight_failed_summary_template:
        errors.append(
            "docs check comment command: preflight summary template missing "
            "'{preflight_error_count}' placeholder"
        )
    if "{check_id}" not in command.failed_check_heading_template:
        errors.append(
            "docs check comment command: failed check heading template missing "
            "'{check_id}' placeholder"
        )
    if "{check_label}" not in command.failed_check_heading_template:
        errors.append(
            "docs check comment command: failed check heading template missing "
            "'{check_label}' placeholder"
        )
    if not command.preflight_heading:
        errors.append("docs check comment command: empty preflight heading")
    if not command.failed_checks_heading:
        errors.append("docs check comment command: empty failed checks heading")
    if not command.skipped_checks_heading:
        errors.append("docs check comment command: empty skipped checks heading")
    return errors


def _escape_annotation_message(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_annotation_property(value: str) -> str:
    return _escape_annotation_message(value).replace(":", "%3A").replace(",", "%2C")


def format_github_annotation(
    level: str,
    *,
    title: str,
    message: str,
    path: str | None = None,
    line: int | None = None,
    end_line: int | None = None,
) -> str:
    properties = [f"title={_escape_annotation_property(title)}"]
    if path:
        properties.append(f"file={_escape_annotation_property(path)}")
    if line is not None:
        properties.append(f"line={line}")
        if end_line is not None and end_line != line:
            properties.append(f"endLine={end_line}")
    return f"::{level} {','.join(properties)}::{_escape_annotation_message(message)}"


def _annotation_level_for_finding(
    finding: DocsCheckFinding,
    command: DocsCheckAnnotationCommand,
) -> str:
    if finding.severity == command.warning_level:
        return command.warning_level
    return command.error_level


def _format_finding_location(finding: DocsCheckFinding) -> str | None:
    if finding.path is None:
        return None
    if finding.line is None:
        return finding.path
    if finding.end_line is not None and finding.end_line != finding.line:
        return f"{finding.path}:{finding.line}-{finding.end_line}"
    return f"{finding.path}:{finding.line}"


def _format_comment_finding(finding: DocsCheckFinding) -> str:
    location = _format_finding_location(finding)
    if location is None:
        return f"- {finding.message}"
    return f"- `{location}` {finding.message}"


def format_docs_check_github_annotations(
    report: DocsCheckReport,
    command: DocsCheckAnnotationCommand = DOCS_CHECK_ANNOTATION_COMMAND,
) -> tuple[str, ...]:
    lines: list[str] = []
    for finding in report.preflight_findings:
        lines.append(
            format_github_annotation(
                _annotation_level_for_finding(finding, command),
                title=command.preflight_title_template,
                message=finding.message,
                path=finding.path,
                line=finding.line,
                end_line=finding.end_line,
            )
        )

    for check in report.checks:
        if check.status == DOCS_CHECK_COMMAND.failed_status:
            lines.extend(
                format_github_annotation(
                    _annotation_level_for_finding(finding, command),
                    title=command.failed_check_title_template.format(
                        check_label=check.report_label,
                        check_id=check.check_id,
                    ),
                    message=finding.message,
                    path=finding.path,
                    line=finding.line,
                    end_line=finding.end_line,
                )
                for finding in check.findings
            )
        elif check.status == DOCS_CHECK_COMMAND.not_run_status:
            lines.append(
                format_github_annotation(
                    command.warning_level,
                    title=command.skipped_check_title_template.format(
                        check_label=check.report_label,
                        check_id=check.check_id,
                    ),
                    message=command.skipped_check_message_template.format(
                        check_label=check.report_label
                    ),
                )
            )
    return tuple(lines)


def format_docs_check_pr_comment(
    report: DocsCheckReport,
    command: DocsCheckCommentCommand = DOCS_CHECK_COMMENT_COMMAND,
) -> str:
    lines = [
        command.comment_marker,
        command.title,
        "",
        f"- Status: `{report.status}`",
        f"- Root: `{report.root}`",
        f"- Checks: {report.check_count}",
        f"- Failed checks: {report.failed_check_count}",
    ]
    if report.status == DOCS_CHECK_COMMAND.passed_status:
        lines.append(
            "- "
            + command.passed_summary_template.format(
                markdown_count=report.markdown_count,
                github_metadata_count=report.github_metadata_count,
            )
        )
    elif report.status == DOCS_CHECK_COMMAND.preflight_failed_status:
        lines.append(
            "- "
            + command.preflight_failed_summary_template.format(
                preflight_error_count=len(report.preflight_findings),
            )
        )
    else:
        lines.append(
            "- "
            + command.failed_summary_template.format(
                failed_check_count=report.failed_check_count,
                check_count=report.check_count,
            )
        )
    lines.append("")

    if report.preflight_findings:
        lines.extend((command.preflight_heading, ""))
        lines.extend(
            _format_comment_finding(finding)
            for finding in report.preflight_findings
        )
        lines.append("")

    failed_checks = [check for check in report.checks if check.findings]
    if failed_checks:
        lines.extend((command.failed_checks_heading, ""))
        for check in failed_checks:
            lines.append(
                command.failed_check_heading_template.format(
                    check_id=check.check_id,
                    check_label=check.report_label,
                )
            )
            lines.append("")
            lines.extend(_format_comment_finding(finding) for finding in check.findings)
            lines.append("")

    skipped_checks = [
        check
        for check in report.checks
        if check.status == DOCS_CHECK_COMMAND.not_run_status
    ]
    if skipped_checks:
        lines.extend((command.skipped_checks_heading, ""))
        lines.extend(
            f"- `{check.check_id}` {check.report_label}"
            for check in skipped_checks
        )
        lines.append("")

    return "\n".join(lines).rstrip()


def load_docs_check_report(
    report_file: Path,
    command: DocsCheckAnnotationCommand = DOCS_CHECK_ANNOTATION_COMMAND,
) -> DocsCheckReport:
    payload = json.loads(report_file.read_text(encoding="utf-8"))
    return docs_check_report_from_payload(
        payload,
        expected_schema_version=command.expected_schema_version,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render docs-check JSON reports for CI or local inspection."
    )
    parser.add_argument(
        "report_file", type=Path, help="Path to docs-check-report.json."
    )
    parser.add_argument(
        "--format",
        choices=("github-annotations", "markdown", "pr-comment"),
        default="github-annotations",
        dest="output_format",
        help="Choose GitHub workflow commands or Markdown summary output.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write rendered output to a file instead of stdout.",
    )
    return parser


def main(
    *,
    report_file: Path,
    output_format: str = "github-annotations",
    output_file: Path | None = None,
    command: DocsCheckAnnotationCommand = DOCS_CHECK_ANNOTATION_COMMAND,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    command_errors = validate_docs_check_annotation_command(command)
    comment_errors = validate_docs_check_comment_command()
    if command_errors or comment_errors:
        for error in (*command_errors, *comment_errors):
            print(error, file=error_stream)
        return 1

    try:
        report = load_docs_check_report(report_file, command)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"docs report render failed: {exc}", file=error_stream)
        return 1

    if output_format == "markdown":
        rendered_output = format_docs_check_markdown_report_from_report(report)
    elif output_format == "pr-comment":
        rendered_output = format_docs_check_pr_comment(report)
    else:
        rendered_output = "\n".join(
            format_docs_check_github_annotations(report, command)
        )

    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            f"{rendered_output}\n" if rendered_output else "",
            encoding="utf-8",
        )
        return 0

    if rendered_output:
        print(rendered_output, file=output_stream)
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(
        report_file=args.report_file,
        output_format=args.output_format,
        output_file=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
