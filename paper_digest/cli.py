"""Command-line interface for Paper Digest."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .analysis import AnalysisError
from .archive_site import ArchiveSiteError, build_archive_site
from .arxiv_client import ArxivClientError
from .config import ConfigError, load_config
from .crossref_client import CrossrefClientError
from .delivery import DeliveryError, send_configured_deliveries
from .digest import summarize_digest, write_outputs
from .feedback import load_feedback
from .openalex_client import OpenAlexClientError
from .pubmed_client import PubMedClientError
from .semantic_scholar_client import SemanticScholarClientError
from .service import generate_digest
from .state import load_state, save_state


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Generate a daily paper digest from supported literature sources."
    )
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
    json_path: Path | None = None
    markdown_path: Path | None = None
    site_path: Path | None = None

    try:
        config = load_config(args.config)
        state = load_state(config.state)
        feedback_state = load_feedback(config.feedback)
        digest = generate_digest(config, state=state, feedback_state=feedback_state)
        json_path, markdown_path = write_outputs(config, digest)
        site_path = build_archive_site(
            config.output_dir,
            tracked_keywords=_tracked_keywords(config),
            feedback_state=feedback_state,
        )
        delivery_receipts = send_configured_deliveries(config, digest)
        save_state(config.state, state)
    except DeliveryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if json_path is not None and markdown_path is not None:
            print(
                "Artifacts preserved at "
                f"{Path(json_path).resolve()} and {Path(markdown_path).resolve()}",
                file=sys.stderr,
            )
        return 1
    except (
        AnalysisError,
        ArchiveSiteError,
        ConfigError,
        ArxivClientError,
        CrossrefClientError,
        OpenAlexClientError,
        PubMedClientError,
        SemanticScholarClientError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"JSON written to {Path(json_path).resolve()}")
        print(f"Markdown written to {Path(markdown_path).resolve()}")
        print(f"Archive site written to {Path(site_path).resolve()}")
        print(f"Matched papers: {summarize_digest(digest)}")
        for receipt in delivery_receipts:
            print(receipt)
    return 0


def _tracked_keywords(config: object) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    feeds = getattr(config, "feeds", [])
    for feed in feeds:
        for keyword in getattr(feed, "keywords", []):
            stripped = keyword.strip()
            normalized = stripped.lower()
            if not stripped or normalized in seen:
                continue
            seen.add(normalized)
            keywords.append(stripped)
    return keywords


if __name__ == "__main__":
    raise SystemExit(main())
