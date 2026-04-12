"""Command-line interface for Paper Digest."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from . import __version__
from .analysis import AnalysisError
from .archive_site import ArchiveSiteError, build_archive_site
from .arxiv_client import ArxivClientError
from .config import ConfigError, load_config
from .crossref_client import CrossrefClientError
from .delivery import DeliveryError, send_configured_deliveries
from .digest import summarize_digest, write_outputs
from .feedback import (
    clear_feedback_action,
    clear_feedback_due_date,
    clear_feedback_note,
    clear_feedback_status,
    list_feedback_entries,
    load_feedback,
    load_feedback_file,
    save_feedback,
    set_feedback_action,
    set_feedback_due_date,
    set_feedback_note,
    set_feedback_status,
)
from .openalex_client import OpenAlexClientError
from .pubmed_client import PubMedClientError
from .semantic_scholar_client import SemanticScholarClientError
from .service import generate_digest
from .state import load_state, save_state


def build_parser() -> ArgumentParser:
    return build_digest_parser()


def build_digest_parser() -> ArgumentParser:
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


def build_feedback_parser() -> ArgumentParser:
    common = ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        default="config.toml",
        help="Path to the TOML configuration file.",
    )
    parser = ArgumentParser(
        description="Manage local paper feedback state keyed by canonical_id.",
        parents=[common],
    )
    subparsers = parser.add_subparsers(dest="feedback_command", required=True)

    set_parser = subparsers.add_parser(
        "set",
        help="Set a feedback status.",
        parents=[common],
    )
    set_parser.add_argument("canonical_id", help="Canonical paper identifier.")
    set_parser.add_argument(
        "status",
        choices=["star", "follow_up", "reading", "done", "ignore"],
        help="Feedback status to store.",
    )
    set_parser.add_argument(
        "--note",
        help="Optional personal note to store with this feedback entry.",
    )

    clear_parser = subparsers.add_parser(
        "clear",
        help="Remove a feedback status.",
        parents=[common],
    )
    clear_parser.add_argument("canonical_id", help="Canonical paper identifier.")

    note_parser = subparsers.add_parser(
        "note",
        help="Set or update the note for an existing feedback entry.",
        parents=[common],
    )
    note_parser.add_argument("canonical_id", help="Canonical paper identifier.")
    note_parser.add_argument("note", help="Personal note text.")

    clear_note_parser = subparsers.add_parser(
        "clear-note",
        help="Clear the note for an existing feedback entry.",
        parents=[common],
    )
    clear_note_parser.add_argument("canonical_id", help="Canonical paper identifier.")

    action_parser = subparsers.add_parser(
        "action",
        help="Set or clear the next action for an existing feedback entry.",
        parents=[common],
    )
    action_subparsers = action_parser.add_subparsers(
        dest="feedback_action_command",
        required=True,
    )
    action_set_parser = action_subparsers.add_parser(
        "set",
        help="Store the next action for an existing feedback entry.",
        parents=[common],
    )
    action_set_parser.add_argument(
        "canonical_id",
        help="Canonical paper identifier.",
    )
    action_set_parser.add_argument(
        "next_action",
        help="Next action text.",
    )
    action_clear_parser = action_subparsers.add_parser(
        "clear",
        help="Clear the next action for an existing feedback entry.",
        parents=[common],
    )
    action_clear_parser.add_argument(
        "canonical_id",
        help="Canonical paper identifier.",
    )

    due_parser = subparsers.add_parser(
        "due",
        help="Set or clear the due date for an existing feedback entry.",
        parents=[common],
    )
    due_subparsers = due_parser.add_subparsers(
        dest="feedback_due_command",
        required=True,
    )
    due_set_parser = due_subparsers.add_parser(
        "set",
        help="Store the due date for an existing feedback entry.",
        parents=[common],
    )
    due_set_parser.add_argument(
        "canonical_id",
        help="Canonical paper identifier.",
    )
    due_set_parser.add_argument(
        "due_date",
        help="Due date in YYYY-MM-DD format.",
    )
    due_clear_parser = due_subparsers.add_parser(
        "clear",
        help="Clear the due date for an existing feedback entry.",
        parents=[common],
    )
    due_clear_parser.add_argument(
        "canonical_id",
        help="Canonical paper identifier.",
    )

    subparsers.add_parser(
        "list",
        help="List configured feedback entries.",
        parents=[common],
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    if args_list and args_list[0] == "feedback":
        return _main_feedback(args_list[1:])
    return _main_digest(args_list)


def _main_digest(argv: Sequence[str]) -> int:
    args = build_digest_parser().parse_args(argv)
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


def _main_feedback(argv: Sequence[str]) -> int:
    args = build_feedback_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        feedback_state = load_feedback_file(config.feedback.path)
        feedback_path = Path(config.feedback.path).resolve()
        if args.feedback_command == "set":
            entry = set_feedback_status(
                feedback_state,
                canonical_id=args.canonical_id,
                status=args.status,
                note=args.note,
            )
            save_feedback(config.feedback, feedback_state)
            updated_at = (
                entry.updated_at.isoformat() if entry.updated_at is not None else "n/a"
            )
            note_suffix = (
                f" with note {entry.note!r}"
                if entry.note is not None
                else ""
            )
            print(
                f"Set {args.canonical_id.strip()} -> {entry.status} "
                f"at {updated_at}{note_suffix} in {feedback_path}"
            )
            return 0
        if args.feedback_command == "clear":
            removed = clear_feedback_status(
                feedback_state,
                canonical_id=args.canonical_id,
            )
            save_feedback(config.feedback, feedback_state)
            if removed:
                print(f"Cleared {args.canonical_id.strip()} from {feedback_path}")
            else:
                print(f"No entry for {args.canonical_id.strip()} in {feedback_path}")
            return 0
        if args.feedback_command == "note":
            note_entry = set_feedback_note(
                feedback_state,
                canonical_id=args.canonical_id,
                note=args.note,
            )
            if note_entry is None:
                print(
                    f"No entry for {args.canonical_id.strip()} in {feedback_path}",
                    file=sys.stderr,
                )
                return 1
            save_feedback(config.feedback, feedback_state)
            print(
                f"Updated note for {args.canonical_id.strip()} in {feedback_path}"
            )
            return 0
        if args.feedback_command == "clear-note":
            removed = clear_feedback_note(
                feedback_state,
                canonical_id=args.canonical_id,
            )
            save_feedback(config.feedback, feedback_state)
            if removed:
                print(
                    f"Cleared note for {args.canonical_id.strip()} in {feedback_path}"
                )
            else:
                print(
                    f"No note for {args.canonical_id.strip()} in {feedback_path}"
                )
            return 0
        if args.feedback_command == "action":
            if args.feedback_action_command == "set":
                action_entry = set_feedback_action(
                    feedback_state,
                    canonical_id=args.canonical_id,
                    next_action=args.next_action,
                )
                if action_entry is None:
                    print(
                        f"No entry for {args.canonical_id.strip()} in {feedback_path}",
                        file=sys.stderr,
                    )
                    return 1
                save_feedback(config.feedback, feedback_state)
                print(
                    "Updated next action for "
                    f"{args.canonical_id.strip()} in {feedback_path}"
                )
                return 0
            removed = clear_feedback_action(
                feedback_state,
                canonical_id=args.canonical_id,
            )
            save_feedback(config.feedback, feedback_state)
            if removed:
                print(
                    "Cleared next action for "
                    f"{args.canonical_id.strip()} in {feedback_path}"
                )
            else:
                print(
                    f"No next action for {args.canonical_id.strip()} in {feedback_path}"
                )
            return 0
        if args.feedback_command == "due":
            if args.feedback_due_command == "set":
                try:
                    due_date = date.fromisoformat(args.due_date)
                except ValueError:
                    print(
                        "Error: due_date must use YYYY-MM-DD format",
                        file=sys.stderr,
                    )
                    return 1
                due_entry = set_feedback_due_date(
                    feedback_state,
                    canonical_id=args.canonical_id,
                    due_date=due_date,
                )
                if due_entry is None:
                    print(
                        f"No entry for {args.canonical_id.strip()} in {feedback_path}",
                        file=sys.stderr,
                    )
                    return 1
                save_feedback(config.feedback, feedback_state)
                print(
                    "Updated due date for "
                    f"{args.canonical_id.strip()} -> {due_date.isoformat()} "
                    f"in {feedback_path}"
                )
                return 0
            removed = clear_feedback_due_date(
                feedback_state,
                canonical_id=args.canonical_id,
            )
            save_feedback(config.feedback, feedback_state)
            if removed:
                print(
                    "Cleared due date for "
                    f"{args.canonical_id.strip()} in {feedback_path}"
                )
            else:
                print(
                    f"No due date for {args.canonical_id.strip()} in {feedback_path}"
                )
            return 0

        entries = list_feedback_entries(feedback_state)
        if not entries:
            print(f"No feedback entries found in {feedback_path}")
            return 0
        for canonical_id, entry in entries:
            updated_at = (
                entry.updated_at.isoformat()
                if entry.updated_at is not None
                else "n/a"
            )
            due_date_label = (
                entry.due_date.isoformat() if entry.due_date is not None else ""
            )
            next_action = entry.next_action or ""
            note = entry.note or ""
            print(
                f"{entry.status}\t{canonical_id}\t{updated_at}\t"
                f"{due_date_label}\t{next_action}\t{note}"
            )
        return 0
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


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
