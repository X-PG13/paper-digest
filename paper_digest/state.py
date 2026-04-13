"""Persistent state for deduping already-seen papers and action notifications."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .arxiv_client import Paper
from .config import StateConfig


@dataclass(slots=True)
class DigestState:
    seen_papers: dict[str, dict[str, str]]
    action_notifications: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ActionNotificationRecord:
    canonical_id: str
    reason: str
    notified_at: datetime


def load_state(config: StateConfig) -> DigestState:
    """Load state from disk if enabled, otherwise return an empty state."""

    if not config.enabled or not config.path.exists():
        return DigestState(seen_papers={})

    raw = json.loads(config.path.read_text(encoding="utf-8"))
    feeds = raw.get("feeds", {})
    notifications = raw.get("action_notifications", {})
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
    normalized_notifications: dict[str, dict[str, str]] = {}
    if isinstance(notifications, dict):
        for canonical_id, reasons in notifications.items():
            if isinstance(canonical_id, str) and isinstance(reasons, dict):
                normalized_notifications[canonical_id] = {
                    reason: timestamp
                    for reason, timestamp in reasons.items()
                    if isinstance(reason, str) and isinstance(timestamp, str)
                }
    return DigestState(
        seen_papers=normalized,
        action_notifications=normalized_notifications,
    )


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
        paper_key = paper.canonical_id()
        if paper_key in seen_in_run or paper_key in seen_for_feed:
            continue
        seen_in_run.add(paper_key)
        seen_for_feed[paper_key] = seen_at
        new_papers.append(paper)

    return new_papers


def save_state(config: StateConfig, state: DigestState) -> None:
    """Persist the dedup state if enabled."""

    if not config.enabled:
        return

    config.path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 2,
        "feeds": state.seen_papers,
        "action_notifications": state.action_notifications,
    }
    config.path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_action_notifications(
    state: DigestState,
    *,
    canonical_id: str | None = None,
    reason: str | None = None,
    before_date: date | None = None,
) -> list[ActionNotificationRecord]:
    records: list[ActionNotificationRecord] = []
    for current_id, reasons in state.action_notifications.items():
        if canonical_id is not None and current_id != canonical_id:
            continue
        for current_reason, notified_at in reasons.items():
            if reason is not None and current_reason != reason:
                continue
            notified_at_dt = _parse_state_datetime(notified_at)
            if before_date is not None and notified_at_dt.date() >= before_date:
                continue
            records.append(
                ActionNotificationRecord(
                    canonical_id=current_id,
                    reason=current_reason,
                    notified_at=notified_at_dt,
                )
            )
    return sorted(
        records,
        key=lambda record: (
            -record.notified_at.timestamp(),
            record.canonical_id,
            record.reason,
        ),
    )


def clear_action_notifications(
    state: DigestState,
    *,
    canonical_id: str | None = None,
    reason: str | None = None,
    before_date: date | None = None,
) -> int:
    if canonical_id is None and reason is None and before_date is None:
        raise ValueError("canonical_id, reason, or before_date must be provided")

    matches = list_action_notifications(
        state,
        canonical_id=canonical_id,
        reason=reason,
        before_date=before_date,
    )
    for record in matches:
        reasons = state.action_notifications.get(record.canonical_id)
        if reasons is None:
            continue
        reasons.pop(record.reason, None)
        if not reasons:
            state.action_notifications.pop(record.canonical_id, None)
    return len(matches)


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
