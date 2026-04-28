from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from tools.install_actionlint import DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH

ACTIONLINT_MISSING_EXIT_CODE = 127


def _resolve_candidate_path(candidate: str, root: Path) -> Path:
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def find_actionlint_binary(
    root: Path,
    *,
    configured_path: str | None = None,
) -> Path | None:
    if configured_path:
        configured_binary = _resolve_candidate_path(configured_path, root)
        if _is_executable_file(configured_binary):
            return configured_binary

    env_binary = os.environ.get("ACTIONLINT_BIN")
    if env_binary:
        resolved_env_binary = _resolve_candidate_path(env_binary, root)
        if _is_executable_file(resolved_env_binary):
            return resolved_env_binary

    repo_local_binary = root / DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH
    if _is_executable_file(repo_local_binary):
        return repo_local_binary

    discovered_binary = shutil.which("actionlint")
    if discovered_binary:
        return Path(discovered_binary)
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local GitHub workflow linting through actionlint."
    )
    parser.add_argument(
        "--actionlint-bin",
        help=(
            "Override actionlint discovery with an explicit binary path. "
            "Relative paths are resolved from the repository root."
        ),
    )
    return parser


def main(
    *,
    root: Path | None = None,
    actionlint_bin: str | None = None,
    stderr: TextIO | None = None,
) -> int:
    error_stream = sys.stderr if stderr is None else stderr
    repo_root = Path(__file__).resolve().parents[1] if root is None else root.resolve()
    binary = find_actionlint_binary(repo_root, configured_path=actionlint_bin)
    if binary is None:
        print(
            "actionlint not found. Install it in PATH, set ACTIONLINT_BIN, or place "
            "the binary at "
            f"{DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH}. "
            "To install the pinned repo-local copy, run `make workflow-tools`.",
            file=error_stream,
        )
        return ACTIONLINT_MISSING_EXIT_CODE

    completed = subprocess.run(
        [str(binary)],
        cwd=repo_root,
        check=False,
    )
    return completed.returncode


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(actionlint_bin=args.actionlint_bin)


if __name__ == "__main__":
    raise SystemExit(cli())
