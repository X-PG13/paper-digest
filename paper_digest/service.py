"""Application service layer."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .arxiv_client import fetch_latest_papers
from .config import AppConfig
from .digest import DigestRun, FeedDigest, filter_papers


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

    for feed in config.feeds:
        papers = fetch_latest_papers(
            feed,
            request_delay_seconds=config.request_delay_seconds,
        )
        filtered = filter_papers(
            papers,
            feed,
            now=now_utc,
            lookback_hours=config.lookback_hours,
        )
        feeds.append(FeedDigest(name=feed.name, papers=filtered))

    return DigestRun(
        generated_at=local_now,
        timezone=config.timezone,
        lookback_hours=config.lookback_hours,
        feeds=feeds,
    )
