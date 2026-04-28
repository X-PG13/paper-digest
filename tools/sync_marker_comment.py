from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO
from urllib.error import HTTPError, URLError

from tools.github_api import DEFAULT_GITHUB_TOKEN_ENV
from tools.github_services import GitHubManagedCommentsService


def sync_marker_comment(
    service: GitHubManagedCommentsService,
    *,
    issue_number: int,
    marker: str,
    desired_body: str | None,
) -> str:
    return service.sync_marker_comment(
        issue_number=issue_number,
        marker=marker,
        desired_body=desired_body,
    )


def load_comment_body(
    *,
    body_file: Path | None = None,
    body_env: str | None = None,
) -> str:
    if body_file is not None:
        return body_file.read_text(encoding="utf-8").strip()

    if body_env is None:
        raise ValueError("comment body source is missing")
    return os.environ.get(body_env, "").strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create, update, or delete a GitHub issue comment selected by a "
            "stable marker string."
        )
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository in owner/name form.",
    )
    parser.add_argument(
        "--issue-number",
        required=True,
        type=int,
        help="Issue or pull request number to synchronize.",
    )
    parser.add_argument(
        "--marker",
        required=True,
        help="Unique marker string used to identify the managed comment.",
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_GITHUB_TOKEN_ENV,
        help=(
            "Environment variable that holds the GitHub token. "
            f"Defaults to {DEFAULT_GITHUB_TOKEN_ENV}."
        ),
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--body-file",
        type=Path,
        help="Read the desired comment body from this file.",
    )
    mode_group.add_argument(
        "--body-env",
        help="Read the desired comment body from this environment variable.",
    )
    mode_group.add_argument(
        "--delete",
        action="store_true",
        help="Delete the managed comment if it exists.",
    )
    return parser


def main(
    *,
    repo: str,
    issue_number: int,
    marker: str,
    body_file: Path | None = None,
    body_env: str | None = None,
    delete: bool = False,
    token_env: str = DEFAULT_GITHUB_TOKEN_ENV,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    token = os.environ.get(token_env, "").strip()
    if not token:
        print(
            f"marker comment sync failed: missing GitHub token in {token_env}",
            file=error_stream,
        )
        return 1

    try:
        desired_body = None if delete else load_comment_body(
            body_file=body_file,
            body_env=body_env,
        )
        if desired_body == "":
            raise ValueError("comment body is empty")
        action = sync_marker_comment(
            GitHubManagedCommentsService(repository=repo, token=token),
            issue_number=issue_number,
            marker=marker,
            desired_body=desired_body,
        )
    except (OSError, ValueError, HTTPError, URLError) as exc:
        print(f"marker comment sync failed: {exc}", file=error_stream)
        return 1

    print(action, file=output_stream)
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(
        repo=args.repo,
        issue_number=args.issue_number,
        marker=args.marker,
        body_file=args.body_file,
        body_env=args.body_env,
        delete=args.delete,
        token_env=args.token_env,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
