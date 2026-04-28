from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.check_policies import (
    DEFAULT_POLICY_CHECKS,
    POLICY_REPORT_SCHEMA_VERSION,
    PolicyCheck,
    PolicyCheckFailure,
    main,
    run_policy_checks,
)


class CheckPoliciesTests(unittest.TestCase):
    def test_default_policy_checks_have_stable_unique_names(self) -> None:
        names = [check.name for check in DEFAULT_POLICY_CHECKS]

        self.assertEqual(len(names), len(set(names)))
        self.assertIn("issue form policy", names)
        self.assertIn("routing label policy", names)
        self.assertIn("support contract", names)
        self.assertIn("saved reply contract", names)
        self.assertIn("release lifecycle contract schema", names)

    def test_run_policy_checks_reports_exception_with_contract_name(self) -> None:
        def fail() -> None:
            raise ValueError("broken contract")

        failures = run_policy_checks((PolicyCheck("example policy", fail),))

        self.assertEqual(
            failures,
            (
                PolicyCheckFailure(
                    name="example policy",
                    message="broken contract",
                ),
            ),
        )

    def test_run_policy_checks_reports_returned_errors_with_contract_name(self) -> None:
        def fail_with_errors() -> tuple[str, ...]:
            return ("missing field", "")

        failures = run_policy_checks(
            (PolicyCheck("schema policy", fail_with_errors),)
        )

        self.assertEqual(
            failures,
            (
                PolicyCheckFailure(name="schema policy", message="missing field"),
                PolicyCheckFailure(
                    name="schema policy",
                    message="unknown policy validation error",
                ),
            ),
        )

    def test_main_prints_success_summary(self) -> None:
        def pass_check() -> None:
            return None

        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main((PolicyCheck("passing policy", pass_check),))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Policy checks passed for 1 contracts.", stdout.getvalue())

    def test_main_reports_failure_names_to_stderr(self) -> None:
        def fail() -> tuple[str, ...]:
            return ("bad field",)

        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main((PolicyCheck("failing policy", fail),))

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Policy checks failed:", stderr.getvalue())
        self.assertIn("- failing policy: bad field", stderr.getvalue())

    def test_main_writes_success_json_to_stdout(self) -> None:
        def pass_check() -> None:
            return None

        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                (PolicyCheck("passing policy", pass_check),),
                argv=("--format", "json"),
            )

        report = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(report["schema_version"], POLICY_REPORT_SCHEMA_VERSION)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["errors"], [])
        self.assertEqual(
            report["contracts"],
            [
                {
                    "name": "passing policy",
                    "status": "passed",
                    "errors": [],
                },
            ],
        )

    def test_main_writes_failure_json_to_stderr(self) -> None:
        def fail() -> tuple[str, ...]:
            return ("bad field",)

        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                (PolicyCheck("failing policy", fail),),
                argv=("--format", "json"),
            )

        report = json.loads(stderr.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(report["schema_version"], POLICY_REPORT_SCHEMA_VERSION)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(
            report["errors"],
            [{"contract": "failing policy", "message": "bad field"}],
        )
        self.assertEqual(
            report["contracts"],
            [
                {
                    "name": "failing policy",
                    "status": "failed",
                    "errors": ["bad field"],
                },
            ],
        )

    def test_main_writes_json_report_file(self) -> None:
        def fail() -> tuple[str, ...]:
            return ("bad field",)

        stdout = io.StringIO()
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "reports" / "policy-check-report.json"
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    (PolicyCheck("failing policy", fail),),
                    argv=("--json-report-file", str(report_path)),
                )

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("- failing policy: bad field", stderr.getvalue())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(
            report["errors"],
            [{"contract": "failing policy", "message": "bad field"}],
        )


if __name__ == "__main__":
    unittest.main()
