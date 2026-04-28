from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.docs_contracts import validate_docs_contract_schema
from tools.docs_findings import DocsCheckFinding, infer_repository_path
from tools.docs_links import (
    check_markdown_links,
    check_repository_references,
)
from tools.docs_parser import (
    iter_github_metadata_files,
    iter_markdown_files,
)
from tools.docs_registry_checks import check_maintainer_doc_registry
from tools.lifecycle_checks import (
    check_issue_close_out_contract,
    check_issue_linkage_contract,
    check_issue_summary_semantics_contract,
    check_maintainer_issue_contract,
    check_release_lifecycle_contract,
)
from tools.lifecycle_contracts import validate_lifecycle_contract_schema


@dataclass(frozen=True)
class DocsCheckContext:
    root: Path
    markdown_files: tuple[Path, ...]
    github_metadata_files: tuple[Path, ...]


DocsCheckRunner = Callable[[DocsCheckContext], Sequence[str | DocsCheckFinding]]
CHECK_ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def build_default_check_id(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return normalized


def normalize_check_id(check_id: str | None, name: str) -> str:
    candidate = (check_id or "").strip() or build_default_check_id(name)
    return candidate


@dataclass(frozen=True)
class DocsCheck:
    name: str
    report_label: str
    runner: DocsCheckRunner
    check_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "check_id",
            normalize_check_id(self.check_id, self.name),
        )


@dataclass(frozen=True)
class DocsCheckPipeline:
    checks: tuple[DocsCheck, ...]
    success_message_template: str


@dataclass(frozen=True)
class DocsCheckCommand:
    root: Path
    pipeline: DocsCheckPipeline
    success_exit_code: int
    failure_exit_code: int
    report_schema_version: str
    passed_status: str
    failed_status: str
    preflight_failed_status: str
    not_run_status: str
    preflight_failure_summary_template: str
    failure_summary_template: str
    failure_detail_template: str


@dataclass(frozen=True)
class DocsCheckRun:
    name: str
    report_label: str
    findings: tuple[DocsCheckFinding, ...]
    check_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "check_id",
            normalize_check_id(self.check_id, self.name),
        )

    @property
    def has_errors(self) -> bool:
        return bool(self.findings)

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(finding.message for finding in self.findings)


@dataclass(frozen=True)
class DocsCheckPipelineResult:
    context: DocsCheckContext
    check_runs: tuple[DocsCheckRun, ...]

    @property
    def failed_runs(self) -> tuple[DocsCheckRun, ...]:
        return tuple(run for run in self.check_runs if run.has_errors)


@dataclass(frozen=True)
class DocsCheckReportCheck:
    name: str
    report_label: str
    status: str
    findings: tuple[DocsCheckFinding, ...]
    check_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "check_id",
            normalize_check_id(self.check_id, self.name),
        )

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(finding.message for finding in self.findings)


@dataclass(frozen=True)
class DocsCheckReport:
    schema_version: str
    status: str
    exit_code: int
    root: str
    markdown_count: int
    github_metadata_count: int
    check_count: int
    failed_check_count: int
    preflight_findings: tuple[DocsCheckFinding, ...]
    checks: tuple[DocsCheckReportCheck, ...]

    @property
    def preflight_errors(self) -> tuple[str, ...]:
        return tuple(finding.message for finding in self.preflight_findings)


@dataclass(frozen=True)
class DocsCheckResult:
    exit_code: int
    report: DocsCheckReport
    stdout_lines: tuple[str, ...]
    stderr_lines: tuple[str, ...]


LEGACY_LOCATED_ERROR_RE = re.compile(
    r"^(?P<path>[^:\n]+):(?P<line>\d+)(?:-(?P<end_line>\d+))?: (?P<message>.+)$"
)
LEGACY_PATH_ERROR_RE = re.compile(r"^(?P<path>[^:\n]+\.\w+): (?P<message>.+)$")


