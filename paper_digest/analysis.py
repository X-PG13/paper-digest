"""Analysis orchestration for optional paper enrichment."""

from __future__ import annotations

from .arxiv_client import Paper, PaperAnalysis
from .config import AnalysisConfig
from .digest import DigestRun
from .openai_analysis import OpenAIAnalysisError, analyze_paper_with_openai


class AnalysisError(RuntimeError):
    """Raised when configured analysis fails."""


def enrich_digest_with_analysis(config: AnalysisConfig, digest: DigestRun) -> None:
    """Mutate a digest in place with optional structured paper analysis."""

    papers_to_analyze = _select_papers_for_analysis(digest, config.max_papers)
    if not papers_to_analyze:
        return

    try:
        for paper in papers_to_analyze:
            paper.analysis = _analyze_paper(config, paper)
    except OpenAIAnalysisError as exc:
        raise AnalysisError(str(exc)) from exc

    digest.highlights = build_digest_highlights(digest, config.top_highlights)


def build_digest_highlights(digest: DigestRun, max_items: int) -> list[str]:
    """Build compact highlight lines from analyzed papers."""

    highlights: list[str] = []
    for feed in digest.feeds:
        for paper in feed.papers:
            summary_line = _highlight_text(paper)
            if not summary_line:
                continue
            highlights.append(f"{feed.name}: {paper.title} - {summary_line}")
            if len(highlights) >= max_items:
                return highlights
    return highlights


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


def _truncate_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
