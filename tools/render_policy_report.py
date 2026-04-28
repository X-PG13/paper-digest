from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from tools.check_policies import POLICY_REPORT_SCHEMA_VERSION
from tools.render_docs_report import format_github_annotation


@dataclass(frozen=True)
class PolicyContractReport:
    name: str
    status: str
    errors: tuple[str, ...]


@dataclass(frozen=True)
class PolicyReportError:
    contract: str
    message: str


@dataclass(frozen=True)
class PolicyReport:
    schema_version: int
    status: str
    contracts: tuple[PolicyContractReport, ...]
    errors: tuple[PolicyReportError, ...]


def policy_report_from_payload(payload: object) -> PolicyReport:
    if not isinstance(payload, dict):
        raise ValueError("policy report payload must be an object")

    schema_version = payload.get("schema_version")
    if schema_version != POLICY_REPORT_SCHEMA_VERSION:
        raise ValueError(f"unsupported policy report schema version: {schema_version}")

    status = payload.get("status")
    if status not in ("passed", "failed"):
        raise ValueError("policy report status must be 'passed' or 'failed'")

    contracts_payload = payload.get("contracts")
    if not isinstance(contracts_payload, list):
        raise ValueError("policy report contracts must be a list")

    contracts: list[PolicyContractReport] = []
    for index, contract_payload in enumerate(contracts_payload):
        if not isinstance(contract_payload, dict):
            raise ValueError(f"policy report contract #{index} must be an object")
        name = contract_payload.get("name")
        contract_status = contract_payload.get("status")
        errors_payload = contract_payload.get("errors")
        if not isinstance(name, str) or not name:
            raise ValueError(f"policy report contract #{index} has invalid name")
        if contract_status not in ("passed", "failed"):
            raise ValueError(
                f"policy report contract '{name}' has invalid status"
            )
        if not isinstance(errors_payload, list) or any(
            not isinstance(error, str) for error in errors_payload
        ):
            raise ValueError(
                f"policy report contract '{name}' has invalid errors"
            )
        contracts.append(
            PolicyContractReport(
                name=name,
                status=contract_status,
                errors=tuple(errors_payload),
            )
        )

    errors_payload = payload.get("errors")
    if not isinstance(errors_payload, list):
        raise ValueError("policy report errors must be a list")

    errors: list[PolicyReportError] = []
    for index, error_payload in enumerate(errors_payload):
        if not isinstance(error_payload, dict):
            raise ValueError(f"policy report error #{index} must be an object")
        contract = error_payload.get("contract")
        message = error_payload.get("message")
        if not isinstance(contract, str) or not contract:
            raise ValueError(f"policy report error #{index} has invalid contract")
        if not isinstance(message, str) or not message:
            raise ValueError(f"policy report error #{index} has invalid message")
        errors.append(PolicyReportError(contract=contract, message=message))

    expected_errors = [
        PolicyReportError(contract=contract.name, message=error)
        for contract in contracts
        for error in contract.errors
    ]
    if errors != expected_errors:
        raise ValueError("policy report errors do not match contract errors")
    if (status == "failed") != bool(errors):
        raise ValueError("policy report status does not match errors")

    return PolicyReport(
        schema_version=schema_version,
        status=status,
        contracts=tuple(contracts),
        errors=tuple(errors),
    )


def load_policy_report(report_file: Path) -> PolicyReport:
    return policy_report_from_payload(
        json.loads(report_file.read_text(encoding="utf-8"))
    )


def format_policy_markdown_report(report: PolicyReport) -> str:
    failed_contracts = [
        contract for contract in report.contracts if contract.status == "failed"
    ]
    lines = [
        "## Policy Check",
        "",
        f"- Status: `{report.status}`",
        f"- Contracts: {len(report.contracts)}",
        f"- Failed contracts: {len(failed_contracts)}",
        f"- Errors: {len(report.errors)}",
        "",
        "| Contract | Status | Errors |",
        "| --- | --- | ---: |",
    ]
    lines.extend(
        f"| {contract.name} | `{contract.status}` | {len(contract.errors)} |"
        for contract in report.contracts
    )

    if failed_contracts:
        lines.extend(("", "### Failed Contracts", ""))
        for contract in failed_contracts:
            lines.extend((f"#### {contract.name}", ""))
            lines.extend(f"- {error}" for error in contract.errors)
            lines.append("")

    return "\n".join(lines).rstrip()


def format_policy_github_annotations(report: PolicyReport) -> tuple[str, ...]:
    return tuple(
        format_github_annotation(
            "error",
            title=f"Policy check: {error.contract}",
            message=error.message,
        )
        for error in report.errors
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render policy-check JSON reports for CI or local inspection."
    )
    parser.add_argument(
        "report_file",
        type=Path,
        help="Path to policy-check-report.json.",
    )
    parser.add_argument(
        "--format",
        choices=("github-annotations", "markdown"),
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
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr

    try:
        report = load_policy_report(report_file)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"policy report render failed: {exc}", file=error_stream)
        return 1

    rendered_output = (
        format_policy_markdown_report(report)
        if output_format == "markdown"
        else "\n".join(format_policy_github_annotations(report))
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
