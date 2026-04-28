from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO
from urllib.error import HTTPError, URLError

from tools.github_api import DEFAULT_GITHUB_TOKEN_ENV
from tools.github_services import (
    GitHubRepositoryLabelsService,
    RepositoryLabelSpec,
    RepositoryLabelSyncResult,
)

DEFAULT_LABELS_FILE = Path(".github/labels.json")


def load_label_specs(path: Path) -> tuple[RepositoryLabelSpec, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("labels file must contain a JSON list")

    labels: list[RepositoryLabelSpec] = []
    seen: set[str] = set()
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"label #{index} must be a JSON object")

        try:
            name = item["name"]
            color = item["color"]
            description = item["description"]
        except KeyError as exc:
            raise ValueError(f"label #{index} is missing {exc.args[0]!r}") from exc

        if not all(isinstance(value, str) for value in (name, color, description)):
            raise ValueError(f"label #{index} fields must be strings")
        if not name.strip() or not color.strip():
            raise ValueError(f"label #{index} name and color must be non-empty")
        if name in seen:
            raise ValueError(f"duplicate label name: {name}")

        seen.add(name)
        labels.append(
            RepositoryLabelSpec(
                name=name,
                color=color,
                description=description,
            )
        )

    return tuple(labels)


def sync_repository_labels(
    service: GitHubRepositoryLabelsService,
    labels: Sequence[RepositoryLabelSpec],
) -> RepositoryLabelSyncResult:
    return service.sync_labels(labels)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Synchronize repository labels from .github/labels.json."
    )
    parser.add_argument("--repo", required=True, help="Repository in owner/name form.")
    parser.add_argument(
        "--labels-file",
        type=Path,
        default=DEFAULT_LABELS_FILE,
        help=f"JSON label registry to sync. Defaults to {DEFAULT_LABELS_FILE}.",
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
    labels_file: Path = DEFAULT_LABELS_FILE,
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
            f"repository label sync failed: missing GitHub token in {token_env}",
            file=error_stream,
        )
        return 1

    try:
        labels = load_label_specs(labels_file)
        result = sync_repository_labels(
            GitHubRepositoryLabelsService(repository=repo, token=token),
            labels,
        )
    except (OSError, ValueError, json.JSONDecodeError, HTTPError, URLError) as exc:
        print(f"repository label sync failed: {exc}", file=error_stream)
        return 1

    changed: list[str] = []
    if result.created:
        changed.append("created " + ", ".join(result.created))
    if result.updated:
        changed.append("updated " + ", ".join(result.updated))
    if not changed:
        changed.append("unchanged")
    print("repository label sync: " + "; ".join(changed), file=output_stream)
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(
        repo=args.repo,
        labels_file=args.labels_file,
        token_env=args.token_env,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
