from __future__ import annotations

import argparse
import sys
from pathlib import Path
from re import DOTALL, escape, subn

from tools.lifecycle_contracts import (
    GeneratedManagedBlock,
    iter_generated_lifecycle_blocks,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def replace_generated_block(
    text: str,
    block: GeneratedManagedBlock,
) -> tuple[str, bool]:
    begin = block.begin_marker
    end = block.end_marker
    pattern = f"{escape(begin)}.*?{escape(end)}"
    replacement = f"{begin}\n{block.content}\n{end}"
    updated_text, replacements = subn(pattern, replacement, text, count=1, flags=DOTALL)
    if replacements == 0:
        raise ValueError(
            f"{block.path}: missing generated block markers for '{block.marker}'"
        )
    return updated_text, updated_text != text


def sync_lifecycle_docs(
    root: Path,
    *,
    check: bool,
    blocks: tuple[GeneratedManagedBlock, ...] | None = None,
) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    blocks = iter_generated_lifecycle_blocks() if blocks is None else blocks
    blocks_by_path: dict[str, list[GeneratedManagedBlock]] = {}

    for block in blocks:
        blocks_by_path.setdefault(block.path, []).append(block)

    for relative_path, path_blocks in sorted(blocks_by_path.items()):
        path = root / relative_path
        if not path.exists():
            errors.append(f"{relative_path}: missing lifecycle doc file")
            continue

        original_text = path.read_text(encoding="utf-8")
        updated_text = original_text

        try:
            for block in path_blocks:
                updated_text, _ = replace_generated_block(updated_text, block)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if updated_text == original_text:
            continue
        if check:
            errors.append(
                f"{relative_path}: managed lifecycle blocks are out of date; "
                "run `python tools/sync_lifecycle_docs.py`"
            )
            continue
        path.write_text(updated_text, encoding="utf-8")

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Sync managed lifecycle blocks in docs, issue forms, and "
            "workflows from the repo-local contract schema."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if managed lifecycle blocks are stale.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    errors = sync_lifecycle_docs(REPO_ROOT, check=args.check)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.check:
        print("Managed lifecycle blocks are up to date.")
    else:
        print("Managed lifecycle blocks synced from tools/lifecycle_contracts.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
