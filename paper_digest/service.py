"""Application service layer."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .config import AppConfig
from .digest import DigestRun, FeedDigest, filter_papers
from .sources import fetch_feed_papers
from .state import dedupe_papers, load_state, save_state


def generate_digest(
    config: AppConfig,
    *,
    now: datetime | None = None,
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
    state = load_state(config.state)
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
            state,
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
    )
    save_state(config.state, state)
    return digest
