"""User feedback state for paper prioritization and reading lists."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from .arxiv_client import Paper
from .config import FeedbackConfig, FeedbackStatus


@dataclass(slots=True, frozen=True)
class FeedbackEntry:
    status: FeedbackStatus
    updated_at: datetime | None = None


@dataclass(slots=True)
class FeedbackState:
    papers: dict[str, FeedbackEntry]


def load_feedback(config: FeedbackConfig) -> FeedbackState:
    """Load feedback state from disk if enabled, otherwise return an empty map."""

    if not config.enabled or not config.path.exists():
        return FeedbackState(papers={})

    raw = json.loads(config.path.read_text(encoding="utf-8"))
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
        if entry.status == "ignore" and config.hide_ignored:
            continue
        if entry.status == "star":
            paper.base_relevance_score += config.star_boost
            paper.match_reasons.append("feedback: starred")
        elif entry.status == "follow_up":
            paper.base_relevance_score += config.follow_up_boost
            paper.match_reasons.append("feedback: follow up")
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
        "ignore": "ignore",
    }
    return labels[status]


def feedback_label_zh(status: FeedbackStatus | None) -> str | None:
    if status is None:
        return None
    labels = {
        "star": "标星",
        "follow_up": "待跟进",
        "ignore": "忽略",
    }
    return labels[status]


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
    return FeedbackEntry(status=status, updated_at=updated_at)


def _feedback_status(value: object) -> FeedbackStatus | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized not in {"star", "follow_up", "ignore"}:
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
