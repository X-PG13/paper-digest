"""Command-line interface for Paper Digest."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import cast

from . import __version__
from .analysis import AnalysisError
from .archive_site import ArchiveSiteError, build_archive_site
from .arxiv_client import ArxivClientError
from .config import ConfigError, load_config
from .crossref_client import CrossrefClientError
from .delivery import DeliveryError, send_configured_deliveries
from .digest import summarize_digest, write_outputs
from .feedback import (
    FeedbackMergeStrategy,
    FeedbackStateDiff,
    clear_feedback_action,
    clear_feedback_due_date,
    clear_feedback_note,
    clear_feedback_review_interval_days,
    clear_feedback_snoozed_until,
    clear_feedback_status,
    diff_feedback_states,
    list_feedback_entries,
    load_feedback,
    load_feedback_file,
    merge_feedback_states,
    normalize_feedback_canonical_id,
    render_feedback_diff,
    save_feedback,
    set_feedback_action,
    set_feedback_due_date,
    set_feedback_note,
    set_feedback_review_interval_days,
    set_feedback_snoozed_until,
    set_feedback_status,
    summarize_feedback_diff,
)
from .github_feedback import (
    DEFAULT_FEEDBACK_SECRET_NAME,
    GitHubFeedbackSyncError,
    pull_feedback_from_github_secret,
    sync_feedback_to_github_secret,
)
from .openalex_client import OpenAlexClientError
from .pubmed_client import PubMedClientError
from .semantic_scholar_client import SemanticScholarClientError
from .service import generate_digest
from .state import (
    clear_action_notifications,
    list_action_notifications,
    load_state,
    save_state,
)


def build_parser() -> ArgumentParser:
    return build_digest_parser()


def build_state_parser() -> ArgumentParser:
    common = ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        default="config.toml",
        help="Path to the TOML configuration file.",
    )
    parser = ArgumentParser(
        description="Inspect or reset local persistent digest state.",
        parents=[common],
    )
    subparsers = parser.add_subparsers(dest="state_command", required=True)

    action_parser = subparsers.add_parser(
        "action",
        help="Inspect or reset action notification state.",
        parents=[common],
    )
    action_subparsers = action_parser.add_subparsers(
        dest="state_action_command",
        required=True,
    )

    action_list_parser = action_subparsers.add_parser(
        "list",
        help="List remembered action notifications.",
        parents=[common],
    )
    action_list_parser.add_argument(
        "--canonical-id",
        help="Optional canonical paper identifier filter.",
    )

    action_reset_parser = action_subparsers.add_parser(
        "reset",
        help="Reset remembered action notifications.",
        parents=[common],
    )
    action_reset_parser.add_argument(
        "canonical_id",
        nargs="?",
        help="Optional canonical paper identifier to reset.",
    )
    action_reset_parser.add_argument(
        "--reason",
        help="Optional action reason to reset, such as overdue_3d.",
    )
    return parser


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

    snooze_parser = subparsers.add_parser(
        "snooze",
        help="Set or clear the snoozed-until date for an existing feedback entry.",
        parents=[common],
    )
    snooze_subparsers = snooze_parser.add_subparsers(
        dest="feedback_snooze_command",
        required=True,
    )
    snooze_set_parser = snooze_subparsers.add_parser(
        "set",
        help="Store the snoozed-until date for an existing feedback entry.",
        parents=[common],
    )
    snooze_set_parser.add_argument(
        "canonical_id",
        help="Canonical paper identifier.",
    )
    snooze_set_parser.add_argument(
        "snoozed_until",
        help="Date in YYYY-MM-DD format.",
    )
    snooze_clear_parser = snooze_subparsers.add_parser(
        "clear",
        help="Clear the snoozed-until date for an existing feedback entry.",
        parents=[common],
    )
    snooze_clear_parser.add_argument(
        "canonical_id",
        help="Canonical paper identifier.",
    )

    interval_parser = subparsers.add_parser(
        "interval",
        help=(
            "Set or clear the recurring review interval for an existing "
            "feedback entry."
        ),
        parents=[common],
    )
    interval_subparsers = interval_parser.add_subparsers(
        dest="feedback_interval_command",
        required=True,
    )
    interval_set_parser = interval_subparsers.add_parser(
        "set",
        help="Store the recurring review interval in days.",
        parents=[common],
    )
    interval_set_parser.add_argument(
        "canonical_id",
        help="Canonical paper identifier.",
    )
    interval_set_parser.add_argument(
        "review_interval_days",
        help="Recurring review interval in days.",
    )
    interval_clear_parser = interval_subparsers.add_parser(
        "clear",
        help="Clear the recurring review interval for an existing feedback entry.",
        parents=[common],
    )
    interval_clear_parser.add_argument(
        "canonical_id",
        help="Canonical paper identifier.",
    )

    subparsers.add_parser(
        "list",
        help="List configured feedback entries.",
        parents=[common],
    )
    sync_common = ArgumentParser(add_help=False)
    sync_common.add_argument(
        "--repo",
        help="Optional owner/repo override. Defaults to the current git origin remote.",
    )
    sync_common.add_argument(
        "--secret-name",
        default=DEFAULT_FEEDBACK_SECRET_NAME,
        help="GitHub Actions secret name to sync.",
    )
    sync_parser = subparsers.add_parser(
        "sync",
        help="Push or pull feedback state through a GitHub Actions repository secret.",
        parents=[common, sync_common],
    )
    sync_parser.add_argument(
        "--direction",
        choices=["push", "pull"],
        default="push",
        help="Sync direction. Push writes the local file; pull restores it locally.",
    )
    sync_parser.add_argument(
        "--merge-strategy",
        choices=["local", "remote", "newer"],
        default="newer",
        help="Conflict resolution for pull. Ignored for push.",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the sync result without writing the local file or GitHub secret.",
    )
    sync_parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Print a field-level diff for the sync result before writing.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    if args_list and args_list[0] == "feedback":
        return _main_feedback(args_list[1:])
    if args_list and args_list[0] == "state":
        return _main_state(args_list[1:])
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
            digest_state=state,
        )
        delivery_receipts = send_configured_deliveries(config, digest)
        save_feedback(config.feedback, feedback_state)
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
        if args.feedback_command == "snooze":
            if args.feedback_snooze_command == "set":
                try:
                    snoozed_until = date.fromisoformat(args.snoozed_until)
                except ValueError:
                    print(
                        "Error: snoozed_until must use YYYY-MM-DD format",
                        file=sys.stderr,
                    )
                    return 1
                snooze_entry = set_feedback_snoozed_until(
                    feedback_state,
                    canonical_id=args.canonical_id,
                    snoozed_until=snoozed_until,
                )
                if snooze_entry is None:
                    print(
                        f"No entry for {args.canonical_id.strip()} in {feedback_path}",
                        file=sys.stderr,
                    )
                    return 1
                save_feedback(config.feedback, feedback_state)
                print(
                    "Updated snoozed-until for "
                    f"{args.canonical_id.strip()} -> {snoozed_until.isoformat()} "
                    f"in {feedback_path}"
                )
                return 0
            removed = clear_feedback_snoozed_until(
                feedback_state,
                canonical_id=args.canonical_id,
            )
            save_feedback(config.feedback, feedback_state)
            if removed:
                print(
                    "Cleared snoozed-until for "
                    f"{args.canonical_id.strip()} in {feedback_path}"
                )
            else:
                print(
                    "No snoozed-until for "
                    f"{args.canonical_id.strip()} in {feedback_path}"
                )
            return 0
        if args.feedback_command == "interval":
            if args.feedback_interval_command == "set":
                try:
                    review_interval_days = int(args.review_interval_days)
                except ValueError:
                    print(
                        "Error: review_interval_days must be a positive integer",
                        file=sys.stderr,
                    )
                    return 1
                if review_interval_days <= 0:
                    print(
                        "Error: review_interval_days must be a positive integer",
                        file=sys.stderr,
                    )
                    return 1
                interval_entry = set_feedback_review_interval_days(
                    feedback_state,
                    canonical_id=args.canonical_id,
                    review_interval_days=review_interval_days,
                )
                if interval_entry is None:
                    print(
                        f"No entry for {args.canonical_id.strip()} in {feedback_path}",
                        file=sys.stderr,
                    )
                    return 1
                save_feedback(config.feedback, feedback_state)
                print(
                    "Updated review interval for "
                    f"{args.canonical_id.strip()} -> {review_interval_days} days "
                    f"in {feedback_path}"
                )
                return 0
            removed = clear_feedback_review_interval_days(
                feedback_state,
                canonical_id=args.canonical_id,
            )
            save_feedback(config.feedback, feedback_state)
            if removed:
                print(
                    "Cleared review interval for "
                    f"{args.canonical_id.strip()} in {feedback_path}"
                )
            else:
                print(
                    "No review interval for "
                    f"{args.canonical_id.strip()} in {feedback_path}"
                )
            return 0
        if args.feedback_command == "sync":
            direction = str(args.direction)
            sync_cwd = Path(args.config).resolve().parent
            preview_requested = bool(args.dry_run or args.show_diff)
            if direction == "push":
                remote_snapshot = None
                if preview_requested:
                    try:
                        remote_snapshot = pull_feedback_from_github_secret(
                            cwd=sync_cwd,
                            repo=args.repo,
                            secret_name=args.secret_name,
                        )
                    except GitHubFeedbackSyncError as exc:
                        if args.dry_run:
                            print(f"Error: {exc}", file=sys.stderr)
                            return 1
                        print(
                            "Warning: could not fetch remote feedback preview: "
                            f"{exc}",
                            file=sys.stderr,
                        )
                if remote_snapshot is not None:
                    diff = diff_feedback_states(
                        remote_snapshot.feedback_state,
                        feedback_state,
                    )
                    _print_feedback_sync_preview(
                        direction="push",
                        feedback_path=feedback_path,
                        secret_name=args.secret_name,
                        repository=remote_snapshot.repository,
                        diff=diff,
                        show_diff=bool(args.show_diff),
                        merge_strategy=None,
                        run_id=remote_snapshot.run_id,
                        dry_run=bool(args.dry_run),
                    )
                    if args.dry_run:
                        return 0
                elif args.dry_run:
                    return 1

                repo = sync_feedback_to_github_secret(
                    feedback_state,
                    cwd=sync_cwd,
                    repo=args.repo,
                    secret_name=args.secret_name,
                )
                print(
                    f"Synced {feedback_path} to GitHub Actions secret "
                    f"{args.secret_name} for {repo}"
                )
                return 0
            pull_result = pull_feedback_from_github_secret(
                cwd=sync_cwd,
                repo=args.repo,
                secret_name=args.secret_name,
            )
            merge_strategy = cast(
                FeedbackMergeStrategy,
                args.merge_strategy,
            )
            merged_feedback = merge_feedback_states(
                feedback_state,
                pull_result.feedback_state,
                strategy=merge_strategy,
            )
            diff = diff_feedback_states(feedback_state, merged_feedback)
            if preview_requested:
                _print_feedback_sync_preview(
                    direction="pull",
                    feedback_path=feedback_path,
                    secret_name=args.secret_name,
                    repository=pull_result.repository,
                    diff=diff,
                    show_diff=bool(args.show_diff),
                    merge_strategy=merge_strategy,
                    run_id=pull_result.run_id,
                    dry_run=bool(args.dry_run),
                )
                if args.dry_run:
                    return 0
            save_feedback(config.feedback, merged_feedback)
            print(
                f"Pulled GitHub Actions secret {args.secret_name} for "
                f"{pull_result.repository} into {feedback_path} "
                f"(run {pull_result.run_id}, merge={merge_strategy})"
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
            snoozed_until_label = (
                entry.snoozed_until.isoformat()
                if entry.snoozed_until is not None
                else ""
            )
            review_interval_label = (
                str(entry.review_interval_days)
                if entry.review_interval_days is not None
                else ""
            )
            next_action = entry.next_action or ""
            note = entry.note or ""
            print(
                f"{entry.status}\t{canonical_id}\t{updated_at}\t"
                f"{due_date_label}\t{snoozed_until_label}\t"
                f"{review_interval_label}\t{next_action}\t{note}"
            )
        return 0
    except (ConfigError, GitHubFeedbackSyncError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _main_state(argv: Sequence[str]) -> int:
    args = build_state_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        state = load_state(config.state)
        state_path = Path(config.state.path).resolve()
        if args.state_command == "action":
            if args.state_action_command == "list":
                canonical_id = (
                    normalize_feedback_canonical_id(args.canonical_id)
                    if args.canonical_id
                    else None
                )
                records = list_action_notifications(
                    state,
                    canonical_id=canonical_id,
                )
                if not records:
                    print(
                        f"No action notification entries found in {state_path}"
                    )
                    return 0
                for record in records:
                    print(
                        f"{record.canonical_id}\t{record.reason}\t"
                        f"{record.notified_at.isoformat()}"
                    )
                return 0

            canonical_id = (
                normalize_feedback_canonical_id(args.canonical_id)
                if args.canonical_id
                else None
            )
            if canonical_id is None and args.reason is None:
                print(
                    "Error: provide a canonical_id and/or --reason for reset",
                    file=sys.stderr,
                )
                return 1
            cleared = clear_action_notifications(
                state,
                canonical_id=canonical_id,
                reason=args.reason,
            )
            save_state(config.state, state)
            if cleared:
                target = canonical_id or "all matching entries"
                reason_suffix = (
                    f" with reason {args.reason}"
                    if args.reason is not None
                    else ""
                )
                print(
                    f"Cleared {cleared} action notification entr"
                    f"{'y' if cleared == 1 else 'ies'} for {target}"
                    f"{reason_suffix} in {state_path}"
                )
            else:
                print(f"No matching action notification entries in {state_path}")
            return 0
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def _print_feedback_sync_preview(
    *,
    direction: str,
    feedback_path: Path,
    secret_name: str,
    repository: str,
    diff: FeedbackStateDiff,
    show_diff: bool,
    merge_strategy: FeedbackMergeStrategy | None,
    run_id: str | None,
    dry_run: bool,
) -> None:
    prefix = "Dry run" if dry_run else "Preview"
    if direction == "push":
        run_label = f" (remote run {run_id})" if run_id else ""
        print(
            f"{prefix}: would sync {feedback_path} to GitHub Actions secret "
            f"{secret_name} for {repository}{run_label}"
        )
    else:
        merge_label = f", merge={merge_strategy}" if merge_strategy is not None else ""
        run_label = f" (run {run_id}{merge_label})" if run_id is not None else ""
        print(
            f"{prefix}: would pull GitHub Actions secret {secret_name} for "
            f"{repository} into {feedback_path}{run_label}"
        )
    print(f"Diff summary: {summarize_feedback_diff(diff)}")
    if show_diff:
        for line in render_feedback_diff(diff):
            print(line)


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
