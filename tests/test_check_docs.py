from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.docs_findings import DocsCheckFinding
from tools.docs_parser import (
    collect_markdown_anchors,
    extract_issue_form_fields,
    extract_markdown_links,
    extract_repository_references,
    extract_workflow_body_lines,
    find_markdown_heading_line,
    find_markdown_heading_range,
    find_workflow_section_line,
    find_workflow_section_range,
    get_markdown_section_lines,
    iter_github_metadata_files,
    normalize_anchor,
    parse_bullet_fields,
    parse_checklist_items,
    parse_plain_bullet_items,
    split_template_sections,
)
from tools.docs_registry_checks import (
    check_maintainer_doc_registry,
)
from tools.lifecycle_checks import (
    check_issue_close_out_contract,
    check_issue_linkage_contract,
    check_issue_summary_semantics_contract,
    check_maintainer_issue_contract,
    check_release_lifecycle_contract,
)


def finding_messages(errors: list[DocsCheckFinding]) -> list[str]:
    return [error.message for error in errors]


class DocsCheckTests(unittest.TestCase):
    def test_normalize_anchor_matches_expected_slug_shape(self) -> None:
        self.assertEqual(
            normalize_anchor("CI Maintenance Policy"),
            "ci-maintenance-policy",
        )
        self.assertEqual(normalize_anchor("`make check` & Build"), "make-check-build")

    def test_collect_markdown_anchors_adds_suffix_for_duplicate_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            page = Path(tmpdir, "page.md")
            page.write_text(
                textwrap.dedent(
                    """\
                    # Title
                    ## Repeat
                    ## Repeat
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                collect_markdown_anchors(page),
                {"title", "repeat", "repeat-1"},
            )

    def test_extract_markdown_links_ignores_fenced_code_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            page = Path(tmpdir, "page.md")
            page.write_text(
                textwrap.dedent(
                    """\
                    [kept](./other.md#section)

                    ```md
                    [ignored](./broken.md)
                    ```
                    """
                ),
                encoding="utf-8",
            )

            links = extract_markdown_links(page)

            self.assertEqual(len(links), 1)
            self.assertEqual(links[0].target, "./other.md#section")

    def test_iter_github_metadata_files_finds_yaml_only_under_dot_github(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_form = root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"
            workflow = root / ".github" / "workflows" / "ci.yaml"
            non_yaml = root / ".github" / "pull_request_template.md"
            issue_form.parent.mkdir(parents=True)
            workflow.parent.mkdir(parents=True)
            issue_form.write_text("name: Bug report\n", encoding="utf-8")
            workflow.write_text("name: CI\n", encoding="utf-8")
            non_yaml.write_text("# PR template\n", encoding="utf-8")

            files = iter_github_metadata_files(root)

            self.assertEqual(files, [issue_form.resolve(), workflow.resolve()])

    def test_extract_repository_references_reads_yaml_paths_and_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = Path(tmpdir, "issue_form.yml")
            metadata.write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: markdown
                        attributes:
                          value: |
                            Use `docs/guide.md` and `README.md`.
                            https://github.com/X-PG13/paper-digest/blob/main/docs/guide.md
                            .github/CODEOWNERS
                    """
                ),
                encoding="utf-8",
            )

            references = extract_repository_references(metadata)

            self.assertEqual(
                [reference.target for reference in references],
                [
                    "docs/guide.md",
                    "README.md",
                    "docs/guide.md",
                    ".github/CODEOWNERS",
                ],
            )

    def test_get_markdown_section_lines_returns_named_section_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            page = Path(tmpdir, "README.md")
            page.write_text(
                textwrap.dedent(
                    """\
                    # Title

                    ## Docs Map
                    - one
                    - two

                    ## Next
                    - three
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                get_markdown_section_lines(page, "Docs Map"),
                ["- one", "- two", ""],
            )

    def test_extract_issue_form_fields_reads_ids_labels_and_literal_blocks(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            issue_form = Path(tmpdir, "release.yml")
            issue_form.write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: input
                        id: quarterly_review
                        attributes:
                          label: Latest quarterly review issue
                      - type: textarea
                        id: close_out
                        attributes:
                          label: Close-out handoff
                          value: |
                            - [ ] First item.
                            - [ ] Wrapped item
                              continues here.
                          placeholder: |
                            - Notes go here.
                    """
                ),
                encoding="utf-8",
            )

            fields = extract_issue_form_fields(issue_form)

            self.assertEqual(
                [
                    (
                        field.field_type,
                        field.field_id,
                        field.label,
                        field.line_number,
                        field.end_line,
                    )
                    for field in fields
                ],
                [
                    (
                        "input",
                        "quarterly_review",
                        "Latest quarterly review issue",
                        2,
                        5,
                    ),
                    ("textarea", "close_out", "Close-out handoff", 6, 15),
                ],
            )
            self.assertEqual(
                parse_checklist_items(list(fields[1].value_lines)),
                ["First item.", "Wrapped item continues here."],
            )
            self.assertEqual(
                list(fields[1].placeholder_lines),
                ["- Notes go here."],
            )

    def test_extract_workflow_body_lines_and_sections_parse_template_blocks(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = Path(tmpdir, "quarterly.yml")
            workflow.write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "<!-- quarterly-maintainer-review -->",
                      "Intro line.",
                      "## Review Summary",
                      "- Access changes: none",
                      "- Repository-settings drift: none",
                      "## Close-Out",
                      "- Link any follow-up issue or pull request here.",
                    ].join("\\n");
                    """
                ),
                encoding="utf-8",
            )

            intro_lines, sections = split_template_sections(
                extract_workflow_body_lines(workflow)
            )

            self.assertEqual(
                intro_lines,
                ["<!-- quarterly-maintainer-review -->", "Intro line."],
            )
            self.assertEqual(
                parse_bullet_fields(sections["Review Summary"]),
                {
                    "Access changes": "none",
                    "Repository-settings drift": "none",
                },
            )
            self.assertEqual(
                parse_plain_bullet_items(sections["Close-Out"]),
                ["Link any follow-up issue or pull request here."],
            )
            self.assertEqual(find_workflow_section_line(workflow, None), 2)
            self.assertEqual(find_workflow_section_line(workflow, "Review Summary"), 4)
            self.assertEqual(find_workflow_section_range(workflow, None), (2, 3))
            self.assertEqual(
                find_workflow_section_range(workflow, "Review Summary"),
                (4, 6),
            )

    def test_find_markdown_heading_line_returns_heading_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            page = Path(tmpdir, "README.md")
            page.write_text(
                textwrap.dedent(
                    """\
                    # Title

                    ## Docs Map
                    - one
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(find_markdown_heading_line(page, "Docs Map"), 3)
            self.assertEqual(find_markdown_heading_range(page, "Docs Map"), (3, 4))
            self.assertIsNone(find_markdown_heading_line(page, "Missing"))
            self.assertEqual(find_markdown_heading_range(page, "Missing"), (None, None))

    def test_check_maintainer_doc_registry_accepts_aligned_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs = root / "docs"
            docs.mkdir()
            (root / "README.md").write_text(
                textwrap.dedent(
                    """\
                    # Project

                    ## Docs Map
                    - Maintainer hub:
                      [`docs/maintainer-operations-hub.md`](./docs/maintainer-operations-hub.md)
                    - Review policy: [`docs/review-policy.md`](./docs/review-policy.md)
                    - Access policy:
                      [`docs/maintainer-access-policy.md`](./docs/maintainer-access-policy.md)
                    """
                ),
                encoding="utf-8",
            )
            (docs / "maintainer-operations-hub.md").write_text(
                textwrap.dedent(
                    """\
                    # Hub

                    ## Source-Of-Truth Map

                    | Area | Source of truth |
                    | --- | --- |
                    | review | `docs/review-policy.md` |
                    | access | `docs/maintainer-access-policy.md` |
                    """
                ),
                encoding="utf-8",
            )
            (docs / "maintainer-guide.md").write_text(
                textwrap.dedent(
                    """\
                    # Guide

                    ## Governance Documents

                    - `docs/review-policy.md`: review rules.
                    - `docs/maintainer-access-policy.md`: access rules.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "review-policy.md").write_text("# Review\n", encoding="utf-8")
            (docs / "maintainer-access-policy.md").write_text(
                "# Access\n",
                encoding="utf-8",
            )

            self.assertEqual(check_maintainer_doc_registry(root), [])

    def test_check_maintainer_doc_registry_reports_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs = root / "docs"
            docs.mkdir()
            (root / "README.md").write_text(
                textwrap.dedent(
                    """\
                    # Project

                    ## Docs Map
                    - Review policy: [`docs/review-policy.md`](./docs/review-policy.md)
                    """
                ),
                encoding="utf-8",
            )
            (docs / "maintainer-operations-hub.md").write_text(
                textwrap.dedent(
                    """\
                    # Hub

                    ## Source-Of-Truth Map

                    | Area | Source of truth |
                    | --- | --- |
                    | review | `docs/review-policy.md` |
                    | access | `docs/maintainer-access-policy.md` |
                    """
                ),
                encoding="utf-8",
            )
            (docs / "maintainer-guide.md").write_text(
                textwrap.dedent(
                    """\
                    # Guide

                    ## Governance Documents

                    - `docs/review-policy.md`: review rules.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "review-policy.md").write_text("# Review\n", encoding="utf-8")
            (docs / "maintainer-access-policy.md").write_text(
                "# Access\n",
                encoding="utf-8",
            )

            errors = check_maintainer_doc_registry(root)

            self.assertEqual(len(errors), 3)
            self.assertEqual(errors[0].path, "README.md")
            self.assertEqual(errors[0].line, 3)
            self.assertEqual(errors[0].end_line, 4)
            self.assertIn(
                "docs/maintainer-access-policy.md",
                errors[0].message,
            )
            self.assertEqual(errors[1].path, "docs/maintainer-guide.md")
            self.assertEqual(errors[1].line, 3)
            self.assertEqual(errors[1].end_line, 5)
            self.assertIn(
                "docs/maintainer-access-policy.md",
                errors[1].message,
            )
            self.assertEqual(errors[2].path, "README.md")
            self.assertEqual(errors[2].line, 3)
            self.assertEqual(errors[2].end_line, 4)
            self.assertIn(
                "docs/maintainer-operations-hub.md",
                errors[2].message,
            )

    def test_check_release_lifecycle_contract_accepts_aligned_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_templates = root / ".github" / "ISSUE_TEMPLATE"
            docs = root / "docs"
            issue_templates.mkdir(parents=True)
            docs.mkdir()

            (root / "RELEASING.md").write_text(
                textwrap.dedent(
                    """\
                    # Releasing

                    ## Before Tagging
                    - Ensure `CHANGELOG.md` is updated.
                    - Confirm the version in `paper_digest/__about__.py`.
                    - Run `make check`, `make build`, and `make release-check`.
                    - Confirm the latest quarterly review issue is current.
                    - Keep the release-preparation issue linked from the
                      release-preparation pull request.

                    ## After Release
                    - Open or confirm the `Post-release follow-up` issue and
                      keep it linked.
                    - Verify that the GitHub release contains both the wheel
                      and source archive.
                    - Verify that the generated release notes match `CHANGELOG.md`.
                    - Verify compatibility statements in `README.md` and
                      `docs/compatibility-matrix.md`.
                    - Bump the version for the next development cycle if needed.
                    - Add a fresh `Unreleased` section.
                    - Capture any release retrospective.
                    - Update `docs/operations-history.md`.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "release-lifecycle-runbook.md").write_text(
                textwrap.dedent(
                    """\
                    # Runbook

                    ## Linkage Rules
                    - The release-preparation issue should link the latest
                      quarterly review issue.
                    - The release-preparation pull request should link the
                      release-preparation issue.
                    - The post-release follow-up issue should link the
                      release-preparation issue.
                    - Once the release is complete, update
                      `docs/operations-history.md`.

                    ## Release-Prep Responsibilities
                    - confirm scope, changelog intent, and compatibility claims
                    - decide whether the latest quarterly review is still current

                    ## Post-Release Responsibilities
                    - verify the published release artifacts and release notes
                    - verify compatibility claims after publication
                    - confirm next-cycle setup such as a fresh `Unreleased` section
                    - capture release retrospective notes while they are still fresh
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "release_preparation.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        attributes:
                          value: |
                            - [ ] `CHANGELOG.md` updated.
                            - [ ] The latest quarterly maintainer review issue
                              is current.
                            - [ ] `make check`
                            - [ ] `make build`
                            - [ ] `make release-check`
                            - [ ] Version in `paper_digest/__about__.py` confirmed.
                            - [ ] Release-preparation PR linked here.
                            - [ ] Post-release follow-up issue linked after publication.
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "post_release_follow_up.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        attributes:
                          value: |
                            - [ ] Release-preparation issue linked.
                            - [ ] GitHub release artifacts verified.
                            - [ ] Generated release notes match `CHANGELOG.md`.
                            - [ ] Compatibility claims in `README.md` and
                              `docs/compatibility-matrix.md` still match the
                              published release.
                            - [ ] Next development-cycle version bump tracked
                              or completed.
                            - [ ] `CHANGELOG.md` has an `Unreleased` section
                              ready for new work.
                            - [ ] `docs/operations-history.md` updated.
                            - [ ] Release retrospective captured.
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(check_release_lifecycle_contract(root), [])

    def test_check_release_lifecycle_contract_reports_missing_contract_items(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_templates = root / ".github" / "ISSUE_TEMPLATE"
            docs = root / "docs"
            issue_templates.mkdir(parents=True)
            docs.mkdir()

            (root / "RELEASING.md").write_text(
                textwrap.dedent(
                    """\
                    # Releasing

                    ## Before Tagging
                    - Ensure `CHANGELOG.md` is updated.

                    ## After Release
                    - Verify that the GitHub release contains both the wheel
                      and source archive.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "release-lifecycle-runbook.md").write_text(
                textwrap.dedent(
                    """\
                    # Runbook

                    ## Linkage Rules
                    - The post-release follow-up issue should link the
                      release-preparation issue.

                    ## Release-Prep Responsibilities
                    - decide whether the latest quarterly review is still current

                    ## Post-Release Responsibilities
                    - verify the published release artifacts and release notes
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "release_preparation.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        attributes:
                          value: |
                            - [ ] `CHANGELOG.md` updated.
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "post_release_follow_up.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        attributes:
                          value: |
                            - [ ] GitHub release artifacts verified.
                    """
                ),
                encoding="utf-8",
            )

            errors = check_release_lifecycle_contract(root)

            self.assertTrue(errors)
            self.assertTrue(
                any(
                    "release prep verification suite" in error
                    for error in finding_messages(errors)
                )
            )
            self.assertTrue(
                any(
                    "operations history update" in error
                    for error in finding_messages(errors)
                )
            )

    def test_check_maintainer_issue_contract_accepts_aligned_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_templates = root / ".github" / "ISSUE_TEMPLATE"
            workflows = root / ".github" / "workflows"
            docs = root / "docs"
            issue_templates.mkdir(parents=True)
            workflows.mkdir(parents=True)
            docs.mkdir()

            (root / "RELEASING.md").write_text(
                textwrap.dedent(
                    """\
                    # Releasing

                    ## Draft Release Notes
                    1. Highlights: user-facing wins.
                    2. Config or workflow changes: operator follow-up.
                    3. Compatibility notes: support expectations.
                    4. Upgrade notes: manual next steps.
                    5. Repository-operations notes: maintainer-facing changes.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "quarterly-maintainer-review.md").write_text(
                textwrap.dedent(
                    """\
                    # Quarterly Maintainer Review

                    ## Close-Out Expectations
                    - close the issue with a short summary of what changed or that
                      no changes were required
                    - mention follow-up work explicitly if the review uncovered
                      deferred cleanup

                    ## Review Summary Template
                    ```md
                    ## Review Summary

                    - Review date: YYYY-MM-DD
                    - Reviewed by: @maintainer
                    - Access changes: none | short summary
                    - Repository-settings drift: none | short summary
                    - Docs updated: none | PR or file list
                    - Follow-up work: none | issue or PR links
                    - Release impact: none | operator-facing note
                    - Next review due: YYYY-MM-DD
                    ```
                    """
                ),
                encoding="utf-8",
            )
            (docs / "post-release-checklist.md").write_text(
                textwrap.dedent(
                    """\
                    # Post-Release Checklist

                    ## Close-Out Expectations
                    - close the issue with a short summary of what was verified
                      or changed
                    - link any follow-up pull request or maintenance issue
                    - note explicitly if no additional work was needed

                    ## Follow-Up Summary Template
                    ```md
                    ## Post-Release Summary

                    - Release: vX.Y.Z
                    - Verified by: @maintainer
                    - Artifacts and release notes: confirmed | short summary
                    - Compatibility and docs drift: none | short summary
                    - Next-cycle setup: complete | short summary
                    - Retro follow-up: none | issue or PR links
                    - Additional repository-operations follow-up: none | short summary
                    ```
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "quarterly-maintainer-review.yml").write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "## Close-Out",
                      "Link any follow-up issue or pull request here.",
                      "If no changes were needed, say so explicitly before closing.",
                      "## Review Summary",
                      "- Review date:",
                      "- Reviewed by:",
                      "- Access changes:",
                      "- Repository-settings drift:",
                      "- Docs updated:",
                      "- Follow-up work:",
                      "- Release impact:",
                      "- Next review due:",
                    ];
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "post-release-follow-up.yml").write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "## Post-Release Summary",
                      "- Release:",
                      "- Verified by:",
                      "- Artifacts and release notes:",
                      "- Compatibility and docs drift:",
                      "- Next-cycle setup:",
                      "- Retro follow-up:",
                      "- Additional repository-operations follow-up:",
                    ];
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "release_preparation.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        attributes:
                          placeholder: |
                            - Highlights:
                            - Config or workflow changes:
                            - Compatibility notes:
                            - Upgrade notes:
                            - Repository-operations notes:
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "post_release_follow_up.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        attributes:
                          label: Close-out summary
                          value: |
                            - [ ] Post-release summary added.
                            - [ ] Follow-up PRs or issues linked.
                            - [ ] No remaining immediate post-release work, or
                              remaining work is explicitly tracked.
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(check_maintainer_issue_contract(root), [])

    def test_check_maintainer_issue_contract_reports_missing_template_items(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_templates = root / ".github" / "ISSUE_TEMPLATE"
            workflows = root / ".github" / "workflows"
            docs = root / "docs"
            issue_templates.mkdir(parents=True)
            workflows.mkdir(parents=True)
            docs.mkdir()

            (root / "RELEASING.md").write_text(
                textwrap.dedent(
                    """\
                    # Releasing

                    ## Draft Release Notes
                    1. Highlights: user-facing wins.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "quarterly-maintainer-review.md").write_text(
                textwrap.dedent(
                    """\
                    # Quarterly Maintainer Review

                    ## Close-Out Expectations
                    - close the issue with a short summary of what changed

                    ## Review Summary Template
                    ```md
                    ## Review Summary

                    - Review date: YYYY-MM-DD
                    ```
                    """
                ),
                encoding="utf-8",
            )
            (docs / "post-release-checklist.md").write_text(
                textwrap.dedent(
                    """\
                    # Post-Release Checklist

                    ## Close-Out Expectations
                    - close the issue with a short summary of what was verified
                      or changed

                    ## Follow-Up Summary Template
                    ```md
                    ## Post-Release Summary

                    - Release: vX.Y.Z
                    ```
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "quarterly-maintainer-review.yml").write_text(
                "const body = [\"## Review Summary\", \"- Review date:\"];\n",
                encoding="utf-8",
            )
            (workflows / "post-release-follow-up.yml").write_text(
                "const body = [\"## Post-Release Summary\", \"- Release:\"];\n",
                encoding="utf-8",
            )
            (issue_templates / "release_preparation.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        attributes:
                          placeholder: |
                            - Highlights:
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "post_release_follow_up.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        attributes:
                          label: Close-out summary
                    """
                ),
                encoding="utf-8",
            )

            errors = check_maintainer_issue_contract(root)

            self.assertTrue(errors)
            self.assertTrue(
                any(
                    "release-prep scope summary" in error
                    for error in finding_messages(errors)
                )
            )
            self.assertTrue(
                any(
                    "quarterly review summary template" in error
                    for error in finding_messages(errors)
                )
            )
            self.assertTrue(
                any(
                    "post-release close-out" in error
                    for error in finding_messages(errors)
                )
            )

    def test_check_issue_linkage_contract_accepts_aligned_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_templates = root / ".github" / "ISSUE_TEMPLATE"
            workflows = root / ".github" / "workflows"
            docs = root / "docs"
            issue_templates.mkdir(parents=True)
            workflows.mkdir(parents=True)
            docs.mkdir()

            (root / "RELEASING.md").write_text(
                textwrap.dedent(
                    """\
                    # Releasing

                    ## Before Tagging
                    - Confirm the latest quarterly review issue is current.
                    - Keep the release-preparation issue linked from the
                      release-preparation pull request.

                    ## After Release
                    - Open or confirm the Post-release follow-up issue and keep it
                      linked from the release-preparation issue.
                    - If repository-operations changes shipped, record the linked
                      quarterly review issue there as well.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "release-lifecycle-runbook.md").write_text(
                textwrap.dedent(
                    """\
                    # Release Lifecycle Runbook

                    ## Linkage Rules
                    - The release-preparation issue should link the latest
                      quarterly review issue.
                    - The release-preparation pull request should link the
                      release-preparation issue.
                    - The post-release follow-up issue should link the
                      release-preparation issue.
                    - Once the post-release issue exists, update the
                      release-preparation issue so the forward link is visible
                      from both ends.
                    - If repository-operations changes shipped in the release,
                      the post-release follow-up issue should link the latest
                      quarterly review issue.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "quarterly-maintainer-review.md").write_text(
                textwrap.dedent(
                    """\
                    # Quarterly Maintainer Review

                    ## Release Linkage
                    - Link the latest quarterly review issue from the
                      release-preparation pull request or maintainer notes.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "post-release-checklist.md").write_text(
                textwrap.dedent(
                    """\
                    # Post-Release Checklist

                    ## Repository Follow-Up
                    - any quarterly maintainer review linkage remains valid
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "release_preparation.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: input
                        id: quarterly_review
                        attributes:
                          label: Latest quarterly review issue
                      - type: textarea
                        id: follow_up
                        attributes:
                          label: Release and post-release follow-up
                          value: |
                            - [ ] Release-preparation PR linked here.
                            - [ ] Post-release follow-up issue linked after publication.
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "post_release_follow_up.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: input
                        id: release_prep_issue
                        attributes:
                          label: Release-preparation issue
                      - type: input
                        id: published_release_url
                        attributes:
                          label: Published release URL
                      - type: input
                        id: quarterly_review_issue
                        attributes:
                          label: Latest quarterly review issue
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "post-release-follow-up.yml").write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      `Release: ${releaseUrl}`,
                      "Update this issue with the linked release-preparation issue and",
                      "quarterly review issue when repository-operations changes",
                      "shipped.",
                    ];
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(check_issue_linkage_contract(root), [])

    def test_check_issue_linkage_contract_reports_missing_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_templates = root / ".github" / "ISSUE_TEMPLATE"
            workflows = root / ".github" / "workflows"
            docs = root / "docs"
            issue_templates.mkdir(parents=True)
            workflows.mkdir(parents=True)
            docs.mkdir()

            (root / "RELEASING.md").write_text(
                textwrap.dedent(
                    """\
                    # Releasing

                    ## Before Tagging
                    - Keep notes.

                    ## After Release
                    - Verify artifacts.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "release-lifecycle-runbook.md").write_text(
                textwrap.dedent(
                    """\
                    # Release Lifecycle Runbook

                    ## Linkage Rules
                    - Keep artifacts visible.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "quarterly-maintainer-review.md").write_text(
                textwrap.dedent(
                    """\
                    # Quarterly Maintainer Review

                    ## Release Linkage
                    - Review the release later.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "post-release-checklist.md").write_text(
                textwrap.dedent(
                    """\
                    # Post-Release Checklist

                    ## Repository Follow-Up
                    - Track next steps.
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "release_preparation.yml").write_text(
                "body:\n  - type: input\n    id: version\n",
                encoding="utf-8",
            )
            (issue_templates / "post_release_follow_up.yml").write_text(
                "body:\n  - type: input\n    id: release_version\n",
                encoding="utf-8",
            )
            (workflows / "post-release-follow-up.yml").write_text(
                "const body = [\"Release ready\"];\n",
                encoding="utf-8",
            )

            errors = check_issue_linkage_contract(root)

            self.assertTrue(errors)
            self.assertTrue(
                any(
                    "quarterly review handoff" in error
                    for error in finding_messages(errors)
                )
            )
            self.assertTrue(
                any(
                    "release-prep linkage fields" in error
                    for error in finding_messages(errors)
                )
            )
            self.assertTrue(
                any(
                    "post-release quarterly review linkage" in error
                    for error in finding_messages(errors)
                )
            )

    def test_check_issue_close_out_contract_accepts_aligned_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_templates = root / ".github" / "ISSUE_TEMPLATE"
            workflows = root / ".github" / "workflows"
            docs = root / "docs"
            issue_templates.mkdir(parents=True)
            workflows.mkdir(parents=True)
            docs.mkdir()

            (root / "RELEASING.md").write_text(
                textwrap.dedent(
                    """\
                    # Releasing

                    ## After Release
                    - Close the release-preparation issue only after the
                      post-release follow-up issue is linked there and any
                      remaining immediate follow-up work is linked or stated as
                      `none`.
                    - Capture any release retrospective or operator-facing
                      follow-up in the post-release issue before closing it,
                      and link remaining work or say `none` explicitly.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "release-lifecycle-runbook.md").write_text(
                textwrap.dedent(
                    """\
                    # Release Lifecycle Runbook

                    ## Issue Close-Out Expectations
                    - Close quarterly maintainer review issues with a short
                      summary, and write `none` explicitly when no changes or
                      follow-up work were needed.
                    - Close release-preparation issues only after the
                      post-release follow-up issue is linked. If immediate
                      follow-up work remains, link it there; otherwise say
                      `none` explicitly in the closing handoff note.
                    - Close post-release follow-up issues with a short summary
                      that links any remaining follow-up work, or says `none`
                      explicitly when nothing remains.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "quarterly-maintainer-review.md").write_text(
                textwrap.dedent(
                    """\
                    # Quarterly Maintainer Review

                    ## Close-Out Expectations
                    - close the issue with a short summary of what changed or
                      that no changes were needed
                    - mention follow-up work explicitly if the review uncovered
                      deferred cleanup
                    """
                ),
                encoding="utf-8",
            )
            (docs / "post-release-checklist.md").write_text(
                textwrap.dedent(
                    """\
                    # Post-Release Checklist

                    ## Close-Out Expectations
                    - close the issue with a short summary of what was verified
                      or changed
                    - link any follow-up pull request or maintenance issue
                    - note explicitly if no additional work was needed
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "quarterly-maintainer-review.yml").write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "## Close-Out",
                      "- Link any follow-up issue or pull request here.",
                      "- If no changes were needed, say so explicitly before closing.",
                    ];
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "release_preparation.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        id: close_out
                        attributes:
                          label: Close-out handoff
                          value: |
                            - [ ] Post-release follow-up issue linked here.
                            - [ ] Any remaining immediate follow-up work is
                              linked there, or `none` is stated explicitly.
                            - [ ] Release-preparation summary or maintainer
                              notes are complete.
                    """
                ),
                encoding="utf-8",
            )
            (issue_templates / "post_release_follow_up.yml").write_text(
                textwrap.dedent(
                    """\
                    body:
                      - type: textarea
                        id: close_out
                        attributes:
                          label: Close-out summary
                          value: |
                            - [ ] Post-release summary added.
                            - [ ] Follow-up PRs or issues linked.
                            - [ ] No remaining immediate post-release work, or
                              remaining work is explicitly tracked.
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(check_issue_close_out_contract(root), [])

    def test_check_issue_close_out_contract_reports_missing_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            issue_templates = root / ".github" / "ISSUE_TEMPLATE"
            workflows = root / ".github" / "workflows"
            docs = root / "docs"
            issue_templates.mkdir(parents=True)
            workflows.mkdir(parents=True)
            docs.mkdir()

            (root / "RELEASING.md").write_text(
                textwrap.dedent(
                    """\
                    # Releasing

                    ## After Release
                    - Verify artifacts.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "release-lifecycle-runbook.md").write_text(
                textwrap.dedent(
                    """\
                    # Release Lifecycle Runbook

                    ## Issue Close-Out Expectations
                    - Keep notes.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "quarterly-maintainer-review.md").write_text(
                textwrap.dedent(
                    """\
                    # Quarterly Maintainer Review

                    ## Close-Out Expectations
                    - close the issue
                    """
                ),
                encoding="utf-8",
            )
            (docs / "post-release-checklist.md").write_text(
                textwrap.dedent(
                    """\
                    # Post-Release Checklist

                    ## Close-Out Expectations
                    - close the issue
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "quarterly-maintainer-review.yml").write_text(
                "const body = [];\n",
                encoding="utf-8",
            )
            (issue_templates / "release_preparation.yml").write_text(
                "body:\n  - type: input\n    id: version\n",
                encoding="utf-8",
            )
            (issue_templates / "post_release_follow_up.yml").write_text(
                "body:\n  - type: input\n    id: release_version\n",
                encoding="utf-8",
            )

            errors = check_issue_close_out_contract(root)

            self.assertTrue(errors)
            self.assertTrue(
                any(
                    "quarterly review close-out rule" in error
                    for error in finding_messages(errors)
                )
            )
            self.assertTrue(
                any(
                    "release-preparation close-out rule" in error
                    for error in finding_messages(errors)
                )
            )
            self.assertTrue(
                any(
                    "post-release close-out rule" in error
                    for error in finding_messages(errors)
                )
            )

    def test_check_issue_summary_semantics_contract_accepts_aligned_defaults(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workflows = root / ".github" / "workflows"
            docs = root / "docs"
            workflows.mkdir(parents=True)
            docs.mkdir()

            (docs / "quarterly-maintainer-review.md").write_text(
                textwrap.dedent(
                    """\
                    # Quarterly Maintainer Review

                    ## Review Summary Template
                    ```md
                    ## Review Summary

                    - Access changes: none | short summary
                    - Repository-settings drift: none | short summary
                    - Docs updated: none | PR or file list
                    - Follow-up work: none | issue or PR links
                    - Release impact: none | operator-facing note
                    ```

                    The scheduled workflow should prefill the mutable summary
                    fields with `none`; replace `none` with a short summary,
                    file list, or issue/PR links only where the review changed
                    something.
                    """
                ),
                encoding="utf-8",
            )
            (docs / "post-release-checklist.md").write_text(
                textwrap.dedent(
                    """\
                    # Post-Release Checklist

                    ## Follow-Up Summary Template
                    ```md
                    ## Post-Release Summary

                    - Artifacts and release notes: confirmed | short summary
                    - Compatibility and docs drift: none | short summary
                    - Next-cycle setup: complete | short summary
                    - Retro follow-up: none | issue or PR links
                    - Additional repository-operations follow-up: none | short summary
                    ```

                    The release-triggered workflow should prefill the mutable
                    status fields as `confirmed`, `none`, `complete`, `none`,
                    and `none`; replace those defaults with a short summary or
                    issue/PR links only where follow-up exists.
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "quarterly-maintainer-review.yml").write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "## Review Summary",
                      "- Access changes: none",
                      "- Repository-settings drift: none",
                      "- Docs updated: none",
                      "- Follow-up work: none",
                      "- Release impact: none",
                    ];
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "post-release-follow-up.yml").write_text(
                textwrap.dedent(
                    """\
                    const body = [
                      "## Post-Release Summary",
                      "- Artifacts and release notes: confirmed",
                      "- Compatibility and docs drift: none",
                      "- Next-cycle setup: complete",
                      "- Retro follow-up: none",
                      "- Additional repository-operations follow-up: none",
                    ];
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(check_issue_summary_semantics_contract(root), [])

    def test_check_issue_summary_semantics_contract_reports_missing_defaults(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workflows = root / ".github" / "workflows"
            docs = root / "docs"
            workflows.mkdir(parents=True)
            docs.mkdir()

            (docs / "quarterly-maintainer-review.md").write_text(
                textwrap.dedent(
                    """\
                    # Quarterly Maintainer Review

                    ## Review Summary Template
                    ```md
                    ## Review Summary

                    - Access changes: none
                    ```
                    """
                ),
                encoding="utf-8",
            )
            (docs / "post-release-checklist.md").write_text(
                textwrap.dedent(
                    """\
                    # Post-Release Checklist

                    ## Follow-Up Summary Template
                    ```md
                    ## Post-Release Summary

                    - Artifacts and release notes: confirmed
                    ```
                    """
                ),
                encoding="utf-8",
            )
            (workflows / "quarterly-maintainer-review.yml").write_text(
                "const body = [];\n",
                encoding="utf-8",
            )
            (workflows / "post-release-follow-up.yml").write_text(
                "const body = [];\n",
                encoding="utf-8",
            )

            errors = check_issue_summary_semantics_contract(root)

            self.assertTrue(errors)
            self.assertTrue(
                any(
                    "quarterly summary semantics" in error
                    for error in finding_messages(errors)
                )
            )
            self.assertTrue(
                any(
                    "post-release summary semantics" in error
                    for error in finding_messages(errors)
                )
            )


if __name__ == "__main__":
    unittest.main()
