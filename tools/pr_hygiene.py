from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TextIO
from urllib.error import HTTPError, URLError

from tools.github_api import DEFAULT_GITHUB_TOKEN_ENV
from tools.github_services import GitHubPullRequestFilesService
from tools.pr_policy import (
    PR_HYGIENE_COMMENT_FOOTER,
    PR_HYGIENE_COMMENT_HEADER,
    PR_HYGIENE_MARKER,
    PR_TEMPLATE_LINKED_ISSUE_LABEL,
    PR_TEMPLATE_NO_CHANGELOG_LABEL,
    PR_TEMPLATE_NO_DOCS_LABEL,
    PR_TEMPLATE_NO_LINKED_ISSUE_LABEL,
    get_pr_hygiene_reminder,
)
from tools.workflow_outputs import emit_workflow_outputs
from tools.workflow_path_policy import (
    is_changelog_path,
    is_public_doc_path,
    is_runtime_or_ops_path,
    is_test_path,
)

DEFAULT_PR_BODY_ENV = "PR_BODY"


@dataclass(frozen=True)
class PrHygieneResult:
    mode: str
    marker: str
    comment_body: str | None
    reminders: tuple[str, ...]


def checkbox_checked(body: str, label: str) -> bool:
    escaped = re.escape(label)
    return re.search(rf"^- \[(x|X)\] {escaped}$", body, flags=re.MULTILINE) is not None


def line_value(body: str, label: str) -> str:
    escaped = re.escape(label)
    match = re.search(rf"^- {escaped}:\s*(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match is not None else ""


def has_reference(text: str) -> bool:
    return bool(
        re.search(r"#\d+", text)
        or re.search(r"/issues/\d+\b", text)
        or re.search(r"/pull/\d+\b", text)
    )


def body_has_issue_reference(body: str, linked_issue_value: str) -> bool:
    return bool(
        re.search(
            (
                r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|"
                r"ref(?:er(?:s|enced)?)?|related to)\s+#\d+\b"
            ),
            body,
            flags=re.IGNORECASE,
        )
        or has_reference(linked_issue_value)
    )


def evaluate_pr_hygiene(
    body: str,
    paths: Sequence[str],
    *,
    marker: str = PR_HYGIENE_MARKER,
) -> PrHygieneResult:
    changelog_touched = any(is_changelog_path(path) for path in paths)
    docs_touched = any(is_public_doc_path(path) for path in paths)
    likely_changelog_needed = any(is_runtime_or_ops_path(path) for path in paths)
    likely_docs_needed = any(is_runtime_or_ops_path(path) for path in paths)
    docs_only_or_tests_only = bool(paths) and all(
        is_public_doc_path(path)
        or is_changelog_path(path)
        or is_test_path(path)
        for path in paths
    )

    acknowledged_no_changelog = checkbox_checked(body, PR_TEMPLATE_NO_CHANGELOG_LABEL)
    acknowledged_no_docs = checkbox_checked(body, PR_TEMPLATE_NO_DOCS_LABEL)
    acknowledged_no_linked_issue = checkbox_checked(
        body,
        PR_TEMPLATE_NO_LINKED_ISSUE_LABEL,
    )
    linked_issue_value = line_value(body, PR_TEMPLATE_LINKED_ISSUE_LABEL)
    issue_reference_present = body_has_issue_reference(body, linked_issue_value)

    reminders: list[str] = []
    if (
        likely_changelog_needed
        and not docs_only_or_tests_only
        and not changelog_touched
        and not acknowledged_no_changelog
    ):
        reminders.append(get_pr_hygiene_reminder("changelog").message)

    if (
        likely_docs_needed
        and not docs_only_or_tests_only
        and not docs_touched
        and not acknowledged_no_docs
    ):
        reminders.append(get_pr_hygiene_reminder("docs").message)

    if (
        any(is_runtime_or_ops_path(path) for path in paths)
        and not docs_only_or_tests_only
        and not issue_reference_present
        and not acknowledged_no_linked_issue
    ):
        reminders.append(get_pr_hygiene_reminder("linked_issue").message)

    if not reminders:
        return PrHygieneResult(
            mode="delete",
            marker=marker,
            comment_body=None,
            reminders=(),
        )

    comment_body = "\n".join(
        [
            marker,
            PR_HYGIENE_COMMENT_HEADER,
            "",
            *[f"- {reminder}" for reminder in reminders],
            "",
            PR_HYGIENE_COMMENT_FOOTER,
        ]
    )
    return PrHygieneResult(
        mode="upsert",
        marker=marker,
        comment_body=comment_body,
        reminders=tuple(reminders),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate PR hygiene reminders for docs/changelog/context gaps."
    )
    parser.add_argument("--repo", required=True, help="Repository in owner/name form.")
    parser.add_argument(
        "--pull-number",
        required=True,
        type=int,
        help="Pull request number to inspect.",
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_GITHUB_TOKEN_ENV,
        help=(
            "Environment variable with the GitHub token. Defaults to "
            f"{DEFAULT_GITHUB_TOKEN_ENV}."
        ),
    )
    parser.add_argument(
        "--body-env",
        default=DEFAULT_PR_BODY_ENV,
        help=(
            "Environment variable with the PR body. Defaults to "
            f"{DEFAULT_PR_BODY_ENV}."
        ),
    )
    return parser


def main(
    *,
    repo: str,
    pull_number: int,
    token_env: str = DEFAULT_GITHUB_TOKEN_ENV,
    body_env: str = DEFAULT_PR_BODY_ENV,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    env: dict[str, str] | None = None,
) -> int:
    current_env = os.environ if env is None else env
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    token = current_env.get(token_env, "").strip()
    if not token:
        print(
            f"PR hygiene evaluation failed: missing GitHub token in {token_env}",
            file=error_stream,
        )
        return 1

    body = current_env.get(body_env, "")
    try:
        paths = GitHubPullRequestFilesService(
            repository=repo,
            token=token,
        ).list_paths(pull_number)
        result = evaluate_pr_hygiene(body, paths)
    except (OSError, ValueError, HTTPError, URLError) as exc:
        print(f"PR hygiene evaluation failed: {exc}", file=error_stream)
        return 1

    outputs = {
        "mode": result.mode,
        "marker": result.marker,
    }
    if result.comment_body is not None:
        outputs["comment-body"] = result.comment_body
    emit_workflow_outputs(outputs, env=current_env, stdout=output_stream)
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(
        repo=args.repo,
        pull_number=args.pull_number,
        token_env=args.token_env,
        body_env=args.body_env,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
