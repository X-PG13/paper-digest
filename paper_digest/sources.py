"""Source dispatch for paper retrieval."""

from __future__ import annotations

from datetime import datetime

from .arxiv_client import Paper, fetch_latest_papers
from .config import FeedConfig
from .crossref_client import fetch_latest_crossref_papers
from .pubmed_client import fetch_latest_pubmed_papers
from .semantic_scholar_client import fetch_latest_semantic_scholar_papers


def fetch_feed_papers(
    feed: FeedConfig,
    *,
    now: datetime,
    lookback_hours: int,
    request_delay_seconds: float,
    request_timeout_seconds: int,
    retry_attempts: int,
    retry_backoff_seconds: float,
    contact_email: str | None,
) -> list[Paper]:
    """Fetch papers for a feed from its configured source."""

    if feed.source == "arxiv":
        return fetch_latest_papers(
            feed,
            request_delay_seconds=request_delay_seconds,
            request_timeout_seconds=request_timeout_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    if feed.source == "crossref":
        return fetch_latest_crossref_papers(
            feed,
            now=now,
            lookback_hours=lookback_hours,
            request_delay_seconds=request_delay_seconds,
            request_timeout_seconds=request_timeout_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            contact_email=contact_email,
        )
    if feed.source == "pubmed":
        return fetch_latest_pubmed_papers(
            feed,
            now=now,
            lookback_hours=lookback_hours,
            request_delay_seconds=request_delay_seconds,
            request_timeout_seconds=request_timeout_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            contact_email=contact_email,
        )
    if feed.source == "semantic_scholar":
        return fetch_latest_semantic_scholar_papers(
            feed,
            now=now,
            lookback_hours=lookback_hours,
            request_delay_seconds=request_delay_seconds,
            request_timeout_seconds=request_timeout_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            contact_email=contact_email,
        )
    raise ValueError(f"unsupported feed source: {feed.source}")
