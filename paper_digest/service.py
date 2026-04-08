"""Application service layer."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .analysis import apply_digest_briefing, enrich_digest_with_analysis
from .config import AppConfig
from .digest import DigestRun, FeedDigest, filter_papers
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

    for feed in config.feeds:
        papers = fetch_feed_papers(
            feed,
            now=now_utc,
            lookback_hours=config.lookback_hours,
            request_delay_seconds=config.request_delay_seconds,
            contact_email=contact_email,
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
        feeds.append(FeedDigest(name=feed.name, papers=filtered))

    digest = DigestRun(
        generated_at=local_now,
        timezone=config.timezone,
        lookback_hours=config.lookback_hours,
        feeds=feeds,
        template=config.digest.template,
    )
    if config.analysis is not None:
        enrich_digest_with_analysis(
            config.analysis,
            digest,
            template=config.digest.template,
            top_highlights=config.digest.top_highlights,
            feed_key_points=config.digest.feed_key_points,
        )
    elif config.digest.template != "default":
        apply_digest_briefing(
            digest,
            top_highlights=config.digest.top_highlights,
            feed_key_points=config.digest.feed_key_points,
            template=config.digest.template,
        )
    if state is None:
        save_state(config.state, managed_state)
    return digest
