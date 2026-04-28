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
    IssueLabelSyncResult,
)


def sync_issue_labels(
    service: GitHubIssueLabelsService,
    issue_number: int,
    *,
    ensure_labels: Sequence[str],
    remove_labels: Sequence[str],
) -> IssueLabelSyncResult:
    return service.sync_labels(
        issue_number,
        ensure_labels=ensure_labels,
        remove_labels=remove_labels,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Synchronize managed GitHub issue or pull-request labels."
    )
    parser.add_argument("--repo", required=True, help="Repository in owner/name form.")
    parser.add_argument(
        "--issue-number",
        required=True,
        type=int,
        help="Issue or pull request number to update.",
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
        "--ensure",
        action="append",
        default=[],
        help="Label that must be present after synchronization. Repeat as needed.",
    )
    parser.add_argument(
        "--remove",
        action="append",
        default=[],
        help="Label that must be absent after synchronization. Repeat as needed.",
    )
    return parser


def main(
    *,
    repo: str,
    issue_number: int,
    ensure_labels: Sequence[str] = (),
    remove_labels: Sequence[str] = (),
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
            f"issue label sync failed: missing GitHub token in {token_env}",
            file=error_stream,
        )
        return 1

    try:
        result = sync_issue_labels(
            GitHubIssueLabelsService(repository=repo, token=token),
            issue_number,
            ensure_labels=ensure_labels,
            remove_labels=remove_labels,
        )
    except (OSError, ValueError, HTTPError, URLError) as exc:
        print(f"issue label sync failed: {exc}", file=error_stream)
        return 1

    changed: list[str] = []
    if result.added:
        changed.append("added " + ", ".join(result.added))
    if result.removed:
        changed.append("removed " + ", ".join(result.removed))
    if not changed:
        changed.append("unchanged")
    print("issue label sync: " + "; ".join(changed), file=output_stream)
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(
        repo=args.repo,
        issue_number=args.issue_number,
        ensure_labels=args.ensure,
        remove_labels=args.remove,
        token_env=args.token_env,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
