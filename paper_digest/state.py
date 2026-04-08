"""Persistent state for deduping already-seen papers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from .arxiv_client import Paper
from .config import StateConfig


@dataclass(slots=True)
class DigestState:
    seen_papers: dict[str, dict[str, str]]


def load_state(config: StateConfig) -> DigestState:
    """Load state from disk if enabled, otherwise return an empty state."""

    if not config.enabled or not config.path.exists():
        return DigestState(seen_papers={})

    raw = json.loads(config.path.read_text(encoding="utf-8"))
    feeds = raw.get("feeds", {})
    if not isinstance(feeds, dict):
        return DigestState(seen_papers={})

    normalized: dict[str, dict[str, str]] = {}
    for feed_name, items in feeds.items():
        if isinstance(feed_name, str) and isinstance(items, dict):
            normalized[feed_name] = {
                paper_id: timestamp
                for paper_id, timestamp in items.items()
                if isinstance(paper_id, str) and isinstance(timestamp, str)
            }
    return DigestState(seen_papers=normalized)


def dedupe_papers(
    state: DigestState,
    *,
    feed_name: str,
    papers: list[Paper],
    now: datetime,
    retention_days: int,
) -> list[Paper]:
    """Drop previously seen papers and update state with the new ones."""

    seen_for_feed = state.seen_papers.setdefault(feed_name, {})
    cutoff = now - timedelta(days=retention_days)
    _prune_feed_state(seen_for_feed, cutoff)

    new_papers: list[Paper] = []
    seen_in_run: set[str] = set()
    seen_at = now.isoformat()

    for paper in papers:
        paper_id = paper.paper_id
        if paper_id in seen_in_run or paper_id in seen_for_feed:
            continue
        seen_in_run.add(paper_id)
        seen_for_feed[paper_id] = seen_at
        new_papers.append(paper)

    return new_papers


def save_state(config: StateConfig, state: DigestState) -> None:
    """Persist the dedup state if enabled."""

    if not config.enabled:
        return

    config.path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "feeds": state.seen_papers,
    }
    config.path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _prune_feed_state(feed_state: dict[str, str], cutoff: datetime) -> None:
    stale_keys = [
        paper_id
        for paper_id, seen_at in feed_state.items()
        if _parse_state_datetime(seen_at) < cutoff
    ]
    for paper_id in stale_keys:
        del feed_state[paper_id]


def _parse_state_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
