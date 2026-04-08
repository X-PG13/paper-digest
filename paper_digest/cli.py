"""Command-line interface for Paper Digest."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .arxiv_client import ArxivClientError
from .config import ConfigError, load_config
from .digest import summarize_digest, write_outputs
from .service import generate_digest


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate a daily paper digest from arXiv.")
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to the TOML configuration file.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress success output.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = load_config(args.config)
        digest = generate_digest(config)
        json_path, markdown_path = write_outputs(config, digest)
    except (ConfigError, ArxivClientError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"JSON written to {Path(json_path).resolve()}")
        print(f"Markdown written to {Path(markdown_path).resolve()}")
        print(f"Matched papers: {summarize_digest(digest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
