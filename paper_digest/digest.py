"""Digest filtering and rendering helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .arxiv_client import Paper
from .config import (
    AppConfig,
    DigestTemplate,
    FeedConfig,
    RankingConfig,
    RankingWeights,
    SortMode,
)
from .feedback import feedback_label, feedback_label_zh


@dataclass(slots=True)
class FeedDigest:
    name: str
    papers: list[Paper]
    key_points: list[str] = field(default_factory=list)
    sort_by: SortMode = "hybrid"


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
    default_sort_by: SortMode = "hybrid"
    sort_summary: str = ""
    ranking_weights: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        sort_summary = self.sort_summary or _sort_mode_description(self.default_sort_by)
        return {
            "generated_at": self.generated_at.isoformat(),
            "timezone": self.timezone,
            "lookback_hours": self.lookback_hours,
            "sorting": {
                "default_sort_by": self.default_sort_by,
                "summary": sort_summary,
                "weights": dict(self.ranking_weights),
                "feeds": [
                    {
                        "name": feed.name,
                        "sort_by": feed.sort_by,
                    }
                    for feed in self.feeds
                ],
            },
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
                    "sort_by": feed.sort_by,
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
    ranking: RankingConfig,
) -> list[Paper]:
    cutoff = now - timedelta(hours=lookback_hours)
    filtered: list[Paper] = []

    for paper in papers:
        if paper.published_at < cutoff:
            continue
        title_hits = _keyword_hits(paper.title, feed.keywords)
        summary_hits = [
            keyword
            for keyword in _keyword_hits(paper.summary, feed.keywords)
            if keyword.casefold() not in {item.casefold() for item in title_hits}
        ]
        if feed.keywords and not (title_hits or summary_hits):
            continue
        if feed.exclude_keywords and _matches_any_keyword(paper, feed.exclude_keywords):
            continue
        paper.match_reasons = _build_match_reasons(
            paper,
            title_hits=title_hits,
            summary_hits=summary_hits,
        )
        paper.base_relevance_score = _compute_relevance_score(
            paper,
            title_hits=title_hits,
            summary_hits=summary_hits,
            now=now,
            lookback_hours=lookback_hours,
            weights=ranking.weights,
        )
        paper.relevance_score = paper.base_relevance_score
        filtered.append(paper)

    filtered.sort(
        key=lambda item: _paper_sort_key(
            item,
            sort_by=_effective_sort_mode(feed.sort_by, ranking.sort_by),
        )
    )
    return filtered[: feed.max_items]


def finalize_digest_scoring(digest: DigestRun, *, ranking: RankingConfig) -> None:
    """Apply cross-source ranking bonuses and final paper ordering."""

    digest.default_sort_by = ranking.sort_by
    digest.ranking_weights = _ranking_weights_dict(ranking.weights)
    for feed in digest.feeds:
        for paper in feed.papers:
            paper.match_reasons = _finalize_match_reasons(paper)
            paper.relevance_score = (
                paper.base_relevance_score
                + _cross_source_score_bonus(paper, ranking.weights)
            )
        feed.papers.sort(key=lambda item: _paper_sort_key(item, sort_by=feed.sort_by))
    digest.sort_summary = _build_sort_summary(digest)


def render_markdown(digest: DigestRun) -> str:
    if digest.template == "zh_daily_brief":
        return _render_zh_daily_brief(digest)
    return _render_default_markdown(digest)


def _render_default_markdown(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    sort_summary = digest.sort_summary or _sort_mode_description(digest.default_sort_by)

    lines = [
        "# Daily Paper Digest",
        "",
        f"- Generated at: {generated_at} ({digest.timezone})",
        f"- Lookback window: last {digest.lookback_hours} hours",
        f"- Sorting: {sort_summary}",
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
            lines.append(f"   - Source: {paper.source_label()}")
            feedback = feedback_label(paper.feedback_status)
            if feedback is not None:
                lines.append(f"   - Feedback: {feedback}")
            if paper.relevance_score:
                lines.append(f"   - Relevance: {paper.relevance_score}")
            if paper.match_reasons:
                lines.append(
                    "   - Match Reasons: "
                    + paper.match_reason_label(limit=4)
                )
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
    sort_summary = digest.sort_summary or _sort_mode_description(digest.default_sort_by)

    lines = [
        "# 每日论文简报",
        "",
        f"- 生成时间：{generated_at} ({digest.timezone})",
        f"- 检索窗口：最近 {digest.lookback_hours} 小时",
        f"- 命中概览：{summarize_digest(digest)}",
        f"- 排序策略：{sort_summary}",
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
            lines.append(f"   - 来源：{paper.source_label()}")
            feedback = feedback_label_zh(paper.feedback_status)
            if feedback is not None:
                lines.append(f"   - 反馈状态：{feedback}")
            if paper.relevance_score:
                lines.append(f"   - 相关性分数：{paper.relevance_score}")
            if paper.match_reasons:
                lines.append(
                    "   - 命中原因：" + paper.match_reason_label(limit=4)
                )
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


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    haystack = text.casefold()
    hits: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        normalized = keyword.strip()
        needle = normalized.casefold()
        if not normalized or needle in seen:
            continue
        if needle in haystack:
            seen.add(needle)
            hits.append(normalized)
    return hits


def _build_match_reasons(
    paper: Paper,
    *,
    title_hits: list[str],
    summary_hits: list[str],
) -> list[str]:
    reasons = [f'title matched "{keyword}"' for keyword in title_hits]
    reasons.extend(f'summary matched "{keyword}"' for keyword in summary_hits)
    if paper.doi:
        reasons.append("has DOI")
    if paper.pdf_url:
        reasons.append("has PDF")
    if paper.summary and len(paper.summary) >= 120:
        reasons.append("has rich summary")
    if paper.authors and paper.categories:
        reasons.append("has complete metadata")
    return _merge_unique_reasons(reasons)


def _compute_relevance_score(
    paper: Paper,
    *,
    title_hits: list[str],
    summary_hits: list[str],
    now: datetime,
    lookback_hours: int,
    weights: RankingWeights,
) -> int:
    age_hours = max((now - paper.published_at).total_seconds() / 3600, 0.0)
    freshness_bonus = max(
        0,
        min(weights.freshness_weight_cap, int(lookback_hours - age_hours)),
    )
    summary_bonus = weights.rich_summary_weight if len(paper.summary) >= 120 else 0
    metadata_bonus = (
        weights.metadata_weight if paper.authors and paper.categories else 0
    )
    return (
        len(title_hits) * weights.title_match_weight
        + len(summary_hits) * weights.summary_match_weight
        + (weights.doi_weight if paper.doi else 0)
        + (weights.pdf_weight if paper.pdf_url else 0)
        + summary_bonus
        + metadata_bonus
        + freshness_bonus
    )


def _cross_source_score_bonus(paper: Paper, weights: RankingWeights) -> int:
    extra_sources = max(len(paper.source_variants) - 1, 0)
    return extra_sources * weights.multi_source_weight


def _finalize_match_reasons(paper: Paper) -> list[str]:
    reasons = [
        reason
        for reason in paper.match_reasons
        if not reason.startswith("seen in ")
    ]
    if len(paper.source_variants) > 1:
        reasons.append(f"seen in {len(paper.source_variants)} sources")
    return _merge_unique_reasons(reasons)


def _merge_unique_reasons(reasons: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        normalized = reason.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def _paper_sort_key(
    paper: Paper,
    *,
    sort_by: SortMode,
) -> tuple[int | float | str, ...]:
    if sort_by == "published_at":
        return (
            -paper.published_at.timestamp(),
            -paper.relevance_score,
            paper.title.casefold(),
        )
    if sort_by == "relevance":
        return (
            -paper.relevance_score,
            -len(paper.source_variants),
            paper.title.casefold(),
        )
    return (
        -paper.relevance_score,
        -paper.published_at.timestamp(),
        paper.title.casefold(),
    )


def _effective_sort_mode(
    feed_sort_by: SortMode | None,
    default_sort_by: SortMode,
) -> SortMode:
    return default_sort_by if feed_sort_by is None else feed_sort_by


def _build_sort_summary(digest: DigestRun) -> str:
    if not digest.feeds:
        return _sort_mode_description(digest.default_sort_by)

    distinct_modes = {feed.sort_by for feed in digest.feeds}
    if len(distinct_modes) == 1:
        mode = next(iter(distinct_modes))
        return _sort_mode_description(mode)

    per_feed = ", ".join(f"{feed.name}={feed.sort_by}" for feed in digest.feeds)
    return f"mixed ({per_feed})"


def _sort_mode_description(sort_by: SortMode) -> str:
    if sort_by == "relevance":
        return "relevance (score-first ranking; recency only breaks exact ties)"
    if sort_by == "published_at":
        return "published_at (newest first; relevance is auxiliary)"
    return "hybrid (relevance first, published_at tie-break)"


def _ranking_weights_dict(weights: RankingWeights) -> dict[str, int]:
    return {
        "title_match_weight": weights.title_match_weight,
        "summary_match_weight": weights.summary_match_weight,
        "doi_weight": weights.doi_weight,
        "pdf_weight": weights.pdf_weight,
        "rich_summary_weight": weights.rich_summary_weight,
        "metadata_weight": weights.metadata_weight,
        "multi_source_weight": weights.multi_source_weight,
        "freshness_weight_cap": weights.freshness_weight_cap,
    }


def summarize_digest(digest: DigestRun) -> str:
    """Return a compact human-readable summary of per-feed counts."""

    if not digest.feeds:
        return "no feeds"
    return ", ".join(f"{feed.name}={len(feed.papers)}" for feed in digest.feeds)


def digest_has_papers(digest: DigestRun) -> bool:
    """Return True when the digest contains at least one paper."""

    return any(feed.papers for feed in digest.feeds)
