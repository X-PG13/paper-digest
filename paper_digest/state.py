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


@dataclass(slots=True, frozen=True)
class ActionNotificationChange:
    canonical_id: str
    reason: str
    previous_notified_at: str | None
    next_notified_at: str | None


@dataclass(slots=True, frozen=True)
class ActionNotificationDiff:
    added: tuple[ActionNotificationChange, ...] = ()
    removed: tuple[ActionNotificationChange, ...] = ()
    updated: tuple[ActionNotificationChange, ...] = ()


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
    normalized_notifications = normalize_action_notifications(notifications)
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


def normalize_action_notifications(
    raw: object,
) -> dict[str, dict[str, str]]:
    normalized_notifications: dict[str, dict[str, str]] = {}
    if not isinstance(raw, dict):
        return normalized_notifications
    for canonical_id, reasons in raw.items():
        if isinstance(canonical_id, str) and isinstance(reasons, dict):
            normalized_reasons = {
                reason: timestamp
                for reason, timestamp in reasons.items()
                if isinstance(reason, str) and isinstance(timestamp, str)
            }
            if normalized_reasons:
                normalized_notifications[canonical_id] = normalized_reasons
    return normalized_notifications


def serialize_action_notifications(
    action_notifications: dict[str, dict[str, str]],
) -> str:
    payload = {
        "version": 1,
        "action_notifications": normalize_action_notifications(action_notifications),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_action_notifications_payload(
    payload: str,
) -> dict[str, dict[str, str]]:
    raw = json.loads(payload)
    if isinstance(raw, dict) and "action_notifications" in raw:
        return normalize_action_notifications(raw.get("action_notifications"))
    return normalize_action_notifications(raw)


def diff_action_notifications(
    previous: dict[str, dict[str, str]],
    current: dict[str, dict[str, str]],
) -> ActionNotificationDiff:
    previous_flat = _flatten_action_notifications(previous)
    current_flat = _flatten_action_notifications(current)
    added: list[ActionNotificationChange] = []
    removed: list[ActionNotificationChange] = []
    updated: list[ActionNotificationChange] = []

    for key in sorted(previous_flat.keys() | current_flat.keys()):
        previous_notified_at = previous_flat.get(key)
        current_notified_at = current_flat.get(key)
        if previous_notified_at is None and current_notified_at is not None:
            added.append(
                ActionNotificationChange(
                    canonical_id=key[0],
                    reason=key[1],
                    previous_notified_at=None,
                    next_notified_at=current_notified_at,
                )
            )
            continue
        if previous_notified_at is not None and current_notified_at is None:
            removed.append(
                ActionNotificationChange(
                    canonical_id=key[0],
                    reason=key[1],
                    previous_notified_at=previous_notified_at,
                    next_notified_at=None,
                )
            )
            continue
        if (
            previous_notified_at is not None
            and current_notified_at is not None
            and previous_notified_at != current_notified_at
        ):
            updated.append(
                ActionNotificationChange(
                    canonical_id=key[0],
                    reason=key[1],
                    previous_notified_at=previous_notified_at,
                    next_notified_at=current_notified_at,
                )
            )

    return ActionNotificationDiff(
        added=tuple(added),
        removed=tuple(removed),
        updated=tuple(updated),
    )


def summarize_action_notification_diff(diff: ActionNotificationDiff) -> str:
    return (
        f"added={len(diff.added)}, "
        f"updated={len(diff.updated)}, "
        f"removed={len(diff.removed)}"
    )


def render_action_notification_diff(
    diff: ActionNotificationDiff,
) -> list[str]:
    lines: list[str] = []
    for change in diff.added:
        lines.append(
            f"+\t{change.canonical_id}\t{change.reason}\t"
            f"{change.next_notified_at or ''}"
        )
    for change in diff.updated:
        lines.append(
            f"~\t{change.canonical_id}\t{change.reason}\t"
            f"{change.previous_notified_at or ''}\t->\t"
            f"{change.next_notified_at or ''}"
        )
    for change in diff.removed:
        lines.append(
            f"-\t{change.canonical_id}\t{change.reason}\t"
            f"{change.previous_notified_at or ''}"
        )
    return lines


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


def _flatten_action_notifications(
    action_notifications: dict[str, dict[str, str]],
) -> dict[tuple[str, str], str]:
    flattened: dict[tuple[str, str], str] = {}
    for canonical_id, reasons in normalize_action_notifications(
        action_notifications
    ).items():
        for reason, notified_at in reasons.items():
            flattened[(canonical_id, reason)] = notified_at
    return flattened
