"""Application service layer."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from .analysis import apply_digest_briefing, enrich_digest_with_analysis
from .arxiv_client import Paper
from .config import AppConfig, FeedbackStatus
from .digest import (
    DigestRun,
    FeedDigest,
    FocusItem,
    filter_papers,
    finalize_digest_scoring,
)
from .feedback import (
    FeedbackEntry,
    FeedbackState,
    apply_feedback_to_papers,
    load_feedback,
)
from .sources import fetch_feed_papers
from .state import DigestState, dedupe_papers, load_state, save_state


@dataclass(slots=True)
class _CurrentFocusCandidate:
    paper: Paper
    feed_names: set[str] = field(default_factory=set)
    seen_before_today: bool = False
    in_digest: bool = False


@dataclass(slots=True)
class _HistorySnapshot:
    paper: Paper
    feed_names: set[str] = field(default_factory=set)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    active_days: set[str] = field(default_factory=set)
    appearance_count: int = 0


def generate_digest(
    config: AppConfig,
    *,
    now: datetime | None = None,
    state: DigestState | None = None,
    feedback_state: FeedbackState | None = None,
) -> DigestRun:
    """Build a digest for every configured feed."""

    local_tz = ZoneInfo(config.timezone)
    topic_candidates = _topic_candidates_from_feeds(config.feeds)
    if now is None:
        local_now = datetime.now(local_tz)
    else:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        local_now = now.astimezone(local_tz)

    now_utc = local_now.astimezone(UTC)
    feeds: list[FeedDigest] = []
    managed_state = state
    if managed_state is None:
        managed_state = load_state(config.state)
    managed_feedback = feedback_state
    if managed_feedback is None:
        managed_feedback = load_feedback(config.feedback)
    contact_email = config.email.from_address if config.email is not None else None
    openalex_api_key = None
    if config.openalex_api_key_env is not None:
        openalex_api_key = os.getenv(config.openalex_api_key_env)
    papers_by_canonical_id: dict[str, Paper] = {}
    focus_candidates: dict[str, _CurrentFocusCandidate] = {}

    for feed in config.feeds:
        papers = fetch_feed_papers(
            feed,
            now=now_utc,
            lookback_hours=config.lookback_hours,
            request_delay_seconds=config.request_delay_seconds,
            request_timeout_seconds=config.request_timeout_seconds,
            retry_attempts=config.fetch_retry_attempts,
            retry_backoff_seconds=config.fetch_retry_backoff_seconds,
            contact_email=contact_email,
            openalex_api_key=openalex_api_key,
        )
        filtered = filter_papers(
            papers,
            feed,
            now=now_utc,
            lookback_hours=config.lookback_hours,
            ranking=config.ranking,
        )
        filtered = apply_feedback_to_papers(
            filtered,
            feedback_state=managed_feedback,
            config=config.feedback,
        )
        seen_before_today = set(managed_state.seen_papers.get(feed.name, {}))
        _record_focus_candidates(
            focus_candidates,
            papers=filtered,
            feed_name=feed.name,
            seen_before_today=seen_before_today,
        )
        filtered = dedupe_papers(
            managed_state,
            feed_name=feed.name,
            papers=filtered,
            now=local_now,
            retention_days=config.state.retention_days,
        )
        feed_papers: list[Paper] = []
        for paper in filtered:
            canonical_id = paper.canonical_id()
            existing = papers_by_canonical_id.get(canonical_id)
            if existing is None:
                papers_by_canonical_id[canonical_id] = paper
                candidate = focus_candidates.get(canonical_id)
                if candidate is not None:
                    candidate.paper = paper
                    candidate.in_digest = True
                feed_papers.append(paper)
                continue
            existing.merge_duplicate(paper)
            candidate = focus_candidates.get(canonical_id)
            if candidate is not None:
                candidate.paper = existing
                candidate.in_digest = True
        feed_papers.sort(key=lambda item: item.published_at, reverse=True)
        feeds.append(
            FeedDigest(
                name=feed.name,
                papers=feed_papers,
                sort_by=feed.sort_by or config.ranking.sort_by,
            )
        )

    digest = DigestRun(
        generated_at=local_now,
        timezone=config.timezone,
        lookback_hours=config.lookback_hours,
        feeds=feeds,
        template=config.digest.template,
    )
    finalize_digest_scoring(digest, ranking=config.ranking)
    if config.analysis is not None:
        enrich_digest_with_analysis(
            config.analysis,
            digest,
            template=config.digest.template,
            top_highlights=config.digest.top_highlights,
            feed_key_points=config.digest.feed_key_points,
            topic_candidates=topic_candidates,
        )
    elif config.digest.template != "default":
        apply_digest_briefing(
            digest,
            top_highlights=config.digest.top_highlights,
            feed_key_points=config.digest.feed_key_points,
            template=config.digest.template,
            topic_candidates=topic_candidates,
        )
    if state is None:
        save_state(config.state, managed_state)
    digest.focus_items = _build_focus_items(
        digest,
        config=config,
        feedback_state=managed_feedback,
        focus_candidates=focus_candidates,
        now=local_now,
    )
    return digest


def _topic_candidates_from_feeds(feeds: Sequence[object]) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for feed in feeds:
        for keyword in getattr(feed, "keywords", []):
            stripped = keyword.strip()
            normalized = stripped.lower()
            if not stripped or normalized in seen:
                continue
            seen.add(normalized)
            keywords.append(stripped)
    return keywords


def _record_focus_candidates(
    candidates: dict[str, _CurrentFocusCandidate],
    *,
    papers: Sequence[Paper],
    feed_name: str,
    seen_before_today: set[str],
) -> None:
    for paper in papers:
        if paper.feedback_status not in {"star", "follow_up"}:
            continue
        canonical_id = paper.canonical_id()
        existing = candidates.get(canonical_id)
        if existing is None:
            candidates[canonical_id] = _CurrentFocusCandidate(
                paper=paper,
                feed_names={feed_name},
                seen_before_today=canonical_id in seen_before_today,
            )
            continue
        existing.paper.merge_duplicate(paper)
        existing.feed_names.add(feed_name)
        existing.seen_before_today = (
            existing.seen_before_today or canonical_id in seen_before_today
        )


def _build_focus_items(
    digest: DigestRun,
    *,
    config: AppConfig,
    feedback_state: FeedbackState,
    focus_candidates: dict[str, _CurrentFocusCandidate],
    now: datetime,
) -> list[FocusItem]:
    if not feedback_state.papers:
        return []

    history_ids = {
        canonical_id
        for canonical_id, entry in feedback_state.papers.items()
        if entry.status in {"star", "follow_up"}
    } | set(focus_candidates)
    history = _load_history_snapshots(config.output_dir, history_ids)
    current_date = now.astimezone(ZoneInfo(config.timezone)).date().isoformat()
    focus_items: list[tuple[tuple[int, float, int, str], FocusItem]] = []
    recent_cutoff = now.astimezone(UTC) - timedelta(hours=config.lookback_hours)

    for canonical_id, entry in feedback_state.papers.items():
        if entry.status not in {"star", "follow_up"}:
            continue

        candidate = focus_candidates.get(canonical_id)
        snapshot = history.get(canonical_id)
        paper = (
            candidate.paper
            if candidate is not None
            else (snapshot.paper if snapshot else None)
        )
        if paper is None:
            continue

        reason_codes: list[str] = []
        if (
            entry.status == "star"
            and config.notify.include_new_starred
            and _is_recent_feedback(entry, cutoff=recent_cutoff)
        ):
            reason_codes.append("new_starred")
        if (
            entry.status == "follow_up"
            and config.notify.include_follow_up_resurfaced
            and candidate is not None
            and candidate.seen_before_today
        ):
            reason_codes.append("follow_up_resurfaced")
        if (
            entry.status == "star"
            and config.notify.include_starred_momentum
            and candidate is not None
            and _entered_momentum(
                snapshot,
                candidate,
                current_date=current_date,
                current_seen_at=now,
            )
        ):
            reason_codes.append("starred_momentum")
        if not reason_codes:
            continue

        merged_stats = _merge_snapshot_with_candidate(
            snapshot,
            candidate,
            current_date=current_date,
            current_seen_at=now,
        )
        focus_item = FocusItem(
            canonical_id=paper.canonical_id(),
            title=paper.title,
            abstract_url=paper.abstract_url,
            summary=paper.summary,
            source_label=paper.source_label(),
            feedback_status=entry.status,
            reasons=reason_codes,
            feed_names=sorted(merged_stats.feed_names),
            relevance_score=paper.relevance_score,
            active_days=len(merged_stats.active_days),
            active_feeds=len(merged_stats.feed_names),
            appearance_count=merged_stats.appearance_count,
            first_seen=merged_stats.first_seen,
            last_seen=merged_stats.last_seen,
        )
        priority = _focus_priority(reason_codes)
        anchor = (
            entry.updated_at.timestamp()
            if entry.updated_at is not None
            else now.timestamp()
        )
        focus_items.append(
            (
                (priority, -anchor, -paper.relevance_score, paper.title.casefold()),
                focus_item,
            )
        )

    focus_items.sort(key=lambda item: item[0])
    return [
        item
        for _, item in focus_items[: config.notify.max_focus_items]
    ]


def _load_history_snapshots(
    output_dir: Path,
    canonical_ids: set[str],
) -> dict[str, _HistorySnapshot]:
    if not canonical_ids or not output_dir.exists():
        return {}

    snapshots: dict[str, _HistorySnapshot] = {}
    for day_dir in sorted(output_dir.iterdir()):
        if not day_dir.is_dir():
            continue
        digest_path = day_dir / "digest.json"
        if not digest_path.exists():
            continue
        try:
            payload = json.loads(digest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        generated_at = _parse_optional_datetime(payload.get("generated_at"))
        if generated_at is None:
            continue
        day_label = day_dir.name
        for feed_payload in payload.get("feeds", []):
            if not isinstance(feed_payload, dict):
                continue
            feed_name = str(feed_payload.get("name", "")).strip()
            for raw_paper in feed_payload.get("papers", []):
                if not isinstance(raw_paper, dict):
                    continue
                paper = _paper_from_payload(raw_paper)
                if paper is None:
                    continue
                canonical_id = paper.canonical_id()
                if canonical_id not in canonical_ids:
                    continue
                snapshot = snapshots.get(canonical_id)
                if snapshot is None:
                    snapshots[canonical_id] = _HistorySnapshot(
                        paper=paper,
                        feed_names={feed_name} if feed_name else set(),
                        first_seen=generated_at,
                        last_seen=generated_at,
                        active_days={day_label},
                        appearance_count=1,
                    )
                    continue
                snapshot.paper.merge_duplicate(paper)
                if feed_name:
                    snapshot.feed_names.add(feed_name)
                snapshot.active_days.add(day_label)
                snapshot.appearance_count += 1
                if snapshot.first_seen is None or generated_at < snapshot.first_seen:
                    snapshot.first_seen = generated_at
                if snapshot.last_seen is None or generated_at > snapshot.last_seen:
                    snapshot.last_seen = generated_at
    return snapshots


def _paper_from_payload(payload: dict[str, object]) -> Paper | None:
    try:
        published_at = datetime.fromisoformat(str(payload["published_at"]))
        updated_at = datetime.fromisoformat(str(payload["updated_at"]))
    except (KeyError, TypeError, ValueError):
        return None
    title = str(payload.get("title", "")).strip()
    abstract_url = str(payload.get("abstract_url", "")).strip()
    if not title or not abstract_url:
        return None
    return Paper(
        title=title,
        summary=str(payload.get("summary", "")).strip(),
        authors=_string_list(payload.get("authors")),
        categories=_string_list(payload.get("categories")),
        paper_id=str(payload.get("paper_id", abstract_url)).strip() or abstract_url,
        abstract_url=abstract_url,
        pdf_url=_optional_string(payload.get("pdf_url")),
        published_at=published_at,
        updated_at=updated_at,
        source=str(payload.get("source", "arxiv")).strip() or "arxiv",
        date_label=str(payload.get("date_label", "Published")).strip() or "Published",
        tags=_string_list(payload.get("tags")),
        topics=_string_list(payload.get("topics")),
        doi=_optional_string(payload.get("doi")),
        arxiv_id=_optional_string(payload.get("arxiv_id")),
        source_variants=_string_list(payload.get("source_variants")),
        source_urls=_string_dict(payload.get("source_urls")),
        relevance_score=_optional_int(payload.get("relevance_score")) or 0,
        match_reasons=_string_list(payload.get("match_reasons")),
        feedback_status=_feedback_status(payload.get("feedback_status")),
    )


def _merge_snapshot_with_candidate(
    snapshot: _HistorySnapshot | None,
    candidate: _CurrentFocusCandidate | None,
    *,
    current_date: str,
    current_seen_at: datetime,
) -> _HistorySnapshot:
    if snapshot is None and candidate is None:
        raise ValueError("snapshot or candidate must be provided")
    if snapshot is None:
        assert candidate is not None
        return _HistorySnapshot(
            paper=candidate.paper,
            feed_names=set(candidate.feed_names),
            first_seen=current_seen_at,
            last_seen=current_seen_at,
            active_days={current_date},
            appearance_count=max(len(candidate.feed_names), 1),
        )

    merged = _HistorySnapshot(
        paper=snapshot.paper,
        feed_names=set(snapshot.feed_names),
        first_seen=snapshot.first_seen,
        last_seen=snapshot.last_seen,
        active_days=set(snapshot.active_days),
        appearance_count=snapshot.appearance_count,
    )
    if candidate is None:
        return merged

    merged.paper.merge_duplicate(candidate.paper)
    merged.feed_names.update(candidate.feed_names)
    merged.active_days.add(current_date)
    merged.appearance_count += max(len(candidate.feed_names), 1)
    if merged.first_seen is None or current_seen_at < merged.first_seen:
        merged.first_seen = current_seen_at
    if merged.last_seen is None or current_seen_at > merged.last_seen:
        merged.last_seen = current_seen_at
    return merged


def _entered_momentum(
    snapshot: _HistorySnapshot | None,
    candidate: _CurrentFocusCandidate,
    *,
    current_date: str,
    current_seen_at: datetime,
) -> bool:
    previous_momentum = _is_momentum(snapshot)
    current_momentum = _is_momentum(
        _merge_snapshot_with_candidate(
            snapshot,
            candidate,
            current_date=current_date,
            current_seen_at=current_seen_at,
        )
    )
    return current_momentum and not previous_momentum


def _is_momentum(snapshot: _HistorySnapshot | None) -> bool:
    if snapshot is None:
        return False
    return len(snapshot.active_days) > 1 or len(snapshot.feed_names) > 1


def _focus_priority(reason_codes: Sequence[str]) -> int:
    if "new_starred" in reason_codes:
        return 0
    if "follow_up_resurfaced" in reason_codes:
        return 1
    return 2


def _is_recent_feedback(entry: FeedbackEntry, *, cutoff: datetime) -> bool:
    return entry.updated_at is not None and entry.updated_at >= cutoff


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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _string_dict(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        key_text = str(key).strip()
        item_text = str(item).strip()
        if key_text and item_text:
            result[key_text] = item_text
    return result


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _feedback_status(value: object) -> FeedbackStatus | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized not in {"star", "follow_up", "ignore"}:
        return None
    return cast(FeedbackStatus, normalized)
