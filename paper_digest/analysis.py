"""Analysis orchestration for optional paper enrichment."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .arxiv_client import Paper, PaperAnalysis
from .config import AnalysisConfig, DigestTemplate
from .digest import DigestRun, TopicDigest
from .openai_analysis import OpenAIAnalysisError, analyze_paper_with_openai

_TOPIC_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+-]{2,}|[\u4e00-\u9fff]{2,}")
_TOPIC_STOPWORDS = {
    "about",
    "across",
    "analysis",
    "approach",
    "based",
    "efficient",
    "framework",
    "from",
    "large",
    "method",
    "model",
    "models",
    "paper",
    "papers",
    "results",
    "study",
    "system",
    "systems",
    "task",
    "tasks",
    "their",
    "these",
    "using",
    "with",
    "work",
}
_TAG_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "评测",
        (
            "benchmark",
            "evaluation",
            "leaderboard",
            "metric",
            "评测",
            "基准",
        ),
    ),
    (
        "数据",
        (
            "annotation",
            "corpus",
            "dataset",
            "datasets",
            "synthetic data",
            "数据集",
            "标注",
            "语料",
        ),
    ),
    (
        "应用",
        (
            "application",
            "assistant",
            "deployment",
            "healthcare",
            "medical",
            "robot",
            "search",
            "video",
            "workflow",
            "应用",
            "场景",
        ),
    ),
    (
        "方法",
        (
            "agent",
            "alignment",
            "algorithm",
            "architecture",
            "diffusion",
            "framework",
            "inference",
            "method",
            "model",
            "multimodal",
            "reasoning",
            "segmentation",
            "training",
            "方法",
            "推理",
            "模型",
            "算法",
            "训练",
        ),
    ),
)


class AnalysisError(RuntimeError):
    """Raised when configured analysis fails."""


def enrich_digest_with_analysis(
    config: AnalysisConfig,
    digest: DigestRun,
    *,
    template: DigestTemplate,
    top_highlights: int,
    feed_key_points: int,
    topic_candidates: Sequence[str] = (),
) -> None:
    """Mutate a digest in place with optional structured paper analysis."""

    papers_to_analyze = _select_papers_for_analysis(digest, config.max_papers)
    if papers_to_analyze:
        try:
            for paper in papers_to_analyze:
                paper.analysis = _analyze_paper(config, paper, template=template)
        except OpenAIAnalysisError as exc:
            raise AnalysisError(str(exc)) from exc

    apply_digest_briefing(
        digest,
        top_highlights=top_highlights,
        feed_key_points=feed_key_points,
        template=template,
        topic_candidates=topic_candidates,
    )


def apply_digest_briefing(
    digest: DigestRun,
    *,
    top_highlights: int,
    feed_key_points: int,
    template: DigestTemplate,
    topic_candidates: Sequence[str] = (),
) -> None:
    """Populate render-ready highlights, topics, and key points."""

    digest.template = template
    for paper in _iter_papers(digest):
        paper.tags = build_paper_tags(paper)

    digest.topic_sections = build_topic_sections(
        digest,
        max_items=max(top_highlights, 5),
        topic_candidates=topic_candidates,
        template=template,
    )
    digest.highlights = build_digest_highlights(
        digest,
        top_highlights,
        template=template,
    )
    for feed in digest.feeds:
        feed.key_points = build_feed_key_points(
            feed.papers,
            feed_key_points,
            template=template,
        )


def build_digest_highlights(
    digest: DigestRun,
    max_items: int,
    *,
    template: DigestTemplate = "default",
) -> list[str]:
    """Build compact highlight lines from analyzed papers or rule-based topics."""

    if template == "zh_daily_brief" and digest.topic_sections:
        return [
            _format_topic_highlight(topic)
            for topic in digest.topic_sections[:max_items]
        ]

    highlights: list[str] = []
    for feed in digest.feeds:
        for paper in feed.papers:
            summary_line = _highlight_text(paper)
            if not summary_line:
                continue
            highlights.append(
                _format_digest_highlight(
                    feed.name,
                    paper.title,
                    summary_line,
                    template,
                )
            )
            if len(highlights) >= max_items:
                return highlights
    return highlights


def build_feed_key_points(
    papers: list[Paper],
    max_items: int,
    *,
    template: DigestTemplate = "default",
) -> list[str]:
    """Build compact feed-level key points from analyzed or raw papers."""

    key_points: list[str] = []
    for paper in papers:
        summary_line = _highlight_text(paper)
        if not summary_line:
            continue
        key_points.append(
            _format_feed_key_point(
                paper.title,
                summary_line,
                template,
                tags=paper.tags,
            )
        )
        if len(key_points) >= max_items:
            return key_points
    return key_points


def build_topic_sections(
    digest: DigestRun,
    *,
    max_items: int,
    topic_candidates: Sequence[str] = (),
    template: DigestTemplate = "default",
) -> list[TopicDigest]:
    """Build compact topic clusters for the digest."""

    candidate_pairs = _normalize_topic_candidates(topic_candidates)
    topic_counts = _build_topic_frequency_index(digest, candidate_pairs)
    buckets: dict[str, TopicDigest] = {}
    topic_scores: dict[str, int] = {}
    for feed in digest.feeds:
        for paper in feed.papers:
            paper.topics = _extract_paper_topics(
                paper,
                candidate_pairs,
                topic_counts,
            )
            if not paper.topics:
                continue

            for topic_name in paper.topics:
                bucket = buckets.setdefault(
                    topic_name,
                    TopicDigest(
                        name=topic_name,
                        paper_count=0,
                        feed_names=[],
                        paper_titles=[],
                        key_points=[],
                    ),
                )
                bucket.paper_count += 1
                if feed.name not in bucket.feed_names:
                    bucket.feed_names.append(feed.name)
                if paper.title not in bucket.paper_titles:
                    bucket.paper_titles.append(paper.title)
                point = _format_topic_key_point(
                    paper,
                    template=template,
                )
                if point not in bucket.key_points and len(bucket.key_points) < 2:
                    bucket.key_points.append(point)
                topic_scores[topic_name] = max(
                    topic_scores.get(topic_name, 0),
                    paper.relevance_score,
                )

    return sorted(
        buckets.values(),
        key=lambda topic: (
            -topic.paper_count,
            -topic_scores.get(topic.name, 0),
            -len(topic.feed_names),
            topic.name,
        ),
    )[:max_items]


def build_paper_tags(paper: Paper) -> list[str]:
    """Assign a small set of rule-based briefing tags to a paper."""

    haystack = _match_text(paper)
    tags = [
        tag
        for tag, needles in _TAG_RULES
        if any(needle in haystack for needle in needles)
    ]
    if tags:
        return tags
    return ["方法"]


def _iter_papers(digest: DigestRun) -> list[Paper]:
    papers: list[Paper] = []
    for feed in digest.feeds:
        papers.extend(feed.papers)
    return papers


def _normalize_topic_candidates(
    topic_candidates: Sequence[str],
) -> list[tuple[str, str]]:
    seen: set[str] = set()
    normalized: list[tuple[str, str]] = []
    for candidate in topic_candidates:
        stripped = candidate.strip()
        needle = stripped.lower()
        if not stripped or needle in seen:
            continue
        seen.add(needle)
        normalized.append((needle, _display_topic(stripped)))
    return normalized


def _build_topic_frequency_index(
    digest: DigestRun,
    candidate_pairs: Sequence[tuple[str, str]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for paper in _iter_papers(digest):
        paper_terms: set[str] = set()
        haystack = _match_text(paper)
        for needle, display in candidate_pairs:
            if needle in haystack:
                paper_terms.add(display)
        paper_terms.update(_extract_topic_terms(paper.title)[:4])
        paper_terms.update(_extract_topic_terms(paper.summary)[:6])
        for term in paper_terms:
            counts[term] = counts.get(term, 0) + 1
    return counts


def _extract_paper_topics(
    paper: Paper,
    candidate_pairs: Sequence[tuple[str, str]],
    topic_counts: dict[str, int],
) -> list[str]:
    haystack = _match_text(paper)
    matched_candidates = [
        display for needle, display in candidate_pairs if needle in haystack
    ]
    if matched_candidates:
        return sorted(
            matched_candidates,
            key=lambda term: (-topic_counts.get(term, 0), term),
        )[:2]

    fallback_terms = _extract_topic_terms(paper.title)
    fallback_terms.extend(
        term
        for term in _extract_topic_terms(paper.summary)
        if term not in fallback_terms
    )
    if not fallback_terms:
        return []

    frequent_terms = [
        term for term in fallback_terms if topic_counts.get(term, 0) >= 2
    ]
    if frequent_terms:
        return sorted(
            frequent_terms,
            key=lambda term: (-topic_counts.get(term, 0), fallback_terms.index(term)),
        )[:2]
    return fallback_terms[:2]


def _extract_topic_terms(value: str) -> list[str]:
    seen: set[str] = set()
    topics: list[str] = []
    for token in _TOPIC_TOKEN_PATTERN.findall(value):
        normalized = token.lower()
        if normalized in _TOPIC_STOPWORDS:
            continue
        display = _display_topic(token)
        if display.lower() in seen:
            continue
        seen.add(display.lower())
        topics.append(display)
    return topics


def _display_topic(value: str) -> str:
    if any("\u4e00" <= char <= "\u9fff" for char in value):
        return value
    parts = re.split(r"[\s_-]+", value)
    normalized_parts = []
    for part in parts:
        if not part:
            continue
        if part.isupper() or len(part) <= 4:
            normalized_parts.append(part.upper())
        else:
            normalized_parts.append(part.capitalize())
    return " ".join(normalized_parts)


def _match_text(paper: Paper) -> str:
    return f"{paper.title}\n{paper.summary}".lower()


def _select_papers_for_analysis(digest: DigestRun, max_papers: int) -> list[Paper]:
    selected: list[Paper] = []
    index = 0

    while len(selected) < max_papers:
        added = False
        for feed in digest.feeds:
            if index < len(feed.papers):
                selected.append(feed.papers[index])
                added = True
                if len(selected) >= max_papers:
                    break
        if not added:
            break
        index += 1
    return selected


def _analyze_paper(
    config: AnalysisConfig,
    paper: Paper,
    *,
    template: DigestTemplate,
) -> PaperAnalysis:
    if config.provider == "openai":
        return analyze_paper_with_openai(config, paper, template=template)
    raise AnalysisError(f"unsupported analysis provider: {config.provider}")


def _highlight_text(paper: Paper) -> str:
    if paper.analysis is not None:
        return _truncate_text(paper.analysis.conclusion, 160)
    return _truncate_text(paper.summary, 160)


def _format_digest_highlight(
    feed_name: str,
    paper_title: str,
    summary_line: str,
    template: DigestTemplate,
) -> str:
    if template == "zh_daily_brief":
        return f"{feed_name}：关注《{paper_title}》，今日要点：{summary_line}"
    return f"{feed_name}: {paper_title} - {summary_line}"


def _format_topic_highlight(topic: TopicDigest) -> str:
    feed_label = "、".join(topic.feed_names[:2])
    if len(topic.feed_names) > 2:
        feed_label += " 等"
    title_label = "、".join(f"《{title}》" for title in topic.paper_titles[:2])
    return (
        f"主题「{topic.name}」：命中 {topic.paper_count} 篇，覆盖 {feed_label}，"
        f"代表论文包括 {title_label}。"
    )


def _format_feed_key_point(
    paper_title: str,
    summary_line: str,
    template: DigestTemplate,
    *,
    tags: Sequence[str],
) -> str:
    if template == "zh_daily_brief":
        tag_label = f"〔{' / '.join(tags)}〕" if tags else ""
        return f"《{paper_title}》{tag_label}：{summary_line}"
    return f"{paper_title}: {summary_line}"


def _format_topic_key_point(
    paper: Paper,
    *,
    template: DigestTemplate,
) -> str:
    summary_line = _highlight_text(paper)
    tag_label = f"〔{' / '.join(paper.tags)}〕" if paper.tags else ""
    if template == "zh_daily_brief":
        return f"《{paper.title}》{tag_label}：{summary_line}"
    return f"{paper.title}: {summary_line}"


def _truncate_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
