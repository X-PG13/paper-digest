"""Analysis orchestration for optional paper enrichment."""

from __future__ import annotations

from .arxiv_client import Paper, PaperAnalysis
from .config import AnalysisConfig, AnalysisTemplate
from .digest import DigestRun
from .openai_analysis import OpenAIAnalysisError, analyze_paper_with_openai


class AnalysisError(RuntimeError):
    """Raised when configured analysis fails."""


def enrich_digest_with_analysis(config: AnalysisConfig, digest: DigestRun) -> None:
    """Mutate a digest in place with optional structured paper analysis."""

    digest.template = config.template
    papers_to_analyze = _select_papers_for_analysis(digest, config.max_papers)
    if papers_to_analyze:
        try:
            for paper in papers_to_analyze:
                paper.analysis = _analyze_paper(config, paper)
        except OpenAIAnalysisError as exc:
            raise AnalysisError(str(exc)) from exc

    digest.highlights = build_digest_highlights(
        digest,
        config.top_highlights,
        template=config.template,
    )
    for feed in digest.feeds:
        feed.key_points = build_feed_key_points(
            feed.papers,
            config.feed_key_points,
            template=config.template,
        )


def build_digest_highlights(
    digest: DigestRun,
    max_items: int,
    *,
    template: AnalysisTemplate = "default",
) -> list[str]:
    """Build compact highlight lines from analyzed papers."""

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
    template: AnalysisTemplate = "default",
) -> list[str]:
    """Build compact feed-level key points from analyzed or raw papers."""

    key_points: list[str] = []
    for paper in papers:
        summary_line = _highlight_text(paper)
        if not summary_line:
            continue
        key_points.append(_format_feed_key_point(paper.title, summary_line, template))
        if len(key_points) >= max_items:
            return key_points
    return key_points


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


def _analyze_paper(config: AnalysisConfig, paper: Paper) -> PaperAnalysis:
    if config.provider == "openai":
        return analyze_paper_with_openai(config, paper)
    raise AnalysisError(f"unsupported analysis provider: {config.provider}")


def _highlight_text(paper: Paper) -> str:
    if paper.analysis is not None:
        return _truncate_text(paper.analysis.conclusion, 160)
    return _truncate_text(paper.summary, 160)


def _format_digest_highlight(
    feed_name: str,
    paper_title: str,
    summary_line: str,
    template: AnalysisTemplate,
) -> str:
    if template == "zh_daily_brief":
        return f"{feed_name}：{paper_title}：{summary_line}"
    return f"{feed_name}: {paper_title} - {summary_line}"


def _format_feed_key_point(
    paper_title: str,
    summary_line: str,
    template: AnalysisTemplate,
) -> str:
    if template == "zh_daily_brief":
        return f"{paper_title}：{summary_line}"
    return f"{paper_title}: {summary_line}"


def _truncate_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
