"""Digest filtering and rendering helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .arxiv_client import Paper
from .config import AppConfig, FeedConfig


@dataclass(slots=True)
class FeedDigest:
    name: str
    papers: list[Paper]


@dataclass(slots=True)
class DigestRun:
    generated_at: datetime
    timezone: str
    lookback_hours: int
    feeds: list[FeedDigest]

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "timezone": self.timezone,
            "lookback_hours": self.lookback_hours,
            "feeds": [
                {
                    "name": feed.name,
                    "papers": [paper.to_dict() for paper in feed.papers],
                }
                for feed in self.feeds
            ],
        }


def filter_papers(
    papers: list[Paper],
    feed: FeedConfig,
    *,
    now: datetime,
    lookback_hours: int,
) -> list[Paper]:
    cutoff = now - timedelta(hours=lookback_hours)
    filtered: list[Paper] = []

    for paper in papers:
        if paper.published_at < cutoff:
            continue
        if feed.keywords and not _matches_any_keyword(paper, feed.keywords):
            continue
        if feed.exclude_keywords and _matches_any_keyword(paper, feed.exclude_keywords):
            continue
        filtered.append(paper)

    filtered.sort(key=lambda item: item.published_at, reverse=True)
    return filtered[: feed.max_items]


def render_markdown(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    lines = [
        "# Daily Paper Digest",
        "",
        f"- Generated at: {generated_at} ({digest.timezone})",
        f"- Lookback window: last {digest.lookback_hours} hours",
        "",
    ]

    for feed in digest.feeds:
        lines.append(f"## {feed.name}")
        lines.append("")
        if not feed.papers:
            lines.append("No matching papers found.")
            lines.append("")
            continue

        for index, paper in enumerate(feed.papers, start=1):
            published = paper.published_at.astimezone(local_tz).strftime(
                "%Y-%m-%d %H:%M"
            )
            authors = (
                ", ".join(paper.authors[:6]) if paper.authors else "Unknown authors"
            )
            if len(paper.authors) > 6:
                authors += ", et al."

            lines.append(f"{index}. [{paper.title}]({paper.abstract_url})")
            lines.append(f"   - Published: {published}")
            lines.append(f"   - Authors: {authors}")
            lines.append(f"   - Categories: {', '.join(paper.categories)}")
            if paper.pdf_url:
                lines.append(f"   - PDF: {paper.pdf_url}")
            lines.append(f"   - Summary: {paper.summary}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_outputs(config: AppConfig, digest: DigestRun) -> tuple[Path, Path]:
    target_dir = config.output_dir / digest.generated_at.astimezone(
        ZoneInfo(config.timezone)
    ).strftime("%Y-%m-%d")
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / "digest.json"
    markdown_path = target_dir / "digest.md"

    json_payload = json.dumps(digest.to_dict(), ensure_ascii=False, indent=2)
    markdown_payload = render_markdown(digest)

    json_path.write_text(json_payload, encoding="utf-8")
    markdown_path.write_text(markdown_payload, encoding="utf-8")

    latest_json = config.output_dir / "latest.json"
    latest_markdown = config.output_dir / "latest.md"
    latest_json.write_text(json_payload, encoding="utf-8")
    latest_markdown.write_text(markdown_payload, encoding="utf-8")

    return json_path, markdown_path


def _matches_any_keyword(paper: Paper, keywords: list[str]) -> bool:
    haystack = f"{paper.title}\n{paper.summary}".lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def summarize_digest(digest: DigestRun) -> str:
    """Return a compact human-readable summary of per-feed counts."""

    if not digest.feeds:
        return "no feeds"
    return ", ".join(f"{feed.name}={len(feed.papers)}" for feed in digest.feeds)
