"""Historical archive backfill helpers."""

from __future__ import annotations

import json
import re
import shutil
from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .archive_site import ArchiveSiteError, build_archive_site
from .config import AppConfig, ConfigError, load_config

if TYPE_CHECKING:
    from collections.abc import Sequence

_DATE_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ArchiveBackfillError(RuntimeError):
    """Raised when historical archive backfill cannot complete."""


@dataclass(slots=True, frozen=True)
class DigestSnapshot:
    date: str
    day: Date
    generated_at: datetime
    total_papers: int
    feed_names: tuple[str, ...]
    source_dir: Path


@dataclass(slots=True, frozen=True)
class BackfillWindow:
    date_from: Date | None = None
    date_to: Date | None = None

    def includes(self, day: Date) -> bool:
        if self.date_from is not None and day < self.date_from:
            return False
        if self.date_to is not None and day > self.date_to:
            return False
        return True


@dataclass(slots=True, frozen=True)
class BackfillResult:
    imported_dates: list[str]
    replaced_dates: list[str]
    skipped_dates: list[str]
    scanned_snapshots: int


def backfill_archive_history(
    config: AppConfig,
    artifacts_dir: Path,
    *,
    window: BackfillWindow | None = None,
) -> BackfillResult:
    """Merge historical digest outputs into the configured output directory."""

    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tracked_keywords = _tracked_keywords(config)
    effective_window = window or BackfillWindow()

    current_by_date = _collect_snapshots(output_dir)
    selected_by_date = dict(current_by_date)
    skipped_dates: set[str] = set()
    scanned_snapshots = 0

    for digest_json_path in _iter_digest_json_paths(artifacts_dir):
        candidate = _load_snapshot(digest_json_path)
        scanned_snapshots += 1
        if _is_synthetic_snapshot(candidate):
            skipped_dates.add(candidate.date)
            continue
        if not effective_window.includes(candidate.day):
            continue

        current = selected_by_date.get(candidate.date)
        if current is None or _snapshot_rank(candidate) > _snapshot_rank(current):
            selected_by_date[candidate.date] = candidate

    imported_dates: list[str] = []
    replaced_dates: list[str] = []
    for date_str, candidate in sorted(selected_by_date.items()):
        current = current_by_date.get(date_str)
        if current is not None and _snapshot_rank(candidate) == _snapshot_rank(current):
            continue
        _copy_snapshot(candidate, output_dir / date_str)
        if current is None:
            imported_dates.append(date_str)
        else:
            replaced_dates.append(date_str)

    _refresh_latest_files(output_dir)
    build_archive_site(output_dir, tracked_keywords=tracked_keywords)

    return BackfillResult(
        imported_dates=imported_dates,
        replaced_dates=replaced_dates,
        skipped_dates=sorted(skipped_dates),
        scanned_snapshots=scanned_snapshots,
    )


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Backfill historical archive outputs.")
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to the TOML configuration file.",
    )
    parser.add_argument(
        "--artifacts-dir",
        required=True,
        help="Directory containing downloaded workflow artifacts.",
    )
    parser.add_argument(
        "--date-from",
        help="Optional earliest digest date to import (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--date-to",
        help="Optional latest digest date to import (YYYY-MM-DD).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        window = BackfillWindow(
            date_from=_parse_filter_date(args.date_from, "--date-from"),
            date_to=_parse_filter_date(args.date_to, "--date-to"),
        )
        if (
            window.date_from is not None
            and window.date_to is not None
            and window.date_from > window.date_to
        ):
            raise ArchiveBackfillError("--date-from cannot be after --date-to")
        result = backfill_archive_history(
            config,
            Path(args.artifacts_dir),
            window=window,
        )
    except (ArchiveBackfillError, ArchiveSiteError, ConfigError) as exc:
        print(f"Error: {exc}")
        return 1

    print(
        "Backfill complete: "
        f"imported={len(result.imported_dates)}, "
        f"replaced={len(result.replaced_dates)}, "
        f"skipped={len(result.skipped_dates)}, "
        f"scanned={result.scanned_snapshots}"
    )
    if result.imported_dates:
        print("Imported dates: " + ", ".join(result.imported_dates))
    if result.replaced_dates:
        print("Replaced dates: " + ", ".join(result.replaced_dates))
    if result.skipped_dates:
        print("Skipped dates: " + ", ".join(result.skipped_dates))
    return 0