def docs_check_finding_from_legacy_error(
    value: str | DocsCheckFinding,
) -> DocsCheckFinding:
    if isinstance(value, DocsCheckFinding):
        return value

    located_match = LEGACY_LOCATED_ERROR_RE.match(value)
    if located_match is not None:
        return DocsCheckFinding(
            message=located_match.group("message"),
            path=located_match.group("path"),
            line=int(located_match.group("line")),
            end_line=(
                int(located_match.group("end_line"))
                if located_match.group("end_line") is not None
                else None
            ),
        )

    path_match = LEGACY_PATH_ERROR_RE.match(value)
    if path_match is not None:
        return DocsCheckFinding(
            message=path_match.group("message"),
            path=path_match.group("path"),
        )

    repository_path = infer_repository_path(value)
    if repository_path is not None:
        return DocsCheckFinding(
            message=value,
            path=repository_path,
        )

    return DocsCheckFinding(message=value)


def _run_docs_contract_schema_check(
    _: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return validate_docs_contract_schema()


def _run_lifecycle_contract_schema_check(
    _: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return validate_lifecycle_contract_schema()


def _run_markdown_links_check(
    context: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return check_markdown_links(context.root, list(context.markdown_files))


def _run_repository_references_check(
    context: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return check_repository_references(
        context.root,
        list(context.github_metadata_files),
    )


def _run_maintainer_doc_registry_check(
    context: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return check_maintainer_doc_registry(context.root)


def _run_release_lifecycle_contract_check(
    context: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return check_release_lifecycle_contract(context.root)


def _run_maintainer_issue_contract_check(
    context: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return check_maintainer_issue_contract(context.root)


def _run_issue_linkage_contract_check(
    context: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return check_issue_linkage_contract(context.root)


def _run_issue_close_out_contract_check(
    context: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return check_issue_close_out_contract(context.root)


def _run_issue_summary_semantics_contract_check(
    context: DocsCheckContext,
) -> Sequence[str | DocsCheckFinding]:
    return check_issue_summary_semantics_contract(context.root)


DOCS_CHECK_PIPELINE = DocsCheckPipeline(
    checks=(
        DocsCheck(
            name="docs contract schema",
            report_label="Docs contract schema",
            runner=_run_docs_contract_schema_check,
            check_id="docs_contract_schema",
        ),
        DocsCheck(
            name="lifecycle contract schema",
            report_label="Lifecycle contract schema",
            runner=_run_lifecycle_contract_schema_check,
            check_id="lifecycle_contract_schema",
        ),
        DocsCheck(
            name="markdown links",
            report_label="Markdown links",
            runner=_run_markdown_links_check,
            check_id="markdown_links",
        ),
        DocsCheck(
            name="repository references",
            report_label="Repository references",
            runner=_run_repository_references_check,
            check_id="repository_references",
        ),
        DocsCheck(
            name="maintainer doc registry",
            report_label="Maintainer doc registry",
            runner=_run_maintainer_doc_registry_check,
            check_id="maintainer_doc_registry",
        ),
        DocsCheck(
            name="release lifecycle contract",
            report_label="Release lifecycle contract",
            runner=_run_release_lifecycle_contract_check,
            check_id="release_lifecycle_contract",
        ),
        DocsCheck(
            name="maintainer issue contract",
            report_label="Maintainer issue contract",
            runner=_run_maintainer_issue_contract_check,
            check_id="maintainer_issue_contract",
        ),
        DocsCheck(
            name="issue linkage contract",
            report_label="Issue linkage contract",
            runner=_run_issue_linkage_contract_check,
            check_id="issue_linkage_contract",
        ),
        DocsCheck(
            name="issue close-out contract",
            report_label="Issue close-out contract",
            runner=_run_issue_close_out_contract_check,
            check_id="issue_close_out_contract",
        ),
        DocsCheck(
            name="issue summary semantics contract",
            report_label="Issue summary semantics contract",
            runner=_run_issue_summary_semantics_contract_check,
            check_id="issue_summary_semantics_contract",
        ),
    ),
    success_message_template=(
        "Docs check passed for "
        "{markdown_count} Markdown files and "
        "{github_metadata_count} GitHub metadata files."
    ),
)


DOCS_CHECK_COMMAND = DocsCheckCommand(
    root=Path(__file__).resolve().parents[1],
    pipeline=DOCS_CHECK_PIPELINE,
    success_exit_code=0,
    failure_exit_code=1,
    report_schema_version="4",
    passed_status="passed",
    failed_status="failed",
    preflight_failed_status="preflight_failed",
    not_run_status="not_run",
    preflight_failure_summary_template=(
        "Docs check failed before execution with {error_count} preflight errors."
    ),
    failure_summary_template=(
        "Docs check failed in {failed_check_count} of {check_count} checks."
    ),
    failure_detail_template="[{check_label}] {error}",
)


def build_docs_check_context(root: Path) -> DocsCheckContext:
    resolved_root = root.resolve()
    return DocsCheckContext(
        root=resolved_root,
        markdown_files=tuple(iter_markdown_files(resolved_root)),
        github_metadata_files=tuple(iter_github_metadata_files(resolved_root)),
    )


def validate_docs_check_pipeline(
    pipeline: DocsCheckPipeline = DOCS_CHECK_PIPELINE,
) -> list[str]:
    errors: list[str] = []
    if not pipeline.checks:
        errors.append("docs check pipeline: no checks configured")
    check_names = [check.name for check in pipeline.checks]
    if len(check_names) != len(set(check_names)):
        errors.append("docs check pipeline: duplicate check names")
    if any(not name for name in check_names):
        errors.append("docs check pipeline: empty check name")

    check_labels = [check.report_label for check in pipeline.checks]
    if len(check_labels) != len(set(check_labels)):
        errors.append("docs check pipeline: duplicate check report labels")
    if any(not label for label in check_labels):
        errors.append("docs check pipeline: empty check report label")

    check_ids = [
        normalize_check_id(check.check_id, check.name)
        for check in pipeline.checks
    ]
    if len(check_ids) != len(set(check_ids)):
        errors.append("docs check pipeline: duplicate check ids")
    if any(not check_id for check_id in check_ids):
        errors.append("docs check pipeline: empty check id")
    invalid_check_ids = [
        check_id for check_id in check_ids if CHECK_ID_RE.fullmatch(check_id) is None
    ]
    if invalid_check_ids:
        errors.append("docs check pipeline: invalid check id format")

    template = pipeline.success_message_template
    if "{markdown_count}" not in template:
        errors.append(
            "docs check pipeline: success message template missing "
            "'{markdown_count}' placeholder"
        )
    if "{github_metadata_count}" not in template:
        errors.append(
            "docs check pipeline: success message template missing "
            "'{github_metadata_count}' placeholder"
        )
    return errors


def validate_docs_check_command(
    command: DocsCheckCommand = DOCS_CHECK_COMMAND,
) -> list[str]:
    errors: list[str] = []
    if command.success_exit_code == command.failure_exit_code:
        errors.append("docs check command: success and failure exit codes must differ")
    if not command.report_schema_version:
        errors.append("docs check command: empty report schema version")

    status_values = [
        command.passed_status,
        command.failed_status,
        command.preflight_failed_status,
        command.not_run_status,
    ]
    if any(not status for status in status_values):
        errors.append("docs check command: empty report status value")
    if len(status_values) != len(set(status_values)):
        errors.append("docs check command: duplicate report status values")

    preflight_template = command.preflight_failure_summary_template
    if "{error_count}" not in preflight_template:
        errors.append(
            "docs check command: preflight failure summary template missing "
            "'{error_count}' placeholder"
        )

    failure_summary_template = command.failure_summary_template
    if "{failed_check_count}" not in failure_summary_template:
        errors.append(
            "docs check command: failure summary template missing "
            "'{failed_check_count}' placeholder"
        )
    if "{check_count}" not in failure_summary_template:
        errors.append(
            "docs check command: failure summary template missing "
            "'{check_count}' placeholder"
        )

    detail_template = command.failure_detail_template
    if "{check_label}" not in detail_template:
        errors.append(
            "docs check command: failure detail template missing "
            "'{check_label}' placeholder"
        )
    if "{error}" not in detail_template:
        errors.append(
            "docs check command: failure detail template missing '{error}' placeholder"
        )

    if not command.root.exists():
        errors.append(f"docs check command: root does not exist: {command.root}")
    elif not command.root.is_dir():
        errors.append(f"docs check command: root is not a directory: {command.root}")
    return errors


def run_docs_check_pipeline(
    context: DocsCheckContext,
    pipeline: DocsCheckPipeline = DOCS_CHECK_PIPELINE,
) -> DocsCheckPipelineResult:
    return DocsCheckPipelineResult(
        context=context,
        check_runs=tuple(
            DocsCheckRun(
                name=check.name,
                report_label=check.report_label,
                findings=tuple(
                    docs_check_finding_from_legacy_error(finding)
                    for finding in check.runner(context)
                ),
                check_id=check.check_id,
            )
            for check in pipeline.checks
        ),
    )


def format_docs_check_success_message(
    context: DocsCheckContext,
    pipeline: DocsCheckPipeline = DOCS_CHECK_PIPELINE,
) -> str:
    return pipeline.success_message_template.format(
        markdown_count=len(context.markdown_files),
        github_metadata_count=len(context.github_metadata_files),
    )


def format_docs_check_preflight_failure_summary(
    error_count: int,
    command: DocsCheckCommand = DOCS_CHECK_COMMAND,
) -> str:
    return command.preflight_failure_summary_template.format(
        error_count=error_count,
    )


def format_docs_check_failure_summary(
    result: DocsCheckPipelineResult,
    command: DocsCheckCommand = DOCS_CHECK_COMMAND,
) -> str:
    return command.failure_summary_template.format(
        failed_check_count=len(result.failed_runs),
        check_count=len(result.check_runs),
    )


def format_docs_check_failure_detail(
    check_label: str,
    error: str,
    command: DocsCheckCommand = DOCS_CHECK_COMMAND,
) -> str:
    return command.failure_detail_template.format(
        check_label=check_label,
        error=error,
    )


def _resolve_report_root(root: Path) -> str:
    return str(root.resolve()) if root.exists() else str(root)


def _build_runtime_report_checks(
    check_runs: tuple[DocsCheckRun, ...],
    command: DocsCheckCommand,
) -> tuple[DocsCheckReportCheck, ...]:
    return tuple(
        DocsCheckReportCheck(
            name=run.name,
            report_label=run.report_label,
            status=command.failed_status if run.has_errors else command.passed_status,
            findings=run.findings,
            check_id=run.check_id,
        )
        for run in check_runs
    )


def _build_not_run_report_checks(
    pipeline: DocsCheckPipeline,
    command: DocsCheckCommand,
) -> tuple[DocsCheckReportCheck, ...]:
    return tuple(
        DocsCheckReportCheck(
            name=check.name,
            report_label=check.report_label,
            status=command.not_run_status,
            findings=(),
            check_id=check.check_id,
        )
        for check in pipeline.checks
    )


def _build_docs_check_report(
    *,
    command: DocsCheckCommand,
    exit_code: int,
    status: str,
    context: DocsCheckContext | None,
    preflight_findings: tuple[DocsCheckFinding, ...] = (),
    checks: tuple[DocsCheckReportCheck, ...] = (),
) -> DocsCheckReport:
    markdown_count = 0 if context is None else len(context.markdown_files)
    github_metadata_count = 0 if context is None else len(context.github_metadata_files)
    failed_check_count = sum(
        1 for check in checks if check.status == command.failed_status
    )
    return DocsCheckReport(
        schema_version=command.report_schema_version,
        status=status,
        exit_code=exit_code,
        root=_resolve_report_root(command.root),
        markdown_count=markdown_count,
        github_metadata_count=github_metadata_count,
        check_count=len(checks),
        failed_check_count=failed_check_count,
        preflight_findings=preflight_findings,
        checks=checks,
    )


def docs_check_report_to_payload(report: DocsCheckReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "status": report.status,
        "exit_code": report.exit_code,
        "root": report.root,
        "counts": {
            "markdown_files": report.markdown_count,
            "github_metadata_files": report.github_metadata_count,
            "checks": report.check_count,
            "failed_checks": report.failed_check_count,
        },
        "preflight_errors": list(report.preflight_errors),
        "preflight_findings": [
            {
                "message": finding.message,
                "severity": finding.severity,
                "path": finding.path,
                "line": finding.line,
                "end_line": finding.end_line,
            }
            for finding in report.preflight_findings
        ],
        "checks": [
            {
                "name": check.name,
                "check_id": check.check_id,
                "report_label": check.report_label,
                "status": check.status,
                "error_count": len(check.errors),
                "errors": list(check.errors),
                "findings": [
                    {
                        "message": finding.message,
                        "severity": finding.severity,
                        "path": finding.path,
                        "line": finding.line,
                        "end_line": finding.end_line,
                    }
                    for finding in check.findings
                ],
            }
            for check in report.checks
        ],
    }


def _require_report_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"docs check report: {context} must be a mapping")
    return value


def _require_report_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"docs check report: {context} must be a non-empty string")
    return value


def _require_report_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"docs check report: {context} must be an integer")
    return int(value)


def _require_report_string_list(value: Any, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"docs check report: {context} must be a list")
    items = tuple(_require_report_string(item, f"{context} entry") for item in value)
    return items


def _require_report_optional_string(value: Any, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"docs check report: {context} must be null or a non-empty string"
        )
    return value


def _require_report_optional_int(value: Any, context: str) -> int | None:
    if value is None:
        return None
    return int(_require_report_int(value, context))


def _require_report_findings(
    value: Any,
    context: str,
) -> tuple[DocsCheckFinding, ...]:
    if not isinstance(value, list):
        raise ValueError(f"docs check report: {context} must be a list")
    findings: list[DocsCheckFinding] = []
    for index, finding_value in enumerate(value):
        finding = _require_report_mapping(finding_value, f"{context}[{index}]")
        findings.append(
            _validate_report_finding_lines(
                message=_require_report_string(
                    finding.get("message"),
                    f"{context}[{index}].message",
                ),
                severity=_require_report_string(
                    finding.get("severity"),
                    f"{context}[{index}].severity",
                ),
                path=_require_report_optional_string(
                    finding.get("path"),
                    f"{context}[{index}].path",
                ),
                line=_require_report_optional_int(
                    finding.get("line"),
                    f"{context}[{index}].line",
                ),
                end_line=_require_report_optional_int(
                    finding.get("end_line"),
                    f"{context}[{index}].end_line",
                ),
                context=f"{context}[{index}]",
            )
        )
    return tuple(findings)


def _validate_report_finding_lines(
    *,
    message: str,
    severity: str,
    path: str | None,
    line: int | None,
    end_line: int | None,
    context: str,
) -> DocsCheckFinding:
    if end_line is not None and line is None:
        raise ValueError(
            f"docs check report: {context}.end_line requires a start line"
        )
    if line is not None and end_line is not None and end_line < line:
        raise ValueError(
            f"docs check report: {context}.end_line must be >= {context}.line"
        )
    return DocsCheckFinding(
        message=message,
        severity=severity,
        path=path,
        line=line,
        end_line=end_line,
    )


def _require_report_check_id(
    value: Any,
    context: str,
) -> str:
    check_id = _require_report_string(value, context)
    if CHECK_ID_RE.fullmatch(check_id) is None:
        raise ValueError(
            f"docs check report: {context} must use snake_case check id format"
        )
    return check_id


def docs_check_report_from_payload(
    payload: Any,
    *,
    expected_schema_version: str = DOCS_CHECK_COMMAND.report_schema_version,
) -> DocsCheckReport:
    report_data = _require_report_mapping(payload, "payload")
    schema_version = _require_report_string(
        report_data.get("schema_version"),
        "schema_version",
    )
    if schema_version != expected_schema_version:
        raise ValueError(
            "docs check report: unsupported schema version: "
            f"{schema_version!r} != {expected_schema_version!r}"
        )

    counts = _require_report_mapping(report_data.get("counts"), "counts")
    markdown_count = _require_report_int(
        counts.get("markdown_files"),
        "counts.markdown_files",
    )
    github_metadata_count = _require_report_int(
        counts.get("github_metadata_files"),
        "counts.github_metadata_files",
    )
    check_count = _require_report_int(counts.get("checks"), "counts.checks")
    failed_check_count = _require_report_int(
        counts.get("failed_checks"),
        "counts.failed_checks",
    )
    preflight_errors = _require_report_string_list(
        report_data.get("preflight_errors"),
        "preflight_errors",
    )
    preflight_findings = _require_report_findings(
        report_data.get("preflight_findings"),
        "preflight_findings",
    )
    if preflight_errors != tuple(finding.message for finding in preflight_findings):
        raise ValueError(
            "docs check report: preflight_errors does not match preflight findings"
        )

    checks_value = report_data.get("checks")
    if not isinstance(checks_value, list):
        raise ValueError("docs check report: checks must be a list")

    checks: list[DocsCheckReportCheck] = []
    for index, check_value in enumerate(checks_value):
        check = _require_report_mapping(check_value, f"checks[{index}]")
        errors = _require_report_string_list(
            check.get("errors"), f"checks[{index}].errors"
        )
        findings = _require_report_findings(
            check.get("findings"),
            f"checks[{index}].findings",
        )
        error_count = _require_report_int(
            check.get("error_count"),
            f"checks[{index}].error_count",
        )
        if error_count != len(errors):
            raise ValueError(
                "docs check report: "
                f"checks[{index}].error_count does not match errors length"
            )
        if errors != tuple(finding.message for finding in findings):
            raise ValueError(
                "docs check report: "
                f"checks[{index}].errors does not match findings messages"
            )
        checks.append(
            DocsCheckReportCheck(
                name=_require_report_string(check.get("name"), f"checks[{index}].name"),
                check_id=_require_report_check_id(
                    check.get("check_id"),
                    f"checks[{index}].check_id",
                ),
                report_label=_require_report_string(
                    check.get("report_label"),
                    f"checks[{index}].report_label",
                ),
                status=_require_report_string(
                    check.get("status"),
                    f"checks[{index}].status",
                ),
                findings=findings,
            )
        )

    if check_count != len(checks):
        raise ValueError(
            "docs check report: counts.checks does not match checks length"
        )

    actual_failed_check_count = sum(
        1 for check in checks if check.status == DOCS_CHECK_COMMAND.failed_status
    )
    if failed_check_count != actual_failed_check_count:
        raise ValueError(
            "docs check report: counts.failed_checks does not match failed check count"
        )

    return DocsCheckReport(
        schema_version=schema_version,
        status=_require_report_string(report_data.get("status"), "status"),
        exit_code=_require_report_int(report_data.get("exit_code"), "exit_code"),
        root=_require_report_string(report_data.get("root"), "root"),
        markdown_count=markdown_count,
        github_metadata_count=github_metadata_count,
        check_count=check_count,
        failed_check_count=failed_check_count,
        preflight_findings=preflight_findings,
        checks=tuple(checks),
    )


def format_docs_check_json_report(result: DocsCheckResult) -> str:
    return json.dumps(docs_check_report_to_payload(result.report), indent=2)


def _escape_markdown_table_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _format_markdown_finding(finding: DocsCheckFinding) -> str:
    location = finding.path
    if finding.path is not None and finding.line is not None:
        if finding.end_line is not None and finding.end_line != finding.line:
            location = f"{finding.path}:{finding.line}-{finding.end_line}"
        else:
            location = f"{finding.path}:{finding.line}"
    if location:
        return f"- `{location}` {finding.message}"
    return f"- {finding.message}"


def format_docs_check_markdown_report_from_report(report: DocsCheckReport) -> str:
    lines = [
        "## Docs Check",
        "",
        f"- Status: `{report.status}`",
        f"- Exit code: `{report.exit_code}`",
        f"- Root: `{report.root}`",
        f"- Markdown files: {report.markdown_count}",
        f"- GitHub metadata files: {report.github_metadata_count}",
        f"- Checks: {report.check_count}",
        f"- Failed checks: {report.failed_check_count}",
        "",
    ]
    if report.preflight_findings:
        lines.extend(("### Preflight Errors", ""))
        lines.extend(
            _format_markdown_finding(finding) for finding in report.preflight_findings
        )
        lines.append("")

    lines.extend(
        (
            "### Checks",
            "",
            "| Check | Status | Errors |",
            "| --- | --- | --- |",
        )
    )
    lines.extend(
        (
            "| "
            f"{_escape_markdown_table_cell(check.report_label)} | "
            f"`{_escape_markdown_table_cell(check.status)}` | "
            f"{len(check.errors)} |"
        )
        for check in report.checks
    )

    failed_checks = [check for check in report.checks if check.findings]
    if failed_checks:
        lines.extend(("", "### Failed Check Details", ""))
        for check in failed_checks:
            lines.append(f"#### {check.report_label} (`{check.check_id}`)")
            lines.append("")
            lines.extend(
                _format_markdown_finding(finding) for finding in check.findings
            )
            lines.append("")

    return "\n".join(lines).rstrip()


def format_docs_check_markdown_report(result: DocsCheckResult) -> str:
    return format_docs_check_markdown_report_from_report(result.report)


def _format_preflight_failure_lines(
    command: DocsCheckCommand,
    command_errors: list[str],
    pipeline_errors: list[str],
) -> tuple[str, ...]:
    lines = [
        format_docs_check_preflight_failure_summary(
            len(command_errors) + len(pipeline_errors),
            command,
        )
    ]
    lines.extend(
        format_docs_check_failure_detail("Command config", error, command)
        for error in command_errors
    )
    lines.extend(
        format_docs_check_failure_detail("Pipeline config", error, command)
        for error in pipeline_errors
    )
    return tuple(lines)


def _format_pipeline_failure_lines(
    result: DocsCheckPipelineResult,
    command: DocsCheckCommand,
) -> tuple[str, ...]:
    lines = [format_docs_check_failure_summary(result, command)]
    for run in result.failed_runs:
        lines.extend(
            format_docs_check_failure_detail(run.report_label, error, command)
            for error in run.errors
        )
    return tuple(lines)


def run_docs_check_command(
    command: DocsCheckCommand = DOCS_CHECK_COMMAND,
) -> DocsCheckResult:
    command_errors = validate_docs_check_command(command)
    pipeline_errors = validate_docs_check_pipeline(command.pipeline)
    preflight_context = None
    if command.root.exists() and command.root.is_dir():
        preflight_context = build_docs_check_context(command.root)
    if command_errors or pipeline_errors:
        preflight_findings = tuple(
            docs_check_finding_from_legacy_error(error)
            for error in (*command_errors, *pipeline_errors)
        )
        return DocsCheckResult(
            exit_code=command.failure_exit_code,
            report=_build_docs_check_report(
                command=command,
                exit_code=command.failure_exit_code,
                status=command.preflight_failed_status,
                context=preflight_context,
                preflight_findings=preflight_findings,
                checks=_build_not_run_report_checks(command.pipeline, command),
            ),
            stdout_lines=(),
            stderr_lines=_format_preflight_failure_lines(
                command,
                command_errors,
                pipeline_errors,
            ),
        )

    context = build_docs_check_context(command.root)
    pipeline_result = run_docs_check_pipeline(context, command.pipeline)
    if pipeline_result.failed_runs:
        return DocsCheckResult(
            exit_code=command.failure_exit_code,
            report=_build_docs_check_report(
                command=command,
                exit_code=command.failure_exit_code,
                status=command.failed_status,
                context=context,
                checks=_build_runtime_report_checks(
                    pipeline_result.check_runs,
                    command,
                ),
            ),
            stdout_lines=(),
            stderr_lines=_format_pipeline_failure_lines(pipeline_result, command),
        )
    return DocsCheckResult(
        exit_code=command.success_exit_code,
        report=_build_docs_check_report(
            command=command,
            exit_code=command.success_exit_code,
            status=command.passed_status,
            context=context,
            checks=_build_runtime_report_checks(
                pipeline_result.check_runs,
                command,
            ),
        ),
        stdout_lines=(format_docs_check_success_message(context, command.pipeline),),
        stderr_lines=(),
    )
