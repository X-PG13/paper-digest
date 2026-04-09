"""Digest filtering and rendering helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .arxiv_client import Paper
from .config import AppConfig, DigestTemplate, FeedConfig


@dataclass(slots=True)
class FeedDigest:
    name: str
    papers: list[Paper]
    key_points: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TopicDigest:
    name: str
    paper_count: int
    feed_names: list[str]
    paper_titles: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DigestRun:
    generated_at: datetime
    timezone: str
    lookback_hours: int
    feeds: list[FeedDigest]
    highlights: list[str] = field(default_factory=list)
    topic_sections: list[TopicDigest] = field(default_factory=list)
    template: DigestTemplate = "default"

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "timezone": self.timezone,
            "lookback_hours": self.lookback_hours,
            "highlights": list(self.highlights),
            "topic_sections": [
                {
                    "name": topic.name,
                    "paper_count": topic.paper_count,
                    "feed_names": list(topic.feed_names),
                    "paper_titles": list(topic.paper_titles),
                    "key_points": list(topic.key_points),
                }
                for topic in self.topic_sections
            ],
            "template": self.template,
            "feeds": [
                {
                    "name": feed.name,
                    "key_points": list(feed.key_points),
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
    if digest.template == "zh_daily_brief":
        return _render_zh_daily_brief(digest)
    return _render_default_markdown(digest)


def _render_default_markdown(digest: DigestRun) -> str:
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

    if digest.highlights:
        lines.append("## Today's Highlights")
        lines.append("")
        lines.extend(f"- {highlight}" for highlight in digest.highlights)
        lines.append("")

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
            lines.append(f"   - {paper.date_label}: {published}")
            lines.append(f"   - Authors: {authors}")
            lines.append(f"   - Source: {paper.source}")
            lines.append(f"   - Categories: {', '.join(paper.categories)}")
            if paper.pdf_url:
                lines.append(f"   - PDF: {paper.pdf_url}")
            if paper.analysis is not None:
                lines.append(f"   - Conclusion: {paper.analysis.conclusion}")
                if paper.analysis.contributions:
                    lines.append(
                        "   - Contributions: " + "; ".join(paper.analysis.contributions)
                    )
                if paper.analysis.audience:
                    lines.append(f"   - Best For: {paper.analysis.audience}")
                if paper.analysis.limitations:
                    lines.append(
                        "   - Limitations: " + "; ".join(paper.analysis.limitations)
                    )
            else:
                lines.append(f"   - Summary: {paper.summary}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _render_zh_daily_brief(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    lines = [
        "# 每日论文简报",
        "",
        f"- 生成时间：{generated_at} ({digest.timezone})",
        f"- 检索窗口：最近 {digest.lookback_hours} 小时",
        f"- 命中概览：{summarize_digest(digest)}",
        "",
    ]

    if digest.highlights:
        lines.append("## 今日重点")
        lines.append("")
        lines.extend(f"- {highlight}" for highlight in digest.highlights)
        lines.append("")

    if digest.topic_sections:
        lines.append("## 主题聚焦")
        lines.append("")
        for topic in digest.topic_sections:
            feed_names = "、".join(topic.feed_names)
            lines.append(f"### {topic.name}")
            lines.append("")
            lines.append(f"- 命中篇数：{topic.paper_count}")
            lines.append(f"- 覆盖分组：{feed_names}")
            if topic.paper_titles:
                lines.append(
                    "- 代表论文："
                    + "、".join(f"《{title}》" for title in topic.paper_titles[:3])
                )
            if topic.key_points:
                lines.append("- 主题速读：")
                lines.extend(f"  - {point}" for point in topic.key_points)
            lines.append("")

    for feed in digest.feeds:
        lines.append(f"## {feed.name} 观察")
        lines.append("")
        if not feed.papers:
            lines.append("今日没有新的命中文献。")
            lines.append("")
            continue

        if feed.key_points:
            lines.append("### 本组速览")
            lines.append("")
            lines.extend(f"- {point}" for point in feed.key_points)
            lines.append("")

        lines.append("### 论文速览")
        lines.append("")
        for index, paper in enumerate(feed.papers, start=1):
            published = paper.published_at.astimezone(local_tz).strftime(
                "%Y-%m-%d %H:%M"
            )
            authors = "，".join(paper.authors[:6]) if paper.authors else "作者信息缺失"
            if len(paper.authors) > 6:
                authors += " 等"

            lines.append(f"{index}. [{paper.title}]({paper.abstract_url})")
            lines.append(f"   - {paper.date_label}：{published}")
            lines.append(f"   - 作者：{authors}")
            lines.append(f"   - 来源：{paper.source}")
            lines.append(f"   - 分类：{', '.join(paper.categories)}")
            if paper.tags:
                lines.append(f"   - 标签：{' / '.join(paper.tags)}")
            if paper.topics:
                lines.append(f"   - 主题词：{' / '.join(paper.topics)}")
            if paper.pdf_url:
                lines.append(f"   - PDF：{paper.pdf_url}")
            if paper.analysis is not None:
                lines.append(f"   - 一句话结论：{paper.analysis.conclusion}")
                if paper.analysis.contributions:
                    lines.append(
                        "   - 主要贡献：" + "；".join(paper.analysis.contributions)
                    )
                if paper.analysis.audience:
                    lines.append(f"   - 适合谁看：{paper.analysis.audience}")
                if paper.analysis.limitations:
                    lines.append(
                        "   - 潜在局限：" + "；".join(paper.analysis.limitations)
                    )
            else:
                lines.append(f"   - 摘要：{paper.summary}")
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


def digest_has_papers(digest: DigestRun) -> bool:
    """Return True when the digest contains at least one paper."""

    return any(feed.papers for feed in digest.feeds)