def _collect_snapshots(root: Path) -> dict[str, DigestSnapshot]:
    snapshots: dict[str, DigestSnapshot] = {}
    for digest_json_path in _iter_digest_json_paths(root):
        snapshot = _load_snapshot(digest_json_path)
        current = snapshots.get(snapshot.date)
        if current is None or _snapshot_rank(snapshot) > _snapshot_rank(current):
            snapshots[snapshot.date] = snapshot
    return snapshots


def _iter_digest_json_paths(root: Path) -> list[Path]:
    return [
        path
        for path in root.glob("**/digest.json")
        if "site" not in path.parts and _DATE_DIR_PATTERN.match(path.parent.name)
    ]


def _load_snapshot(digest_json_path: Path) -> DigestSnapshot:
    markdown_path = digest_json_path.with_name("digest.md")
    if not markdown_path.exists():
        raise ArchiveBackfillError(f"missing digest markdown: {markdown_path}")

    try:
        payload = json.loads(digest_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArchiveBackfillError(
            f"invalid digest JSON: {digest_json_path}"
        ) from exc

    if not isinstance(payload, dict):
        raise ArchiveBackfillError(f"invalid digest payload: {digest_json_path}")

    raw_generated_at = payload.get("generated_at")
    if not isinstance(raw_generated_at, str):
        raise ArchiveBackfillError(f"invalid generated_at in {digest_json_path}")

    try:
        generated_at = datetime.fromisoformat(raw_generated_at)
    except ValueError as exc:
        raise ArchiveBackfillError(
            f"invalid generated_at in {digest_json_path}"
        ) from exc
    if generated_at.tzinfo is None:
        raise ArchiveBackfillError(f"naive generated_at in {digest_json_path}")

    raw_feeds = payload.get("feeds")
    if not isinstance(raw_feeds, list):
        raise ArchiveBackfillError(f"invalid feeds in {digest_json_path}")

    feed_names: list[str] = []
    total_papers = 0
    for raw_feed in raw_feeds:
        if not isinstance(raw_feed, dict):
            continue
        name = raw_feed.get("name")
        if isinstance(name, str) and name.strip():
            feed_names.append(name.strip())
        papers = raw_feed.get("papers")
        if isinstance(papers, list):
            total_papers += len(papers)

    return DigestSnapshot(
        date=digest_json_path.parent.name,
        day=Date.fromisoformat(digest_json_path.parent.name),
        generated_at=generated_at,
        total_papers=total_papers,
        feed_names=tuple(feed_names),
        source_dir=digest_json_path.parent,
    )


def _snapshot_rank(snapshot: DigestSnapshot) -> tuple[int, int, datetime]:
    return (snapshot.total_papers, len(snapshot.feed_names), snapshot.generated_at)


def _is_synthetic_snapshot(snapshot: DigestSnapshot) -> bool:
    return any(
        "delivery check" in feed_name.lower() for feed_name in snapshot.feed_names
    )


def _copy_snapshot(snapshot: DigestSnapshot, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("digest.json", "digest.md"):
        shutil.copyfile(snapshot.source_dir / filename, target_dir / filename)


def _refresh_latest_files(output_dir: Path) -> None:
    snapshots = _collect_snapshots(output_dir)
    if not snapshots:
        return
    latest = max(snapshots.values(), key=lambda item: item.generated_at)
    shutil.copyfile(latest.source_dir / "digest.json", output_dir / "latest.json")
    shutil.copyfile(latest.source_dir / "digest.md", output_dir / "latest.md")


def _tracked_keywords(config: AppConfig) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for feed in config.feeds:
        for keyword in feed.keywords:
            stripped = keyword.strip()
            normalized = stripped.lower()
            if not stripped or normalized in seen:
                continue
            seen.add(normalized)
            keywords.append(stripped)
    return keywords


def _parse_filter_date(value: str | None, flag: str) -> Date | None:
    if value is None or not value.strip():
        return None
    try:
        return Date.fromisoformat(value)
    except ValueError as exc:
        raise ArchiveBackfillError(f"invalid {flag} value: {value}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
