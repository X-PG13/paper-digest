"""User feedback state for paper prioritization and reading lists."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

from .arxiv_client import Paper
from .config import FeedbackConfig, FeedbackStatus

FeedbackMergeStrategy = Literal["local", "remote", "newer"]


@dataclass(slots=True, frozen=True)
class FeedbackEntry:
    status: FeedbackStatus
    updated_at: datetime | None = None
    note: str | None = None
    next_action: str | None = None
    due_date: date | None = None
    snoozed_until: date | None = None
    review_interval_days: int | None = None


@dataclass(slots=True)
class FeedbackState:
    papers: dict[str, FeedbackEntry]


@dataclass(slots=True, frozen=True)
class FeedbackAutomation:
    resumed_from_snooze: frozenset[str]
    recurring_due: frozenset[str]
    changed: bool = False


def load_feedback(config: FeedbackConfig) -> FeedbackState:
    """Load feedback state from disk if enabled, otherwise return an empty map."""

    if not config.enabled:
        return FeedbackState(papers={})
    return load_feedback_file(config.path)


def load_feedback_file(path: object) -> FeedbackState:
    feedback_path = _coerce_feedback_path(path)
    if not feedback_path.exists():
        return FeedbackState(papers={})

    raw = json.loads(feedback_path.read_text(encoding="utf-8"))
    papers = raw.get("papers", {})
    if not isinstance(papers, dict):
        return FeedbackState(papers={})

    normalized: dict[str, FeedbackEntry] = {}
    for canonical_id, value in papers.items():
        if not isinstance(canonical_id, str) or not canonical_id.strip():
            continue
        entry = _parse_feedback_entry(value)
        if entry is None:
            continue
        normalized[canonical_id.strip()] = entry
    return FeedbackState(papers=normalized)


def save_feedback(config: FeedbackConfig, feedback_state: FeedbackState) -> None:
    save_feedback_file(config.path, feedback_state)


def save_feedback_file(path: object, feedback_state: FeedbackState) -> None:
    feedback_path = _coerce_feedback_path(path)
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(
        serialize_feedback_state(feedback_state),
        encoding="utf-8",
    )


def serialize_feedback_state(feedback_state: FeedbackState) -> str:
    papers = {
        canonical_id: _serialize_feedback_entry(entry)
        for canonical_id, entry in sorted(feedback_state.papers.items())
    }
    payload = {
        "version": 1,
        "papers": papers,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def set_feedback_status(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    status: FeedbackStatus,
    updated_at: datetime | None = None,
    note: str | None = None,
) -> FeedbackEntry:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    normalized_note = (
        existing.note
        if note is None and existing is not None
        else _normalize_note(note)
    )
    entry = FeedbackEntry(
        status=status,
        updated_at=updated_at or datetime.now(UTC),
        note=normalized_note,
        next_action=existing.next_action if existing is not None else None,
        due_date=existing.due_date if existing is not None else None,
        snoozed_until=existing.snoozed_until if existing is not None else None,
        review_interval_days=(
            existing.review_interval_days if existing is not None else None
        ),
    )
    feedback_state.papers[normalized_id] = entry
    return entry


def set_feedback_note(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    note: str,
    updated_at: datetime | None = None,
) -> FeedbackEntry | None:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None:
        return None
    entry = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=_normalize_note(note),
        next_action=existing.next_action,
        due_date=existing.due_date,
        snoozed_until=existing.snoozed_until,
        review_interval_days=existing.review_interval_days,
    )
    feedback_state.papers[normalized_id] = entry
    return entry


def set_feedback_action(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    next_action: str,
    updated_at: datetime | None = None,
) -> FeedbackEntry | None:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None:
        return None
    entry = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=existing.note,
        next_action=_normalize_action(next_action),
        due_date=existing.due_date,
        snoozed_until=existing.snoozed_until,
        review_interval_days=existing.review_interval_days,
    )
    feedback_state.papers[normalized_id] = entry
    return entry


def set_feedback_due_date(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    due_date: date,
    updated_at: datetime | None = None,
) -> FeedbackEntry | None:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None:
        return None
    entry = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=existing.note,
        next_action=existing.next_action,
        due_date=due_date,
        snoozed_until=existing.snoozed_until,
        review_interval_days=existing.review_interval_days,
    )
    feedback_state.papers[normalized_id] = entry
    return entry


def set_feedback_snoozed_until(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    snoozed_until: date,
    updated_at: datetime | None = None,
) -> FeedbackEntry | None:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None:
        return None
    entry = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=existing.note,
        next_action=existing.next_action,
        due_date=existing.due_date,
        snoozed_until=snoozed_until,
        review_interval_days=existing.review_interval_days,
    )
    feedback_state.papers[normalized_id] = entry
    return entry


def set_feedback_review_interval_days(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    review_interval_days: int,
    updated_at: datetime | None = None,
) -> FeedbackEntry | None:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None:
        return None
    if review_interval_days <= 0:
        raise ValueError("review_interval_days must be positive")
    entry = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=existing.note,
        next_action=existing.next_action,
        due_date=existing.due_date,
        snoozed_until=existing.snoozed_until,
        review_interval_days=review_interval_days,
    )
    feedback_state.papers[normalized_id] = entry
    return entry


def clear_feedback_status(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
) -> bool:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    return feedback_state.papers.pop(normalized_id, None) is not None


def clear_feedback_note(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    updated_at: datetime | None = None,
) -> bool:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None or existing.note is None:
        return False
    feedback_state.papers[normalized_id] = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=None,
        next_action=existing.next_action,
        due_date=existing.due_date,
        snoozed_until=existing.snoozed_until,
        review_interval_days=existing.review_interval_days,
    )
    return True


def clear_feedback_action(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    updated_at: datetime | None = None,
) -> bool:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None or existing.next_action is None:
        return False
    feedback_state.papers[normalized_id] = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=existing.note,
        next_action=None,
        due_date=existing.due_date,
        snoozed_until=existing.snoozed_until,
        review_interval_days=existing.review_interval_days,
    )
    return True


def clear_feedback_due_date(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    updated_at: datetime | None = None,
) -> bool:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None or existing.due_date is None:
        return False
    feedback_state.papers[normalized_id] = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=existing.note,
        next_action=existing.next_action,
        due_date=None,
        snoozed_until=existing.snoozed_until,
        review_interval_days=existing.review_interval_days,
    )
    return True


def clear_feedback_snoozed_until(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    updated_at: datetime | None = None,
) -> bool:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None or existing.snoozed_until is None:
        return False
    feedback_state.papers[normalized_id] = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=existing.note,
        next_action=existing.next_action,
        due_date=existing.due_date,
        snoozed_until=None,
        review_interval_days=existing.review_interval_days,
    )
    return True


def clear_feedback_review_interval_days(
    feedback_state: FeedbackState,
    *,
    canonical_id: str,
    updated_at: datetime | None = None,
) -> bool:
    normalized_id = normalize_feedback_canonical_id(canonical_id)
    existing = feedback_state.papers.get(normalized_id)
    if existing is None or existing.review_interval_days is None:
        return False
    feedback_state.papers[normalized_id] = FeedbackEntry(
        status=existing.status,
        updated_at=updated_at or datetime.now(UTC),
        note=existing.note,
        next_action=existing.next_action,
        due_date=existing.due_date,
        snoozed_until=existing.snoozed_until,
        review_interval_days=None,
    )
    return True


def list_feedback_entries(
    feedback_state: FeedbackState,
) -> list[tuple[str, FeedbackEntry]]:
    return sorted(
        feedback_state.papers.items(),
        key=lambda item: (
            -(item[1].updated_at.timestamp() if item[1].updated_at is not None else -1),
            item[0],
        ),
    )


def merge_feedback_states(
    local_state: FeedbackState,
    remote_state: FeedbackState,
    *,
    strategy: FeedbackMergeStrategy,
) -> FeedbackState:
    merged: dict[str, FeedbackEntry] = {}
    for canonical_id in sorted(
        set(local_state.papers) | set(remote_state.papers)
    ):
        local_entry = local_state.papers.get(canonical_id)
        remote_entry = remote_state.papers.get(canonical_id)
        if local_entry is None:
            assert remote_entry is not None
            merged[canonical_id] = remote_entry
            continue
        if remote_entry is None:
            merged[canonical_id] = local_entry
            continue
        merged[canonical_id] = _merge_feedback_entry(
            local_entry,
            remote_entry,
            strategy=strategy,
        )
    return FeedbackState(papers=merged)


def advance_feedback_state(
    feedback_state: FeedbackState,
    *,
    today: date,
) -> FeedbackAutomation:
    resumed_from_snooze: set[str] = set()
    recurring_due: set[str] = set()
    changed = False
    actionable_statuses = {"star", "follow_up", "reading"}

    for canonical_id, entry in list(feedback_state.papers.items()):
        updated_entry = entry
        if entry.snoozed_until is not None and entry.snoozed_until <= today:
            if entry.snoozed_until == today:
                resumed_from_snooze.add(canonical_id)
            updated_entry = replace(updated_entry, snoozed_until=None)
            changed = True

        effective_due_date = _effective_due_date(updated_entry)
        if (
            updated_entry.status in actionable_statuses
            and updated_entry.review_interval_days is not None
            and updated_entry.due_date is None
            and effective_due_date is not None
            and effective_due_date <= today
        ):
            recurring_due.add(canonical_id)

        if updated_entry is not entry:
            feedback_state.papers[canonical_id] = updated_entry

    return FeedbackAutomation(
        resumed_from_snooze=frozenset(resumed_from_snooze),
        recurring_due=frozenset(recurring_due),
        changed=changed,
    )


def normalize_feedback_canonical_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("canonical_id must not be empty")
    prefix, separator, remainder = normalized.partition(":")
    if not separator:
        return normalized
    return f"{prefix.casefold()}:{remainder.casefold()}"


def apply_feedback_to_papers(
    papers: list[Paper],
    *,
    feedback_state: FeedbackState,
    config: FeedbackConfig,
) -> list[Paper]:
    """Apply feedback-derived filtering and ranking signals to papers."""

    adjusted: list[Paper] = []
    for paper in papers:
        entry = feedback_state.papers.get(paper.canonical_id())
        if entry is None:
            adjusted.append(paper)
            continue

        paper.feedback_status = entry.status
        paper.feedback_note = entry.note
        paper.feedback_next_action = entry.next_action
        paper.feedback_due_date = entry.due_date
        paper.feedback_snoozed_until = entry.snoozed_until
        paper.feedback_review_interval_days = entry.review_interval_days
        if entry.status == "ignore" and config.hide_ignored:
            continue
        if entry.status == "star":
            paper.base_relevance_score += config.star_boost
            paper.match_reasons.append("feedback: starred")
        elif entry.status == "follow_up":
            paper.base_relevance_score += config.follow_up_boost
            paper.match_reasons.append("feedback: follow up")
        elif entry.status == "reading":
            paper.base_relevance_score += config.reading_boost
            paper.match_reasons.append("feedback: reading")
        elif entry.status == "done":
            paper.base_relevance_score = max(
                0,
                paper.base_relevance_score - config.done_penalty,
            )
            paper.match_reasons.append("feedback: done")
        else:
            paper.base_relevance_score = max(
                0,
                paper.base_relevance_score - config.ignore_penalty,
            )
            paper.match_reasons.append("feedback: ignored")
        adjusted.append(paper)
    return adjusted


def feedback_label(status: FeedbackStatus | None) -> str | None:
    if status is None:
        return None
    labels = {
        "star": "star",
        "follow_up": "follow_up",
        "reading": "reading",
        "done": "done",
        "ignore": "ignore",
    }
    return labels[status]


def feedback_label_zh(status: FeedbackStatus | None) -> str | None:
    if status is None:
        return None
    labels = {
        "star": "标星",
        "follow_up": "待跟进",
        "reading": "阅读中",
        "done": "已完成",
        "ignore": "忽略",
    }
    return labels[status]


def feedback_command_snippet(
    canonical_id: str,
    status: FeedbackStatus,
    *,
    config_path: str = "config.toml",
) -> str:
    return (
        "python -m paper_digest feedback set "
        f"'{canonical_id}' {status} --config {config_path}"
    )


def feedback_action_command_snippet(
    canonical_id: str,
    *,
    action: str = "TODO: next action",
    config_path: str = "config.toml",
) -> str:
    return (
        "python -m paper_digest feedback action set "
        f"'{canonical_id}' '{action}' --config {config_path}"
    )


def feedback_due_command_snippet(
    canonical_id: str,
    *,
    due_date: str = "YYYY-MM-DD",
    config_path: str = "config.toml",
) -> str:
    return (
        "python -m paper_digest feedback due set "
        f"'{canonical_id}' {due_date} --config {config_path}"
    )


def feedback_snooze_command_snippet(
    canonical_id: str,
    *,
    snoozed_until: str = "YYYY-MM-DD",
    config_path: str = "config.toml",
) -> str:
    return (
        "python -m paper_digest feedback snooze set "
        f"'{canonical_id}' {snoozed_until} --config {config_path}"
    )


def feedback_interval_command_snippet(
    canonical_id: str,
    *,
    review_interval_days: int | str = "7",
    config_path: str = "config.toml",
) -> str:
    return (
        "python -m paper_digest feedback interval set "
        f"'{canonical_id}' {review_interval_days} --config {config_path}"
    )


def _parse_feedback_entry(value: object) -> FeedbackEntry | None:
    if isinstance(value, str):
        status = _feedback_status(value)
        if status is None:
            return None
        return FeedbackEntry(status=status)
    if not isinstance(value, dict):
        return None
    status = _feedback_status(value.get("status"))
    if status is None:
        return None
    updated_at = _parse_optional_datetime(value.get("updated_at"))
    return FeedbackEntry(
        status=status,
        updated_at=updated_at,
        note=_normalize_note(value.get("note")),
        next_action=_normalize_action(value.get("next_action")),
        due_date=_parse_optional_date(value.get("due_date")),
        snoozed_until=_parse_optional_date(value.get("snoozed_until")),
        review_interval_days=_parse_optional_positive_int(
            value.get("review_interval_days")
        ),
    )


def _feedback_status(value: object) -> FeedbackStatus | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized not in {"star", "follow_up", "reading", "done", "ignore"}:
        return None
    return cast(FeedbackStatus, normalized)


def _parse_optional_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _parse_optional_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_optional_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value <= 0:
        return None
    return value


def _serialize_feedback_entry(entry: FeedbackEntry) -> object:
    if (
        entry.updated_at is None
        and entry.note is None
        and entry.next_action is None
        and entry.due_date is None
        and entry.snoozed_until is None
        and entry.review_interval_days is None
    ):
        return entry.status
    payload: dict[str, object] = {
        "status": entry.status,
    }
    if entry.updated_at is not None:
        payload["updated_at"] = entry.updated_at.isoformat()
    if entry.note is not None:
        payload["note"] = entry.note
    if entry.next_action is not None:
        payload["next_action"] = entry.next_action
    if entry.due_date is not None:
        payload["due_date"] = entry.due_date.isoformat()
    if entry.snoozed_until is not None:
        payload["snoozed_until"] = entry.snoozed_until.isoformat()
    if entry.review_interval_days is not None:
        payload["review_interval_days"] = entry.review_interval_days
    return payload


def _effective_due_date(entry: FeedbackEntry) -> date | None:
    if entry.due_date is not None:
        return entry.due_date
    if entry.review_interval_days is None or entry.updated_at is None:
        return None
    return entry.updated_at.date() + timedelta(days=entry.review_interval_days)


def _merge_feedback_entry(
    local_entry: FeedbackEntry,
    remote_entry: FeedbackEntry,
    *,
    strategy: FeedbackMergeStrategy,
) -> FeedbackEntry:
    preferred, fallback = _preferred_feedback_entries(
        local_entry,
        remote_entry,
        strategy=strategy,
    )
    return FeedbackEntry(
        status=preferred.status,
        updated_at=_latest_datetime(local_entry.updated_at, remote_entry.updated_at),
        note=_merged_optional_value(preferred.note, fallback.note),
        next_action=_merged_optional_value(
            preferred.next_action,
            fallback.next_action,
        ),
        due_date=_merged_optional_value(preferred.due_date, fallback.due_date),
        snoozed_until=_merged_optional_value(
            preferred.snoozed_until,
            fallback.snoozed_until,
        ),
        review_interval_days=_merged_optional_value(
            preferred.review_interval_days,
            fallback.review_interval_days,
        ),
    )


def _preferred_feedback_entries(
    local_entry: FeedbackEntry,
    remote_entry: FeedbackEntry,
    *,
    strategy: FeedbackMergeStrategy,
) -> tuple[FeedbackEntry, FeedbackEntry]:
    if strategy == "local":
        return local_entry, remote_entry
    if strategy == "remote":
        return remote_entry, local_entry
    local_updated = local_entry.updated_at
    remote_updated = remote_entry.updated_at
    if local_updated is None and remote_updated is None:
        return local_entry, remote_entry
    if remote_updated is None:
        return local_entry, remote_entry
    if local_updated is None:
        return remote_entry, local_entry
    if remote_updated > local_updated:
        return remote_entry, local_entry
    return local_entry, remote_entry


def _merged_optional_value[T](
    preferred: T | None,
    fallback: T | None,
) -> T | None:
    if preferred is not None:
        return preferred
    return fallback


def _latest_datetime(
    left: datetime | None,
    right: datetime | None,
) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _coerce_feedback_path(path: object) -> Path:
    if isinstance(path, Path):
        return path
    return Path(str(path))


def _normalize_note(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_action(value: object) -> str | None:
    return _normalize_note(value)
