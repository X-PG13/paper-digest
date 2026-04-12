"""Digest filtering and rendering helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .arxiv_client import Paper
from .config import (
    AppConfig,
    DigestTemplate,
    FeedbackStatus,
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
class FocusItem:
    canonical_id: str
    title: str
    abstract_url: str
    summary: str
    source_label: str
    feedback_status: FeedbackStatus
    reasons: list[str]
    feedback_note: str | None = None
    feed_names: list[str] = field(default_factory=list)
    relevance_score: int = 0
    active_days: int = 1
    active_feeds: int = 1
    appearance_count: int = 1
    first_seen: datetime | None = None
    last_seen: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_id": self.canonical_id,
            "title": self.title,
            "abstract_url": self.abstract_url,
            "summary": self.summary,
            "source_label": self.source_label,
            "feedback_status": self.feedback_status,
            "feedback_note": self.feedback_note,
            "reasons": list(self.reasons),
            "feed_names": list(self.feed_names),
            "relevance_score": self.relevance_score,
            "active_days": self.active_days,
            "active_feeds": self.active_feeds,
            "appearance_count": self.appearance_count,
            "first_seen": (
                self.first_seen.isoformat() if self.first_seen is not None else None
            ),
            "last_seen": (
                self.last_seen.isoformat() if self.last_seen is not None else None
            ),
        }


@dataclass(slots=True)
class ActionItem:
    canonical_id: str
    title: str
    abstract_url: str
    summary: str
    source_label: str
    feedback_status: FeedbackStatus
    reasons: list[str]
    feedback_note: str | None = None
    next_action: str | None = None
    due_date: date | None = None
    days_until_due: int | None = None
    review_interval_days: int | None = None
    feed_names: list[str] = field(default_factory=list)
    relevance_score: int = 0
    active_days: int = 1
    active_feeds: int = 1
    appearance_count: int = 1
    first_seen: datetime | None = None
    last_seen: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_id": self.canonical_id,
            "title": self.title,
            "abstract_url": self.abstract_url,
            "summary": self.summary,
            "source_label": self.source_label,
            "feedback_status": self.feedback_status,
            "feedback_note": self.feedback_note,
            "next_action": self.next_action,
            "due_date": (
                self.due_date.isoformat() if self.due_date is not None else None
            ),
            "days_until_due": self.days_until_due,
            "review_interval_days": self.review_interval_days,
            "reasons": list(self.reasons),
            "feed_names": list(self.feed_names),
            "relevance_score": self.relevance_score,
            "active_days": self.active_days,
            "active_feeds": self.active_feeds,
            "appearance_count": self.appearance_count,
            "first_seen": (
                self.first_seen.isoformat() if self.first_seen is not None else None
            ),
            "last_seen": (
                self.last_seen.isoformat() if self.last_seen is not None else None
            ),
        }


@dataclass(slots=True)
class DigestRun:
    generated_at: datetime
    timezone: str
    lookback_hours: int
    feeds: list[FeedDigest]
    highlights: list[str] = field(default_factory=list)
    focus_items: list[FocusItem] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
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
            "focus_items": [item.to_dict() for item in self.focus_items],
            "action_items": [item.to_dict() for item in self.action_items],
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
    return render_notification_markdown(digest, feedback_only=False)


def render_notification_markdown(
    digest: DigestRun,
    *,
    feedback_only: bool,
) -> str:
    if feedback_only:
        return render_feedback_brief_markdown(digest)
    if digest.template == "zh_daily_brief":
        return _render_zh_daily_brief(digest)
    return _render_default_markdown(digest)


def render_feedback_brief_markdown(digest: DigestRun) -> str:
    if digest.template == "zh_daily_brief":
        return _render_zh_focus_only_brief(digest)
    return _render_default_focus_only_markdown(digest)


def render_focus_brief_markdown(digest: DigestRun) -> str:
    if digest.template == "zh_daily_brief":
        return _render_zh_focus_brief_only(digest)
    return _render_default_focus_brief_only(digest)


def render_action_brief_markdown(digest: DigestRun) -> str:
    if digest.template == "zh_daily_brief":
        return _render_zh_action_only_brief(digest)
    return _render_default_action_only_markdown(digest)


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

    focus_lines = _render_focus_lines(digest, language="en")
    if focus_lines:
        lines.extend(focus_lines)
        lines.append("")

    action_lines = _render_action_lines(digest, language="en")
    if action_lines:
        lines.extend(action_lines)
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
            if paper.feedback_note:
                lines.append(f"   - Note: {paper.feedback_note}")
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

    focus_lines = _render_focus_lines(digest, language="zh")
    if focus_lines:
        lines.extend(focus_lines)
        lines.append("")

    action_lines = _render_action_lines(digest, language="zh")
    if action_lines:
        lines.extend(action_lines)
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
            if paper.feedback_note:
                lines.append(f"   - 备注：{paper.feedback_note}")
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


def _render_default_focus_only_markdown(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    lines = [
        "# Daily Paper Focus",
        "",
        f"- Generated at: {generated_at} ({digest.timezone})",
        f"- Lookback window: last {digest.lookback_hours} hours",
        f"- Focus summary: {summarize_focus_items(digest)}",
        "",
    ]
    focus_lines = _render_focus_lines(digest, language="en")
    if focus_lines:
        lines.extend(focus_lines)
    action_lines = _render_action_lines(digest, language="en")
    if action_lines:
        if focus_lines:
            lines.append("")
        lines.extend(action_lines)
    if not focus_lines and not action_lines:
        lines.extend(
            [
                "## Focus",
                "",
                "No feedback-triggered papers for this run.",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _render_default_focus_brief_only(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    lines = [
        "# Daily Paper Focus",
        "",
        f"- Generated at: {generated_at} ({digest.timezone})",
        f"- Lookback window: last {digest.lookback_hours} hours",
        f"- Focus summary: {summarize_focus_items(digest)}",
        "",
    ]
    focus_lines = _render_focus_lines(digest, language="en")
    if focus_lines:
        lines.extend(focus_lines)
    else:
        lines.extend(
            [
                "## Focus",
                "",
                "No feedback-triggered papers for this run.",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _render_zh_focus_only_brief(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    lines = [
        "# 每日关注清单",
        "",
        f"- 生成时间：{generated_at} ({digest.timezone})",
        f"- 检索窗口：最近 {digest.lookback_hours} 小时",
        f"- Focus 概览：{summarize_focus_items(digest)}",
        "",
    ]
    focus_lines = _render_focus_lines(digest, language="zh")
    if focus_lines:
        lines.extend(focus_lines)
    action_lines = _render_action_lines(digest, language="zh")
    if action_lines:
        if focus_lines:
            lines.append("")
        lines.extend(action_lines)
    if not focus_lines and not action_lines:
        lines.extend(
            [
                "## Focus 区块",
                "",
                "本次没有触发反馈驱动的关注论文。",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _render_zh_focus_brief_only(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    lines = [
        "# 每日关注清单",
        "",
        f"- 生成时间：{generated_at} ({digest.timezone})",
        f"- 检索窗口：最近 {digest.lookback_hours} 小时",
        f"- Focus 概览：{summarize_focus_items(digest)}",
        "",
    ]
    focus_lines = _render_focus_lines(digest, language="zh")
    if focus_lines:
        lines.extend(focus_lines)
    else:
        lines.extend(
            [
                "## Focus 区块",
                "",
                "本次没有触发反馈驱动的关注论文。",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _render_default_action_only_markdown(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    lines = [
        "# Daily Action Brief",
        "",
        f"- Generated at: {generated_at} ({digest.timezone})",
        f"- Lookback window: last {digest.lookback_hours} hours",
        f"- Action summary: {summarize_action_items(digest)}",
        "",
    ]
    action_lines = _render_action_lines(digest, language="en")
    if action_lines:
        lines.extend(action_lines)
    else:
        lines.extend(
            [
                "## What To Review This Week",
                "",
                "No action reminders for this run.",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _render_zh_action_only_brief(digest: DigestRun) -> str:
    local_tz = ZoneInfo(digest.timezone)
    generated_at = digest.generated_at.astimezone(local_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    lines = [
        "# 每日行动简报",
        "",
        f"- 生成时间：{generated_at} ({digest.timezone})",
        f"- 检索窗口：最近 {digest.lookback_hours} 小时",
        f"- 行动概览：{summarize_action_items(digest)}",
        "",
    ]
    action_lines = _render_action_lines(digest, language="zh")
    if action_lines:
        lines.extend(action_lines)
    else:
        lines.extend(
            [
                "## 本周该处理什么",
                "",
                "本次没有触发行动提醒。",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _render_focus_lines(digest: DigestRun, *, language: str) -> list[str]:
    if not digest.focus_items:
        return []

    local_tz = ZoneInfo(digest.timezone)
    heading = "## Focus" if language == "en" else "## Focus 区块"
    lines = [heading, ""]
    for index, item in enumerate(digest.focus_items, start=1):
        lines.append(f"{index}. [{item.title}]({item.abstract_url})")
        if language == "en":
            lines.append(
                "   - Feedback: "
                + (feedback_label(item.feedback_status) or item.feedback_status)
            )
            if item.feedback_note:
                lines.append(f"   - Note: {item.feedback_note}")
            lines.append(
                "   - Why it was pushed: "
                + "; ".join(
                    _focus_reason_label(reason, language=language)
                    for reason in item.reasons
                )
            )
            if item.feed_names:
                lines.append("   - Feeds: " + ", ".join(item.feed_names))
            lines.append(
                "   - Coverage: "
                f"{item.active_days} active days / {item.active_feeds} feeds / "
                f"{item.appearance_count} appearances"
            )
            if item.first_seen is not None and item.last_seen is not None:
                first_seen = item.first_seen.astimezone(local_tz).strftime(
                    "%Y-%m-%d %H:%M"
                )
                last_seen = item.last_seen.astimezone(local_tz).strftime(
                    "%Y-%m-%d %H:%M"
                )
                seen_window = (
                    f"{first_seen} -> "
                    f"{last_seen}"
                )
                lines.append(
                    "   - Seen Window: "
                    f"{seen_window}"
                )
            lines.append(f"   - Source: {item.source_label}")
            if item.relevance_score:
                lines.append(f"   - Relevance: {item.relevance_score}")
            lines.append(f"   - Summary: {item.summary}")
        else:
            lines.append(
                "   - 反馈状态："
                + (feedback_label_zh(item.feedback_status) or item.feedback_status)
            )
            if item.feedback_note:
                lines.append(f"   - 备注：{item.feedback_note}")
            lines.append(
                "   - 推送原因："
                + "；".join(
                    _focus_reason_label(reason, language=language)
                    for reason in item.reasons
                )
            )
            if item.feed_names:
                lines.append("   - 覆盖分组：" + "、".join(item.feed_names))
            lines.append(
                "   - 覆盖跨度："
                f"{item.active_days} 天 / {item.active_feeds} 个 feed / "
                f"{item.appearance_count} 次命中"
            )
            if item.first_seen is not None and item.last_seen is not None:
                first_seen = item.first_seen.astimezone(local_tz).strftime(
                    "%Y-%m-%d %H:%M"
                )
                last_seen = item.last_seen.astimezone(local_tz).strftime(
                    "%Y-%m-%d %H:%M"
                )
                seen_window = (
                    f"{first_seen} -> "
                    f"{last_seen}"
                )
                lines.append(
                    "   - 历史窗口："
                    f"{seen_window}"
                )
            lines.append(f"   - 来源：{item.source_label}")
            if item.relevance_score:
                lines.append(f"   - 相关性分数：{item.relevance_score}")
            lines.append(f"   - 摘要：{item.summary}")
        lines.append("")
    return lines


def _render_action_lines(digest: DigestRun, *, language: str) -> list[str]:
    if not digest.action_items:
        return []

    local_tz = ZoneInfo(digest.timezone)
    heading = (
        "## What To Review This Week"
        if language == "en"
        else "## 本周该处理什么"
    )
    lines = [heading, ""]
    for index, item in enumerate(digest.action_items, start=1):
        lines.append(f"{index}. [{item.title}]({item.abstract_url})")
        if language == "en":
            lines.append(
                "   - Feedback: "
                + (feedback_label(item.feedback_status) or item.feedback_status)
            )
            if item.due_date is not None:
                lines.append(
                    "   - Due: "
                    + _action_due_label(item, language=language)
                )
            if item.next_action:
                lines.append(f"   - Next Action: {item.next_action}")
            if item.review_interval_days is not None:
                lines.append(
                    "   - Review Cadence: "
                    f"every {item.review_interval_days} day(s)"
                )
            if item.feedback_note:
                lines.append(f"   - Note: {item.feedback_note}")
            lines.append(
                "   - Why now: "
                + "; ".join(
                    _action_reason_label(reason, language=language)
                    for reason in item.reasons
                )
            )
            if item.feed_names:
                lines.append("   - Feeds: " + ", ".join(item.feed_names))
            lines.append(
                "   - Coverage: "
                f"{item.active_days} active days / {item.active_feeds} feeds / "
                f"{item.appearance_count} appearances"
            )
            if item.first_seen is not None and item.last_seen is not None:
                first_seen = item.first_seen.astimezone(local_tz).strftime(
                    "%Y-%m-%d %H:%M"
                )
                last_seen = item.last_seen.astimezone(local_tz).strftime(
                    "%Y-%m-%d %H:%M"
                )
                lines.append(f"   - Seen Window: {first_seen} -> {last_seen}")
            lines.append(f"   - Source: {item.source_label}")
            if item.relevance_score:
                lines.append(f"   - Relevance: {item.relevance_score}")
            lines.append(f"   - Summary: {item.summary}")
        else:
            lines.append(
                "   - 反馈状态："
                + (feedback_label_zh(item.feedback_status) or item.feedback_status)
            )
            if item.due_date is not None:
                lines.append(
                    "   - 最晚处理："
                    + _action_due_label(item, language=language)
                )
            if item.next_action:
                lines.append(f"   - 下一步：{item.next_action}")
            if item.review_interval_days is not None:
                lines.append(f"   - 复查周期：每 {item.review_interval_days} 天")
            if item.feedback_note:
                lines.append(f"   - 备注：{item.feedback_note}")
            lines.append(
                "   - 为什么现在看："
                + "；".join(
                    _action_reason_label(reason, language=language)
                    for reason in item.reasons
                )
            )
            if item.feed_names:
                lines.append("   - 覆盖分组：" + "、".join(item.feed_names))
            lines.append(
                "   - 覆盖跨度："
                f"{item.active_days} 天 / {item.active_feeds} 个 feed / "
                f"{item.appearance_count} 次命中"
            )
            if item.first_seen is not None and item.last_seen is not None:
                first_seen = item.first_seen.astimezone(local_tz).strftime(
                    "%Y-%m-%d %H:%M"
                )
                last_seen = item.last_seen.astimezone(local_tz).strftime(
                    "%Y-%m-%d %H:%M"
                )
                lines.append(f"   - 历史窗口：{first_seen} -> {last_seen}")
            lines.append(f"   - 来源：{item.source_label}")
            if item.relevance_score:
                lines.append(f"   - 相关性分数：{item.relevance_score}")
            lines.append(f"   - 摘要：{item.summary}")
        lines.append("")
    return lines


def _focus_reason_label(reason: str, *, language: str) -> str:
    labels = {
        "new_starred": {
            "en": "newly starred within the current lookback window",
            "zh": "最近刚标星",
        },
        "follow_up_resurfaced": {
            "en": "follow-up paper resurfaced in today's source scan",
            "zh": "待跟进论文今天再次出现",
        },
        "starred_momentum": {
            "en": "starred paper entered momentum",
            "zh": "已标星论文进入持续升温",
        },
    }
    return labels.get(reason, {}).get(language, reason)


def _action_reason_label(reason: str, *, language: str) -> str:
    labels = {
        "overdue": {
            "en": "already overdue",
            "zh": "已经逾期",
        },
        "overdue_1d": {
            "en": "overdue for at least 1 day",
            "zh": "已逾期至少 1 天",
        },
        "overdue_3d": {
            "en": "overdue for at least 3 days",
            "zh": "已逾期至少 3 天",
        },
        "overdue_7d": {
            "en": "overdue for at least 7 days",
            "zh": "已逾期至少 7 天",
        },
        "due_soon": {
            "en": "due within 3 days",
            "zh": "3 天内到期",
        },
        "next_action_pending": {
            "en": "next action is set but not started",
            "zh": "已设下一步动作但还没开始",
        },
        "recurring_review": {
            "en": "entered its recurring review window",
            "zh": "进入周期性复查窗口",
        },
    }
    return labels.get(reason, {}).get(language, reason)


def _action_due_label(item: ActionItem, *, language: str) -> str:
    if item.due_date is None:
        return ""
    base = item.due_date.isoformat()
    if item.days_until_due is None:
        return base
    if item.days_until_due < 0:
        overdue_days = abs(item.days_until_due)
        if language == "en":
            suffix = f"overdue by {overdue_days} day(s)"
        else:
            suffix = f"已逾期 {overdue_days} 天"
        return f"{base} ({suffix})"
    if item.days_until_due == 0:
        suffix = "due today" if language == "en" else "今天到期"
        return f"{base} ({suffix})"
    if language == "en":
        suffix = f"due in {item.days_until_due} day(s)"
    else:
        suffix = f"{item.days_until_due} 天后到期"
    return f"{base} ({suffix})"


def summarize_focus_items(digest: DigestRun) -> str:
    if not digest.focus_items:
        return "Focus=0"
    starred = sum(1 for item in digest.focus_items if item.feedback_status == "star")
    follow_up = sum(
        1 for item in digest.focus_items if item.feedback_status == "follow_up"
    )
    parts = [f"Focus={len(digest.focus_items)}"]
    if starred:
        parts.append(f"star={starred}")
    if follow_up:
        parts.append(f"follow_up={follow_up}")
    return ", ".join(parts)


def summarize_action_items(digest: DigestRun) -> str:
    if not digest.action_items:
        return "Actions=0"
    overdue = sum(
        1 for item in digest.action_items if "overdue" in item.reasons
    )
    due_soon = sum(
        1 for item in digest.action_items if "due_soon" in item.reasons
    )
    next_action = sum(
        1 for item in digest.action_items if "next_action_pending" in item.reasons
    )
    recurring = sum(
        1 for item in digest.action_items if "recurring_review" in item.reasons
    )
    parts = [f"Actions={len(digest.action_items)}"]
    if overdue:
        parts.append(f"overdue={overdue}")
    if due_soon:
        parts.append(f"due_soon={due_soon}")
    if next_action:
        parts.append(f"next_action={next_action}")
    if recurring:
        parts.append(f"recurring={recurring}")
    return ", ".join(parts)


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
