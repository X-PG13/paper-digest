from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.contributor_release_label_policy import (
    validate_contributor_release_label_policy,
)
from tools.docs_contracts import validate_docs_contract_schema
from tools.issue_form_policy import validate_issue_form_policy
from tools.issue_intake_policy import validate_issue_intake_contract
from tools.label_behavior_policy import validate_label_behavior_policy
from tools.label_registry import validate_label_registry
from tools.lifecycle_contracts import validate_lifecycle_contract_schema
from tools.pr_policy import validate_pr_hygiene_contract
from tools.repository_settings_policy import validate_repository_settings_policy
from tools.routing_label_policy import validate_routing_label_policy
from tools.saved_reply_policy import validate_saved_reply_contract
from tools.status_label_policy import validate_status_label_policy
from tools.support_policy import validate_support_contract
from tools.triage_policy import validate_triage_reply_policy

PolicyValidator = Callable[[], Sequence[str] | None]
POLICY_REPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PolicyCheck:
    name: str
    validator: PolicyValidator


@dataclass(frozen=True)
class PolicyCheckFailure:
    name: str
    message: str


@dataclass(frozen=True)
class PolicyCheckResult:
    name: str
    errors: tuple[str, ...]

    @property
    def status(self) -> str:
        if self.errors:
            return "failed"
        return "passed"


DEFAULT_POLICY_CHECKS = (
    PolicyCheck("label registry", validate_label_registry),
    PolicyCheck("issue form policy", validate_issue_form_policy),
    PolicyCheck("issue intake contract", validate_issue_intake_contract),
    PolicyCheck("support contract", validate_support_contract),
    PolicyCheck("saved reply contract", validate_saved_reply_contract),
    PolicyCheck("triage reply policy", validate_triage_reply_policy),
    PolicyCheck("PR hygiene contract", validate_pr_hygiene_contract),
    PolicyCheck("repository settings policy", validate_repository_settings_policy),
    PolicyCheck("routing label policy", validate_routing_label_policy),
    PolicyCheck("label behavior policy", validate_label_behavior_policy),
    PolicyCheck(
        "contributor/release label policy",
        validate_contributor_release_label_policy,
    ),
    PolicyCheck("status label policy", validate_status_label_policy),
    PolicyCheck("docs contract schema", validate_docs_contract_schema),
    PolicyCheck(
        "release lifecycle contract schema",
        validate_lifecycle_contract_schema,
    ),
)


def run_policy_check_results(
    checks: Sequence[PolicyCheck] = DEFAULT_POLICY_CHECKS,
) -> tuple[PolicyCheckResult, ...]:
    results: list[PolicyCheckResult] = []
    for check in checks:
        try:
            errors = check.validator()
        except Exception as exc:
            results.append(
                PolicyCheckResult(
                    name=check.name,
                    errors=(str(exc) or exc.__class__.__name__,),
                )
            )
            continue
        if errors is None:
            results.append(PolicyCheckResult(name=check.name, errors=()))
            continue
        results.append(
            PolicyCheckResult(
                name=check.name,
                errors=tuple(
                    error or "unknown policy validation error"
                    for error in errors
                ),
            )
        )
    return tuple(results)


def run_policy_checks(
    checks: Sequence[PolicyCheck] = DEFAULT_POLICY_CHECKS,
) -> tuple[PolicyCheckFailure, ...]:
    return tuple(
        PolicyCheckFailure(name=result.name, message=error)
        for result in run_policy_check_results(checks)
        for error in result.errors
    )


def build_policy_report(
    results: Sequence[PolicyCheckResult],
) -> dict[str, object]:
    errors = [
        {
            "contract": result.name,
            "message": error,
        }
        for result in results
        for error in result.errors
    ]
    return {
        "schema_version": POLICY_REPORT_SCHEMA_VERSION,
        "status": "failed" if errors else "passed",
        "contracts": [
            {
                "name": result.name,
                "status": result.status,
                "errors": list(result.errors),
            }
            for result in results
        ],
        "errors": errors,
    }


def render_text_report(results: Sequence[PolicyCheckResult]) -> str:
    failures = [
        PolicyCheckFailure(name=result.name, message=error)
        for result in results
        for error in result.errors
    ]
    if failures:
        lines = ["Policy checks failed:"]
        lines.extend(
            f"- {failure.name}: {failure.message}"
            for failure in failures
        )
        return "\n".join(lines)

    return f"Policy checks passed for {len(results)} contracts."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate repo-local policy contract schemas.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    parser.add_argument(
        "--json-report-file",
        help="Write the policy-check JSON report to this path.",
    )
    return parser


def write_json_report_file(path: str, report: dict[str, object]) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(
    checks: Sequence[PolicyCheck] = DEFAULT_POLICY_CHECKS,
    argv: Sequence[str] | None = (),
) -> int:
    args = build_parser().parse_args(argv)
    results = run_policy_check_results(checks)
    report = build_policy_report(results)
    if args.json_report_file:
        write_json_report_file(args.json_report_file, report)

    output = (
        json.dumps(report, indent=2, sort_keys=True)
        if args.format == "json"
        else render_text_report(results)
    )
    if report["status"] == "failed":
        print(output, file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv=None))
