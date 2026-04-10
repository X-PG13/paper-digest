"""Application service layer."""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .analysis import apply_digest_briefing, enrich_digest_with_analysis
from .arxiv_client import Paper
from .config import AppConfig
from .digest import DigestRun, FeedDigest, filter_papers, finalize_digest_scoring
from .sources import fetch_feed_papers
from .state import DigestState, dedupe_papers, load_state, save_state


def generate_digest(
    config: AppConfig,
    *,
    now: datetime | None = None,
    state: DigestState | None = None,
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
    contact_email = config.email.from_address if config.email is not None else None
    openalex_api_key = None
    if config.openalex_api_key_env is not None:
        openalex_api_key = os.getenv(config.openalex_api_key_env)
    papers_by_canonical_id: dict[str, Paper] = {}

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
                feed_papers.append(paper)
                continue
            existing.merge_duplicate(paper)
        feed_papers.sort(key=lambda item: item.published_at, reverse=True)
        feeds.append(FeedDigest(name=feed.name, papers=feed_papers))

    digest = DigestRun(
        generated_at=local_now,
        timezone=config.timezone,
        lookback_hours=config.lookback_hours,
        feeds=feeds,
        template=config.digest.template,
    )
    finalize_digest_scoring(digest)
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
