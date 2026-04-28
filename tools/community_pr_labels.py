from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from typing import TextIO
from urllib.error import HTTPError, URLError

from tools.github_api import DEFAULT_GITHUB_TOKEN_ENV
from tools.github_services import (
    GitHubIssueLabelsService,
    GitHubPullRequestFilesService,
)
from tools.label_behavior_policy import DOCUMENTATION_LABEL
from tools.workflow_path_policy import (
    is_governance_path,
    is_public_doc_path,
)
from tools.workflow_path_policy import (
    is_maintenance_path as is_repository_maintenance_path,
)


def is_documentation_path(path: str) -> bool:
    return is_public_doc_path(path) or path.endswith(".md")


def is_maintenance_path(path: str) -> bool:
    return is_repository_maintenance_path(path)


def desired_pr_labels(paths: Sequence[str], *, actor: str) -> tuple[str, ...]:
    desired: list[str] = []

    if any(is_documentation_path(path) for path in paths):
        desired.append(DOCUMENTATION_LABEL)
    if any(is_maintenance_path(path) for path in paths):
        desired.append("maintenance")
    if actor == "dependabot[bot]" or ".github/dependabot.yml" in paths:
        desired.append("dependencies")
    if any(is_governance_path(path) for path in paths):
        desired.append("proposal")

    return tuple(desired)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply path-based labels to a pull request."
    )
    parser.add_argument("--repo", required=True, help="Repository in owner/name form.")
    parser.add_argument(
        "--pull-number",
        required=True,
        type=int,
        help="Pull request number to inspect.",
    )
    parser.add_argument(
        "--actor",
        required=True,
        help="GitHub actor associated with the pull request event.",
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_GITHUB_TOKEN_ENV,
        help=(
            "Environment variable with the GitHub token. Defaults to "
            f"{DEFAULT_GITHUB_TOKEN_ENV}."
        ),
    )
    return parser


def main(
    *,
    repo: str,
    pull_number: int,
    actor: str,
    token_env: str = DEFAULT_GITHUB_TOKEN_ENV,
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
            f"community PR label routing failed: missing GitHub token in {token_env}",
            file=error_stream,
        )
        return 1

    try:
        paths = GitHubPullRequestFilesService(
            repository=repo,
            token=token,
        ).list_paths(pull_number)
        desired_labels = desired_pr_labels(paths, actor=actor)
        result = GitHubIssueLabelsService(
            repository=repo,
            token=token,
        ).sync_labels(
            pull_number,
            ensure_labels=desired_labels,
            remove_labels=(),
        )
    except (OSError, ValueError, HTTPError, URLError) as exc:
        print(f"community PR label routing failed: {exc}", file=error_stream)
        return 1

    if result.added:
        print(
            "community PR label routing: added " + ", ".join(result.added),
            file=output_stream,
        )
    else:
        print("community PR label routing: unchanged", file=output_stream)
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(
        repo=args.repo,
        pull_number=args.pull_number,
        actor=args.actor,
        token_env=args.token_env,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
