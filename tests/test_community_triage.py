from __future__ import annotations

import unittest
from io import StringIO

from tools.community_triage import (
    COMMUNITY_TRIAGE_MARKER,
    ISSUE_INTAKE_COMMENT_HEADER,
    evaluate_issue_intake,
    extract_section,
    main,
    parse_label_names,
    section_has_content,
)
from tools.issue_intake_policy import (
    BUG_LABEL,
    ISSUE_INTAKE_FIELDS,
    ISSUE_INTAKE_SECTIONS,
    NEEDS_INFO_LABEL,
)
from tools.support_policy import (
    SUPPORT_PRECHECK_DOCS,
    SUPPORT_PRECHECK_MISSING_MESSAGE,
    SUPPORT_REQUEST_CHECKLIST_LABEL,
    SUPPORT_REQUEST_FIELDS,
    SUPPORT_TRIAGE_COMMENT_HEADER,
    SUPPORT_TRIAGE_MARKER,
)


class CommunityTriageTests(unittest.TestCase):
    def test_extract_section_and_section_has_content_cover_placeholders(self) -> None:
        body = "## Reproduction\n1. Configuration used:\nreal step\n\n## Other\nx"
        self.assertEqual(
            extract_section(body, "Reproduction"),
            "1. Configuration used:\nreal step",
        )
        self.assertTrue(section_has_content("real", [r"^placeholder$"]))
        self.assertFalse(section_has_content("_No response_", [r"^_No response_$"]))

    def test_parse_label_names_accepts_strings_and_objects(self) -> None:
        self.assertEqual(
            parse_label_names('["bug", {"name": "needs-info"}, {"other": 1}]'),
            ("bug", "needs-info"),
        )
        with self.assertRaisesRegex(ValueError, "JSON list"):
            parse_label_names('{"bug": true}')

    def test_evaluate_issue_intake_for_non_bug_and_completed_bug(self) -> None:
        non_bug = evaluate_issue_intake("body", ["documentation"])
        self.assertEqual(non_bug.mode, "delete")
        self.assertEqual(non_bug.needs_info_action, "none")

        reproduction = ISSUE_INTAKE_SECTIONS[0]
        minimal_config = ISSUE_INTAKE_SECTIONS[1]
        expected_behavior = ISSUE_INTAKE_SECTIONS[2]
        os_field = ISSUE_INTAKE_FIELDS[0]
        python_field = ISSUE_INTAKE_FIELDS[1]
        project_field = ISSUE_INTAKE_FIELDS[2]
        complete_body = (
            f"## {reproduction.label}\n1. Use config\n2. Run command\n3. It fails\n\n"
            f"## {minimal_config.label}\nreal config\n\n"
            f"## {expected_behavior.label}\nit should work\n\n"
            f"- {os_field.label}: macOS\n"
            f"- {python_field.label}: 3.12\n"
            f"- {project_field.label}: main\n"
        )
        complete = evaluate_issue_intake(complete_body, [BUG_LABEL, NEEDS_INFO_LABEL])
        self.assertEqual(complete.mode, "delete")
        self.assertEqual(complete.needs_info_action, "remove")

    def test_evaluate_issue_intake_for_completed_support_request(self) -> None:
        docs_checked = "\n".join(f"- [x] {doc.path}" for doc in SUPPORT_PRECHECK_DOCS)
        question = SUPPORT_REQUEST_FIELDS[0]
        os_field = SUPPORT_REQUEST_FIELDS[1]
        python_field = SUPPORT_REQUEST_FIELDS[2]
        project_field = SUPPORT_REQUEST_FIELDS[3]
        command_field = SUPPORT_REQUEST_FIELDS[4]
        complete_body = (
            f"### {SUPPORT_REQUEST_CHECKLIST_LABEL}\n{docs_checked}\n\n"
            f"### {question.label}\nTrying to run the digest locally.\n\n"
            f"### {os_field.label}\nmacOS 15\n\n"
            f"### {python_field.label}\n3.12.3\n\n"
            f"### {project_field.label}\nmain\n\n"
            f"### {command_field.label}\npython -m paper_digest.cli run\n"
        )
        complete = evaluate_issue_intake(
            complete_body,
            ["support", NEEDS_INFO_LABEL],
        )
        self.assertEqual(complete.mode, "delete")
        self.assertEqual(complete.marker, SUPPORT_TRIAGE_MARKER)
        self.assertEqual(complete.needs_info_action, "remove")

    def test_evaluate_issue_intake_collects_missing_requirements(self) -> None:
        result = evaluate_issue_intake("", [BUG_LABEL])
        self.assertEqual(result.mode, "upsert")
        self.assertEqual(result.needs_info_action, "add")
        self.assertGreaterEqual(len(result.missing), 6)
        assert result.comment_body is not None
        self.assertIn(COMMUNITY_TRIAGE_MARKER, result.comment_body)
        self.assertIn(ISSUE_INTAKE_COMMENT_HEADER, result.comment_body)

    def test_evaluate_issue_intake_collects_missing_support_context(self) -> None:
        result = evaluate_issue_intake("", ["support"])
        self.assertEqual(result.mode, "upsert")
        self.assertEqual(result.marker, SUPPORT_TRIAGE_MARKER)
        self.assertEqual(result.needs_info_action, "add")
        self.assertIn(SUPPORT_PRECHECK_MISSING_MESSAGE, result.missing)
        assert result.comment_body is not None
        self.assertIn(SUPPORT_TRIAGE_MARKER, result.comment_body)
        self.assertIn(SUPPORT_TRIAGE_COMMENT_HEADER, result.comment_body)

    def test_main_writes_outputs_and_reports_missing_payload(self) -> None:
        stdout = StringIO()
        exit_code = main(
            env={
                "ISSUE_BODY": "",
                'ISSUE_LABELS_JSON': f'["{BUG_LABEL}"]',
            },
            stdout=stdout,
        )
        self.assertEqual(exit_code, 0)
        self.assertIn('"mode": "upsert"', stdout.getvalue())

        stderr = StringIO()
        exit_code = main(env={"ISSUE_BODY": ""}, stderr=stderr)
        self.assertEqual(exit_code, 1)
        self.assertIn("missing labels payload", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
