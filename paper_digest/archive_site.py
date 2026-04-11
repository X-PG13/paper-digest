"""Static archive site generation for digest history."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from email.utils import format_datetime
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .config import FeedbackStatus
from .feedback import FeedbackState, feedback_command_snippet, feedback_label_zh

if TYPE_CHECKING:
    from collections.abc import Sequence


class ArchiveSiteError(RuntimeError):
    """Raised when the archive site cannot be generated."""


@dataclass(slots=True, frozen=True)
class PaperArchive:
    canonical_id: str
    slug: str
    title: str
    href: str
    detail_href: str
    summary: str
    relevance_score: int
    reason_summary: str
    source: str
    source_variants: list[str]
    source_urls: dict[str, str]
    paper_id: str
    pdf_url: str | None
    doi: str | None
    arxiv_id: str | None
    authors: list[str]
    categories: list[str]
    tags: list[str]
    topics: list[str]
    published_at: datetime
    updated_at: datetime
    feedback_status: FeedbackStatus | None
    feedback_note: str | None
    search_text: str


@dataclass(slots=True, frozen=True)
class FeedArchive:
    name: str
    slug: str
    count: int
    summary: str
    key_points: list[str]
    papers: list[PaperArchive]


@dataclass(slots=True, frozen=True)
class DayArchive:
    date: str
    generated_at: datetime
    timezone: str
    total_papers: int
    feeds: list[FeedArchive]
    markdown_href: str
    json_href: str
    days_ago: int
    search_text: str


@dataclass(slots=True, frozen=True)
class ArchiveStats:
    label: str
    primary_value: int
    primary_label: str
    secondary_value: int
    secondary_label: str


@dataclass(slots=True, frozen=True)
class CountPoint:
    label: str
    count: int


@dataclass(slots=True, frozen=True)
class FeedOverview:
    name: str
    slug: str
    total_papers: int
    active_days: int
    recent_7_papers: int
    recent_30_papers: int
    recent_7_active_days: int
    recent_30_active_days: int
    latest_summary: str
    daily_counts: list[CountPoint]


@dataclass(slots=True, frozen=True)
class KeywordMatch:
    date: str
    generated_at: datetime
    generated_label: str
    days_ago: int
    feed_name: str
    title: str
    href: str
    detail_href: str
    summary: str


@dataclass(slots=True, frozen=True)
class KeywordOverview:
    term: str
    slug: str
    total_matches: int
    active_days: int
    recent_7_matches: int
    recent_30_matches: int
    latest_summary: str
    daily_counts: list[CountPoint]
    matches: list[KeywordMatch]


@dataclass(slots=True, frozen=True)
class SubscriptionItem:
    title: str
    link: str
    description: str
    guid: str
    published_at: datetime


@dataclass(slots=True, frozen=True)
class PaperAppearance:
    date: str
    generated_at: datetime
    generated_label: str
    feed_name: str
    feed_slug: str
    summary: str
    relevance_score: int
    match_reasons: list[str]
    markdown_href: str
    json_href: str


@dataclass(slots=True, frozen=True)
class RelatedPaper:
    title: str
    detail_href: str
    relation_summary: str
    relevance_score: int
    source_label: str


@dataclass(slots=True, frozen=True)
class PaperDetail:
    paper: PaperArchive
    appearances: list[PaperAppearance]
    first_seen: datetime
    last_seen: datetime
    active_days: int
    active_feeds: int
    appearance_count: int
    feedback_status: FeedbackStatus | None
    feedback_updated_at: datetime | None
    feedback_note: str | None
    related_papers: list[RelatedPaper]


@dataclass(slots=True, frozen=True)
class WeeklyReviewSection:
    label: str
    description: str
    items: list[PaperDetail]


def build_archive_site(
    output_dir: Path,
    *,
    tracked_keywords: Sequence[str] = (),
    feedback_state: FeedbackState | None = None,
) -> Path:
    """Build a static multi-page archive under ``output_dir / 'site'``."""

    site_root = output_dir / "site"
    digests_root = site_root / "digests"
    feeds_root = site_root / "feeds"
    papers_root = site_root / "papers"
    topics_root = site_root / "topics"
    if site_root.exists():
        shutil.rmtree(site_root)
    digests_root.mkdir(parents=True, exist_ok=True)
    feeds_root.mkdir(parents=True, exist_ok=True)
    papers_root.mkdir(parents=True, exist_ok=True)
    topics_root.mkdir(parents=True, exist_ok=True)

    archives = _load_archives(output_dir, digests_root)
    feed_overviews = _build_feed_overviews(archives)
    keyword_overviews = _build_keyword_overviews(archives, tracked_keywords)
    paper_details = _build_paper_details(
        archives,
        tracked_keywords,
        feedback_state=feedback_state,
    )

    _copy_latest_files(output_dir, site_root)
    site_root.joinpath("index.html").write_text(
        _render_index(archives, feed_overviews, keyword_overviews),
        encoding="utf-8",
    )
    site_root.joinpath("trends.html").write_text(
        _render_trends_page(feed_overviews, keyword_overviews, paper_details),
        encoding="utf-8",
    )
    site_root.joinpath("momentum.html").write_text(
        _render_momentum_page(paper_details),
        encoding="utf-8",
    )
    site_root.joinpath("weekly-review.html").write_text(
        _render_weekly_review_page(paper_details),
        encoding="utf-8",
    )
    site_root.joinpath("reading-list.html").write_text(
        _render_reading_list_page(paper_details),
        encoding="utf-8",
    )
    site_root.joinpath("review-queue.html").write_text(
        _render_review_queue_page(paper_details),
        encoding="utf-8",
    )

    for overview in feed_overviews:
        feeds_root.joinpath(f"{overview.slug}.html").write_text(
            _render_feed_page(overview, archives, keyword_overviews),
            encoding="utf-8",
        )
        feeds_root.joinpath(f"{overview.slug}.xml").write_text(
            _render_feed_rss(overview, archives),
            encoding="utf-8",
        )

    for keyword_overview in keyword_overviews:
        topics_root.joinpath(f"{keyword_overview.slug}.html").write_text(
            _render_keyword_page(keyword_overview),
            encoding="utf-8",
        )
        topics_root.joinpath(f"{keyword_overview.slug}.xml").write_text(
            _render_keyword_rss(keyword_overview),
            encoding="utf-8",
        )
    for detail in paper_details:
        papers_root.joinpath(f"{detail.paper.slug}.html").write_text(
            _render_paper_page(detail),
            encoding="utf-8",
        )
    return site_root


def _load_archives(output_dir: Path, digests_root: Path) -> list[DayArchive]:
    digest_files = sorted(
        output_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/digest.json"),
        reverse=True,
    )
    raw_days = [
        _load_day_archive(digest_file, digests_root) for digest_file in digest_files
    ]
    if not raw_days:
        return []

    latest_day = max(day.generated_at.date() for day in raw_days)
    archives: list[DayArchive] = []
    for day in raw_days:
        archives.append(
            DayArchive(
                date=day.date,
                generated_at=day.generated_at,
                timezone=day.timezone,
                total_papers=day.total_papers,
                feeds=day.feeds,
                markdown_href=day.markdown_href,
                json_href=day.json_href,
                days_ago=(latest_day - day.generated_at.date()).days,
                search_text=day.search_text,
            )
        )
    return archives


def _load_day_archive(digest_json_path: Path, digests_root: Path) -> DayArchive:
    try:
        payload = json.loads(digest_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArchiveSiteError(f"invalid digest JSON: {digest_json_path}") from exc

    if not isinstance(payload, dict):
        raise ArchiveSiteError(f"invalid digest payload: {digest_json_path}")

    generated_at = _parse_datetime(payload.get("generated_at"), digest_json_path)
    timezone = payload.get("timezone")
    if not isinstance(timezone, str) or not timezone.strip():
        raise ArchiveSiteError(f"invalid timezone in {digest_json_path}")
    date_str = digest_json_path.parent.name
    target_root = digests_root / date_str
    target_root.mkdir(parents=True, exist_ok=True)

    markdown_source = digest_json_path.with_name("digest.md")
    if not markdown_source.exists():
        raise ArchiveSiteError(f"missing digest markdown: {markdown_source}")

    markdown_target = target_root / "digest.md"
    json_target = target_root / "digest.json"
    shutil.copyfile(markdown_source, markdown_target)
    shutil.copyfile(digest_json_path, json_target)

    raw_feeds = payload.get("feeds")
    if not isinstance(raw_feeds, list):
        raise ArchiveSiteError(f"invalid feed list in {digest_json_path}")

    feeds: list[FeedArchive] = []
    search_terms: list[str] = []
    total_papers = 0
    for raw_feed in raw_feeds:
        feed = _parse_feed(raw_feed, digest_json_path, generated_at)
        feeds.append(feed)
        total_papers += feed.count
        search_terms.append(feed.name.lower())
        for paper in feed.papers:
            search_terms.append(paper.search_text)

    return DayArchive(
        date=date_str,
        generated_at=generated_at,
        timezone=timezone.strip(),
        total_papers=total_papers,
        feeds=feeds,
        markdown_href=f"digests/{date_str}/digest.md",
        json_href=f"digests/{date_str}/digest.json",
        days_ago=0,
        search_text=" ".join(search_terms),
    )


def _parse_feed(
    raw_feed: object,
    digest_json_path: Path,
    generated_at: datetime,
) -> FeedArchive:
    if not isinstance(raw_feed, dict):
        raise ArchiveSiteError(f"invalid feed payload in {digest_json_path}")

    name = raw_feed.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ArchiveSiteError(f"invalid feed name in {digest_json_path}")

    raw_papers = raw_feed.get("papers")
    if not isinstance(raw_papers, list):
        raise ArchiveSiteError(
            f"invalid papers for feed {name!r} in {digest_json_path}"
        )

    papers = _parse_papers(raw_papers, digest_json_path, generated_at)
    raw_key_points = raw_feed.get("key_points")
    key_points = (
        [
            item.strip()
            for item in raw_key_points
            if isinstance(item, str) and item.strip()
        ]
        if isinstance(raw_key_points, list)
        else []
    )

    summary = _build_feed_summary(name, len(papers), key_points, papers)
    return FeedArchive(
        name=name.strip(),
        slug=_slugify(name),
        count=len(papers),
        summary=summary,
        key_points=key_points,
        papers=papers,
    )


def _parse_papers(
    raw_papers: list[object],
    digest_json_path: Path,
    generated_at: datetime,
) -> list[PaperArchive]:
    papers: list[PaperArchive] = []
    for raw_paper in raw_papers:
        if not isinstance(raw_paper, dict):
            continue
        title = raw_paper.get("title")
        abstract_url = raw_paper.get("abstract_url")
        summary = raw_paper.get("summary", "")
        relevance_score = raw_paper.get("relevance_score", 0)
        raw_match_reasons = raw_paper.get("match_reasons", [])
        canonical_id = raw_paper.get("canonical_id")
        paper_id = raw_paper.get("paper_id")
        raw_source = raw_paper.get("source", "unknown")
        raw_source_variants = raw_paper.get("source_variants", [])
        raw_source_urls = raw_paper.get("source_urls", {})
        if not isinstance(title, str) or not isinstance(abstract_url, str):
            continue
        normalized_summary = summary.strip() if isinstance(summary, str) else ""
        normalized_score = (
            relevance_score if isinstance(relevance_score, int) else 0
        )
        normalized_source = (
            raw_source.strip().lower()
            if isinstance(raw_source, str) and raw_source.strip()
            else "unknown"
        )
        normalized_canonical_id = _canonical_id_from_payload(
            canonical_id,
            paper_id,
            abstract_url,
            title,
        )
        slug = _paper_slug(normalized_canonical_id)
        reason_summary = ""
        if isinstance(raw_match_reasons, list):
            reasons = [
                item.strip()
                for item in raw_match_reasons
                if isinstance(item, str) and item.strip()
            ]
            reason_summary = "；".join(reasons[:3])
        published_at = _parse_optional_datetime(
            raw_paper.get("published_at"),
            fallback=generated_at,
            digest_json_path=digest_json_path,
        )
        updated_at = _parse_optional_datetime(
            raw_paper.get("updated_at"),
            fallback=published_at,
            digest_json_path=digest_json_path,
        )
        source_variants = _normalize_string_list(raw_source_variants)
        if normalized_source not in {item.lower() for item in source_variants}:
            source_variants.append(normalized_source)
        papers.append(
            PaperArchive(
                canonical_id=normalized_canonical_id,
                slug=slug,
                title=title.strip(),
                href=abstract_url,
                detail_href=f"papers/{slug}.html",
                summary=normalized_summary,
                relevance_score=normalized_score,
                reason_summary=reason_summary,
                source=normalized_source,
                source_variants=source_variants,
                source_urls=_normalize_source_url_map(
                    raw_source_urls,
                    source=normalized_source,
                    abstract_url=abstract_url,
                    paper_id=paper_id if isinstance(paper_id, str) else "",
                    doi=_optional_clean_string(raw_paper.get("doi")),
                    arxiv_id=_optional_clean_string(raw_paper.get("arxiv_id")),
                ),
                paper_id=_optional_clean_string(paper_id) or abstract_url,
                pdf_url=_optional_clean_string(raw_paper.get("pdf_url")),
                doi=_optional_clean_string(raw_paper.get("doi")),
                arxiv_id=_optional_clean_string(raw_paper.get("arxiv_id")),
                authors=_normalize_string_list(raw_paper.get("authors", [])),
                categories=_normalize_string_list(raw_paper.get("categories", [])),
                tags=_normalize_string_list(raw_paper.get("tags", [])),
                topics=_normalize_string_list(raw_paper.get("topics", [])),
                published_at=published_at,
                updated_at=updated_at,
                feedback_status=_optional_feedback_status(
                    raw_paper.get("feedback_status")
                ),
                feedback_note=_optional_clean_string(raw_paper.get("feedback_note")),
                search_text=_normalize_search(
                    " ".join(
                        [
                            title,
                            normalized_summary,
                            reason_summary,
                            " ".join(_normalize_string_list(raw_paper.get("tags", []))),
                            " ".join(
                                _normalize_string_list(raw_paper.get("topics", []))
                            ),
                            " ".join(
                                _normalize_string_list(raw_paper.get("categories", []))
                            ),
                        ]
                    )
                ),
            )
        )
    return papers


def _build_feed_summary(
    name: str,
    count: int,
    key_points: list[str],
    papers: list[PaperArchive],
) -> str:
    if count == 0:
        return f"{name} 今日没有新的命中文献。"
    if key_points:
        return _truncate("；".join(key_points[:2]), 220)
    if papers:
        label = "、".join(f"《{paper.title}》" for paper in papers[:2])
        return _truncate(f"收录 {count} 篇，重点包括{label}。", 220)
    return f"收录 {count} 篇新论文。"


def _build_feed_overviews(archives: list[DayArchive]) -> list[FeedOverview]:
    feed_names = sorted({feed.name for day in archives for feed in day.feeds})
    overviews: list[FeedOverview] = []
    for feed_name in feed_names:
        daily_counts: list[CountPoint] = []
        latest_summary = ""
        for day in archives:
            feed = _find_feed(day, feed_name)
            count = feed.count if feed is not None else 0
            daily_counts.append(CountPoint(label=day.date, count=count))
            if (
                feed is not None
                and not latest_summary
                and (feed.count > 0 or feed.summary)
            ):
                latest_summary = feed.summary
        total_papers = sum(point.count for point in daily_counts)
        active_days = sum(1 for point in daily_counts if point.count > 0)
        overviews.append(
            FeedOverview(
                name=feed_name,
                slug=_slugify(feed_name),
                total_papers=total_papers,
                active_days=active_days,
                recent_7_papers=_sum_counts(daily_counts, 7),
                recent_30_papers=_sum_counts(daily_counts, 30),
                recent_7_active_days=_sum_active_days(daily_counts, 7),
                recent_30_active_days=_sum_active_days(daily_counts, 30),
                latest_summary=latest_summary or f"{feed_name} 的长期归档与追踪视图。",
                daily_counts=daily_counts,
            )
        )
    return sorted(
        overviews,
        key=lambda item: (-item.total_papers, item.name.lower()),
    )


def _build_keyword_overviews(
    archives: list[DayArchive],
    tracked_keywords: Sequence[str],
) -> list[KeywordOverview]:
    normalized_terms = _normalize_keywords(tracked_keywords)
    overviews: list[KeywordOverview] = []
    for term in normalized_terms:
        normalized_term = _normalize_search(term)
        matches: list[KeywordMatch] = []
        daily_counts: list[CountPoint] = []
        for day in archives:
            count_for_day = 0
            generated_label = (
                f"{day.generated_at.strftime('%Y-%m-%d %H:%M:%S')} ({day.timezone})"
            )
            for feed in day.feeds:
                for paper in feed.papers:
                    if normalized_term and normalized_term in paper.search_text:
                        count_for_day += 1
                        matches.append(
                            KeywordMatch(
                                date=day.date,
                                generated_at=day.generated_at,
                                generated_label=generated_label,
                                days_ago=day.days_ago,
                                feed_name=feed.name,
                                title=paper.title,
                                href=paper.href,
                                detail_href=paper.detail_href,
                                summary=paper.summary,
                            )
                        )
            daily_counts.append(CountPoint(label=day.date, count=count_for_day))

        total_matches = sum(point.count for point in daily_counts)
        if matches:
            latest = matches[0]
            latest_summary = _truncate(
                f"最近一次命中来自 {latest.feed_name}：{latest.title}", 180
            )
        else:
            latest_summary = "暂未命中，页面会持续追踪后续归档。"
        overviews.append(
            KeywordOverview(
                term=term,
                slug=_slugify(term),
                total_matches=total_matches,
                active_days=sum(1 for point in daily_counts if point.count > 0),
                recent_7_matches=_sum_counts(daily_counts, 7),
                recent_30_matches=_sum_counts(daily_counts, 30),
                latest_summary=latest_summary,
                daily_counts=daily_counts,
                matches=matches,
            )
        )
    return sorted(
        overviews,
        key=lambda item: (-item.total_matches, item.term.lower()),
    )


def _build_paper_details(
    archives: list[DayArchive],
    tracked_keywords: Sequence[str],
    *,
    feedback_state: FeedbackState | None,
) -> list[PaperDetail]:
    occurrences_by_id: dict[
        str,
        list[tuple[DayArchive, FeedArchive, PaperArchive]],
    ] = {}
    for day in archives:
        for feed in day.feeds:
            for paper in feed.papers:
                occurrences_by_id.setdefault(paper.canonical_id, []).append(
                    (day, feed, paper)
                )

    details_by_id: dict[str, PaperDetail] = {}
    normalized_keywords = _normalize_keywords(tracked_keywords)
    for canonical_id, occurrences in occurrences_by_id.items():
        representative = max(
            (paper for _, _, paper in occurrences),
            key=_paper_detail_score,
        )
        sorted_occurrences = sorted(
            occurrences,
            key=lambda item: (
                -item[0].generated_at.timestamp(),
                item[1].name.lower(),
            ),
        )
        first_seen = min(day.generated_at for day, _, _ in occurrences)
        last_seen = max(day.generated_at for day, _, _ in occurrences)
        appearances = [
            PaperAppearance(
                date=day.date,
                generated_at=day.generated_at,
                generated_label=(
                    f"{day.generated_at.strftime('%Y-%m-%d %H:%M:%S')} ({day.timezone})"
                ),
                feed_name=feed.name,
                feed_slug=feed.slug,
                summary=paper.summary,
                relevance_score=paper.relevance_score,
                match_reasons=_expand_reason_summary(paper.reason_summary),
                markdown_href=day.markdown_href,
                json_href=day.json_href,
            )
            for day, feed, paper in sorted_occurrences
        ]
        details_by_id[canonical_id] = PaperDetail(
            paper=representative,
            appearances=appearances,
            first_seen=first_seen,
            last_seen=last_seen,
            active_days=len({day.date for day, _, _ in occurrences}),
            active_feeds=len({feed.name for _, feed, _ in occurrences}),
            appearance_count=len(occurrences),
            feedback_status=_resolve_feedback_status(
                canonical_id,
                representative.feedback_status,
                feedback_state,
            ),
            feedback_updated_at=_resolve_feedback_updated_at(
                canonical_id,
                feedback_state,
            ),
            feedback_note=_resolve_feedback_note(
                canonical_id,
                representative.feedback_note,
                feedback_state,
            ),
            related_papers=[],
        )

    for canonical_id, detail in list(details_by_id.items()):
        related = _build_related_papers(
            canonical_id,
            detail.paper,
            details_by_id,
            normalized_keywords,
        )
        details_by_id[canonical_id] = PaperDetail(
            paper=detail.paper,
            appearances=detail.appearances,
            first_seen=detail.first_seen,
            last_seen=detail.last_seen,
            active_days=detail.active_days,
            active_feeds=detail.active_feeds,
            appearance_count=detail.appearance_count,
            feedback_status=detail.feedback_status,
            feedback_updated_at=detail.feedback_updated_at,
            feedback_note=detail.feedback_note,
            related_papers=related,
        )

    return sorted(
        details_by_id.values(),
        key=lambda detail: (
            -detail.paper.relevance_score,
            -detail.paper.updated_at.timestamp(),
            detail.paper.title.lower(),
        ),
    )


def _copy_latest_files(output_dir: Path, site_root: Path) -> None:
    for filename in ("latest.md", "latest.json"):
        source = output_dir / filename
        if source.exists():
            shutil.copyfile(source, site_root / filename)


def _parse_datetime(value: object, digest_json_path: Path) -> datetime:
    if not isinstance(value, str):
        raise ArchiveSiteError(f"invalid generated_at in {digest_json_path}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ArchiveSiteError(f"invalid generated_at in {digest_json_path}") from exc
    if parsed.tzinfo is None:
        raise ArchiveSiteError(f"naive generated_at in {digest_json_path}")
    return parsed


def _render_index(
    archives: list[DayArchive],
    feed_overviews: list[FeedOverview],
    keyword_overviews: list[KeywordOverview],
) -> str:
    latest_archive = archives[0] if archives else None
    feed_names = [overview.name for overview in feed_overviews]
    stats = [
        _build_stats("最近 7 天", archives, 7),
        _build_stats("最近 30 天", archives, 30),
        _build_stats("全部归档", archives, None),
    ]
    cards_html = (
        "\n".join(_render_day_card(day) for day in archives) or _render_empty_state()
    )
    feed_options = "\n".join(
        f'<option value="{escape(name)}">{escape(name)}</option>' for name in feed_names
    )
    latest_label = _latest_label(latest_archive)
    content = (
        _render_subscription_panel(feed_overviews, keyword_overviews)
        + '<section class="section-grid">'
        + "".join(_render_stats_card(item) for item in stats)
        + "</section>"
        + _render_filter_panel(feed_options)
        + '<section class="archive-grid" id="archive-grid">'
        + cards_html
        + "</section>"
        + (
            '<section class="empty hidden" id="empty-state">'
            "当前筛选条件下没有匹配的归档。"
            "</section>"
        )
    )

    return _render_page(
        page_title="Paper Digest Archive",
        eyebrow="Paper Digest Archive",
        heading="研究日报归档页",
        description=(
            "汇总每天生成的 digest.json 和 digest.md，支持按 feed 过滤、"
            "按标题关键词搜索，"
            "并提供固定 feed 页面、关键词长期追踪页、持续升温视图，"
            "阅读清单、周度回顾，以及最近 7 天 / 30 天趋势页。"
        ),
        hero_links=_render_hero_links(
            [
                ("latest.md", "查看最新 Markdown"),
                ("latest.json", "查看最新 JSON"),
                ("trends.html", "查看趋势总览"),
                ("momentum.html", "持续升温论文"),
                ("weekly-review.html", "周度回顾"),
                (None, f"最近构建：{latest_label}"),
            ]
        ),
        content=content,
        nav_current="home",
        extra_script=_render_index_script(),
    )


def _render_trends_page(
    feed_overviews: list[FeedOverview],
    keyword_overviews: list[KeywordOverview],
    paper_details: list[PaperDetail],
) -> str:
    total_digests = max((len(item.daily_counts) for item in feed_overviews), default=0)
    feed_cards = "\n".join(
        _render_feed_overview_card(item, link_prefix="") for item in feed_overviews
    ) or _render_empty_note("还没有可展示的 feed 趋势。")
    keyword_cards = "\n".join(
        _render_keyword_overview_card(item, link_prefix="")
        for item in keyword_overviews
    ) or _render_empty_note("当前没有配置可追踪的关键词。")
    rising_papers = _build_rising_papers(paper_details)
    reading_list = _build_reading_list(paper_details)
    rising_cards = "\n".join(
        _render_rising_paper_card(item, link_prefix="")
        for item in rising_papers[:6]
    ) or _render_empty_note("当前还没有跨多天或多 feed 的持续升温论文。")
    stats = [
        ArchiveStats(
            "Feed 订阅",
            len(feed_overviews),
            "个固定入口",
            total_digests,
            "个 digest 日",
        ),
        ArchiveStats(
            "关键词追踪",
            len(keyword_overviews),
            "个关键词页",
            sum(item.total_matches for item in keyword_overviews),
            "次历史命中",
        ),
        ArchiveStats(
            "最近 30 天",
            sum(item.recent_30_papers for item in feed_overviews),
            "篇 feed 命中",
            sum(item.recent_30_matches for item in keyword_overviews),
            "次关键词命中",
        ),
        ArchiveStats(
            "持续升温论文",
            len(rising_papers),
            "篇候选",
            sum(item.active_days for item in rising_papers),
            "个累计活跃日期",
        ),
        ArchiveStats(
            "阅读清单",
            len(reading_list),
            "篇已标记论文",
            sum(1 for item in reading_list if item.feedback_status == "star"),
            "篇标星",
        ),
    ]
    content = (
        '<section class="section-grid">'
        + "".join(_render_stats_card(item) for item in stats)
        + "</section>"
        + _render_section(
            "Feed 趋势订阅",
            "固定链接适合长期追踪某个研究方向的命中量和最近变化。",
            f'<div class="subscription-grid">{feed_cards}</div>',
        )
        + _render_section(
            "关键词长期追踪",
            "这些页面来自你配置里的 feed 关键词，适合观察某个主题是否持续冒头。",
            f'<div class="subscription-grid">{keyword_cards}</div>',
        )
        + _render_section(
            "持续升温论文",
            "这些论文在多个日期或多个 feed 中反复出现，更适合放进长期观察列表。",
            f'<div class="subscription-grid">{rising_cards}</div>'
            '<div class="chip-cloud">'
            '<a class="topic-chip" href="momentum.html">查看完整持续升温视图</a>'
            '<a class="topic-chip" href="weekly-review.html">查看周度回顾</a>'
            "</div>",
        )
    )
    return _render_page(
        page_title="Paper Digest Trends",
        eyebrow="Subscription View",
        heading="趋势与订阅总览",
        description=(
            "从归档里提炼长期信号：每个 feed 的近 7 天 / 30 天命中情况，"
            "配置关键词的长期命中轨迹，以及跨多天反复出现的持续升温论文。"
        ),
        hero_links=_render_hero_links(
            [
                ("index.html", "返回归档首页"),
                ("latest.md", "最新 Markdown"),
                ("latest.json", "最新 JSON"),
                ("momentum.html", "持续升温论文"),
                ("weekly-review.html", "周度回顾"),
            ]
        ),
        content=content,
        nav_current="trends",
    )


def _render_feed_page(
    overview: FeedOverview,
    archives: list[DayArchive],
    keyword_overviews: list[KeywordOverview],
) -> str:
    related_keywords = [
        item
        for item in keyword_overviews
        if any(
            match.feed_name == overview.name
            for match in item.matches[: min(len(item.matches), 20)]
        )
    ]
    feed_days: list[DayArchive] = []
    for day in archives:
        feed = _find_feed(day, overview.name)
        if feed is not None and feed.count > 0:
            feed_days.append(day)
    cards_html = "\n".join(
        _render_day_card(day, visible_feed=overview.name, link_prefix="../")
        for day in feed_days
    ) or _render_empty_state("这个 feed 还没有命中过论文。")
    keyword_links = (
        '<div class="chip-cloud">'
        + "".join(
            _render_chip_link(
                f"../topics/{item.slug}.html",
                f"{item.term} · {item.total_matches}",
            )
            for item in related_keywords[:8]
        )
        + "</div>"
        if related_keywords
        else _render_empty_note("当前没有与这个 feed 重合的关键词追踪页。")
    )
    content = (
        '<section class="section-grid">'
        + "".join(
            _render_stats_card(item)
            for item in (
                ArchiveStats(
                    "最近 7 天",
                    overview.recent_7_papers,
                    "篇论文",
                    overview.recent_7_active_days,
                    "个活跃 digest",
                ),
                ArchiveStats(
                    "最近 30 天",
                    overview.recent_30_papers,
                    "篇论文",
                    overview.recent_30_active_days,
                    "个活跃 digest",
                ),
                ArchiveStats(
                    "全部历史",
                    overview.total_papers,
                    "篇论文",
                    overview.active_days,
                    "个活跃 digest",
                ),
            )
        )
        + "</section>"
        + _render_section(
            "近期走势",
            overview.latest_summary,
            _render_trend_list(overview.daily_counts, empty_label="暂无历史数据。"),
        )
        + _render_section(
            "相关关键词页",
            "如果这个 feed 同时命中了你配置里的关键词，这里会给出长期追踪入口。",
            keyword_links,
        )
        + _render_section(
            "历史命中",
            "按天回看这个 feed 的命中文献，并保留当日 digest 的 "
            "Markdown / JSON 原始产物。",
            f'<section class="archive-grid">{cards_html}</section>',
        )
    )
    return _render_page(
        page_title=f"{overview.name} Feed Archive",
        eyebrow="Feed Subscription",
        heading=f"{overview.name} 固定订阅页",
        description=(
            "适合长期跟踪单个研究方向。页面会汇总这个 feed 的最近 7 天 / 30 天表现，"
            "并保留每天命中的原始条目和 digest 链接。"
        ),
        hero_links=_render_hero_links(
            [
                ("../index.html", "返回归档首页"),
                ("../trends.html", "查看趋势总览"),
                ("../latest.md", "最新 Markdown"),
                (f"{overview.slug}.xml", "订阅 RSS"),
            ]
        ),
        content=content,
        nav_current="feeds",
        link_prefix="../",
        rss_href=f"{overview.slug}.xml",
    )


def _render_keyword_page(overview: KeywordOverview) -> str:
    grouped = _group_keyword_matches(overview.matches)
    groups_html = "\n".join(
        _render_keyword_match_group(date, matches) for date, matches in grouped
    ) or _render_empty_state("这个关键词目前还没有历史命中。")
    content = (
        '<section class="section-grid">'
        + "".join(
            _render_stats_card(item)
            for item in (
                ArchiveStats(
                    "最近 7 天",
                    overview.recent_7_matches,
                    "次命中",
                    min(overview.active_days, 7),
                    "个活跃日期",
                ),
                ArchiveStats(
                    "最近 30 天",
                    overview.recent_30_matches,
                    "次命中",
                    min(overview.active_days, 30),
                    "个活跃日期",
                ),
                ArchiveStats(
                    "全部历史",
                    overview.total_matches,
                    "次命中",
                    overview.active_days,
                    "个活跃日期",
                ),
            )
        )
        + "</section>"
        + _render_section(
            "近期走势",
            overview.latest_summary,
            _render_trend_list(overview.daily_counts, empty_label="暂无历史数据。"),
        )
        + _render_section(
            "命中明细",
            "按日期回看匹配到这个关键词的论文标题，并保留来源 feed 信息。",
            f'<section class="match-grid">{groups_html}</section>',
        )
    )
    return _render_page(
        page_title=f"{overview.term} Topic Archive",
        eyebrow="Keyword Tracking",
        heading=f"关键词追踪：{overview.term}",
        description=(
            "这个页面会长期追踪你配置里关心的关键词，并把命中的论文按日期沉淀下来。"
        ),
        hero_links=_render_hero_links(
            [
                ("../index.html", "返回归档首页"),
                ("../trends.html", "查看趋势总览"),
                ("../latest.json", "最新 JSON"),
                (f"{overview.slug}.xml", "订阅 RSS"),
            ]
        ),
        content=content,
        nav_current="topics",
        link_prefix="../",
        rss_href=f"{overview.slug}.xml",
    )


def _build_rising_papers(paper_details: list[PaperDetail]) -> list[PaperDetail]:
    rising = [
        detail
        for detail in paper_details
        if detail.active_days > 1 or detail.active_feeds > 1
    ]
    return sorted(
        rising,
        key=lambda detail: (
            -detail.active_days,
            -detail.active_feeds,
            -detail.appearance_count,
            -detail.last_seen.timestamp(),
            -detail.paper.relevance_score,
            detail.paper.title.lower(),
        ),
    )


def _feedback_stage_priority(status: FeedbackStatus | None) -> int:
    priority = {
        "star": 0,
        "follow_up": 1,
        "reading": 2,
        "done": 3,
        "ignore": 4,
        None: 5,
    }
    return priority[status]


def _review_anchor(paper_details: list[PaperDetail]) -> datetime | None:
    if not paper_details:
        return None
    return max(
        (detail.feedback_updated_at or detail.last_seen) for detail in paper_details
    )


def _is_same_iso_week(value: datetime, anchor: datetime) -> bool:
    value_year, value_week, _ = value.isocalendar()
    anchor_year, anchor_week, _ = anchor.isocalendar()
    return (value_year, value_week) == (anchor_year, anchor_week)


def _days_from_anchor(anchor: datetime, value: datetime) -> int:
    return (anchor.date() - value.date()).days


def _render_rising_paper_card(
    detail: PaperDetail,
    *,
    link_prefix: str,
    kicker: str = "Momentum",
) -> str:
    detail_link = escape(link_prefix + detail.paper.detail_href)
    status_badge = _render_feedback_badge(detail.feedback_status)
    note_html = ""
    if detail.feedback_note:
        note_html = (
            '<p class="resource-copy note-copy">'
            f"备注：{escape(_truncate(detail.feedback_note, 160))}"
            "</p>"
        )
    return (
        f'<a class="resource-card" href="{detail_link}">'
        f'<p class="resource-kicker">{escape(kicker)}</p>'
        f"{status_badge}"
        f'<h3 class="resource-title">{escape(detail.paper.title)}</h3>'
        f'<p class="resource-copy">{escape(_truncate(detail.paper.summary, 220))}</p>'
        f"{note_html}"
        '<div class="resource-meta">'
        f"<span>{detail.active_days} 天</span>"
        f"<span>{detail.active_feeds} 个 feed</span>"
        f"<span>{detail.appearance_count} 次命中</span>"
        "</div>"
        '<div class="resource-meta">'
        f"<span>首次出现：{escape(_format_seen_label(detail.first_seen))}</span>"
        f"<span>最近出现：{escape(_format_seen_label(detail.last_seen))}</span>"
        "</div>"
        "</a>"
    )


def _render_momentum_page(paper_details: list[PaperDetail]) -> str:
    rising_papers = _build_rising_papers(paper_details)
    spotlight_cards = "\n".join(
        _render_rising_paper_card(item, link_prefix="")
        for item in rising_papers
    ) or _render_empty_state("当前还没有跨多天或多 feed 的持续升温论文。")
    stats = [
        ArchiveStats(
            "持续升温论文",
            len(rising_papers),
            "篇候选",
            sum(item.active_days for item in rising_papers),
            "个累计活跃日期",
        ),
        ArchiveStats(
            "跨 Feed 复现",
            sum(1 for item in rising_papers if item.active_feeds > 1),
            "篇论文",
            max((item.active_feeds for item in rising_papers), default=0),
            "个最大 feed 覆盖",
        ),
        ArchiveStats(
            "跨天复现",
            sum(1 for item in rising_papers if item.active_days > 1),
            "篇论文",
            max((item.active_days for item in rising_papers), default=0),
            "个最大活跃日期",
        ),
    ]
    content = (
        '<section class="section-grid">'
        + "".join(_render_stats_card(item) for item in stats)
        + "</section>"
        + _render_section(
            "持续升温论文",
            "优先展示在多个日期或多个 feed 中反复出现的论文，方便建立长期观察清单。",
            f'<div class="subscription-grid">{spotlight_cards}</div>',
        )
    )
    return _render_page(
        page_title="Paper Digest Momentum",
        eyebrow="Relationship View",
        heading="持续升温论文",
        description=(
            "这里聚合跨多天或多 feed 重复出现的论文，"
            "帮助你快速识别值得长期追踪的研究信号。"
        ),
        hero_links=_render_hero_links(
            [
                ("index.html", "返回归档首页"),
                ("trends.html", "查看趋势总览"),
                ("review-queue.html", "Review Queue"),
                ("weekly-review.html", "周度回顾"),
                ("reading-list.html", "阅读清单"),
                ("latest.md", "最新 Markdown"),
            ]
        ),
        content=content,
        nav_current="momentum",
    )


def _build_reading_list(paper_details: list[PaperDetail]) -> list[PaperDetail]:
    reading_list = [
        detail
        for detail in paper_details
        if detail.feedback_status in {"star", "follow_up", "reading"}
    ]
    return sorted(
        reading_list,
        key=lambda detail: (
            _feedback_stage_priority(detail.feedback_status),
            -(detail.feedback_updated_at or detail.last_seen).timestamp(),
            -detail.paper.relevance_score,
            detail.paper.title.lower(),
        ),
    )


def _build_weekly_review_sections(
    paper_details: list[PaperDetail],
) -> list[WeeklyReviewSection]:
    anchor = _review_anchor(paper_details)
    if anchor is None:
        return []

    pending = [
        detail
        for detail in paper_details
        if detail.feedback_status in {"star", "follow_up"}
        and _is_same_iso_week(detail.feedback_updated_at or detail.last_seen, anchor)
    ]
    pending.sort(
        key=lambda detail: (
            _feedback_stage_priority(detail.feedback_status),
            -(detail.feedback_updated_at or detail.last_seen).timestamp(),
            -detail.paper.relevance_score,
            detail.paper.title.lower(),
        )
    )

    reading = [
        detail for detail in paper_details if detail.feedback_status == "reading"
    ]
    reading.sort(
        key=lambda detail: (
            -(detail.feedback_updated_at or detail.last_seen).timestamp(),
            -detail.paper.relevance_score,
            detail.paper.title.lower(),
        )
    )

    done = [detail for detail in paper_details if detail.feedback_status == "done"]
    done.sort(
        key=lambda detail: (
            -(detail.feedback_updated_at or detail.last_seen).timestamp(),
            -detail.paper.relevance_score,
            detail.paper.title.lower(),
        )
    )

    resurfaced = [
        detail
        for detail in paper_details
        if detail.feedback_status in {"star", "follow_up", "reading"}
        and _is_same_iso_week(detail.last_seen, anchor)
        and (detail.active_days > 1 or detail.active_feeds > 1)
    ]
    resurfaced.sort(
        key=lambda detail: (
            -detail.active_days,
            -detail.active_feeds,
            -detail.appearance_count,
            -detail.last_seen.timestamp(),
            -detail.paper.relevance_score,
            detail.paper.title.lower(),
        )
    )

    sections: list[WeeklyReviewSection] = []
    if pending:
        sections.append(
            WeeklyReviewSection(
                label="本周新增待处理",
                description="最近一周新增的标星和待跟进论文，适合作为本周优先处理列表。",
                items=pending,
            )
        )
    if reading:
        sections.append(
            WeeklyReviewSection(
                label="正在看",
                description="已经进入阅读中的论文，适合在周中持续补充笔记或结论。",
                items=reading,
            )
        )
    if done:
        sections.append(
            WeeklyReviewSection(
                label="已完成",
                description="本周已经明确完成处理的论文，方便在周报里和待处理项分开回看。",
                items=done,
            )
        )
    if resurfaced:
        sections.append(
            WeeklyReviewSection(
                label="再次提醒",
                description="本周再次升温的已标记论文，适合作为周会前的二次提醒列表。",
                items=resurfaced,
            )
        )
    return sections


def _build_review_queue_sections(
    paper_details: list[PaperDetail],
) -> list[WeeklyReviewSection]:
    anchor = _review_anchor(paper_details)
    if anchor is None:
        return []

    unreviewed = [
        detail
        for detail in paper_details
        if detail.feedback_status is None
        and _days_from_anchor(anchor, detail.last_seen) <= 7
    ]
    unreviewed.sort(
        key=lambda detail: (
            -detail.paper.relevance_score,
            -detail.last_seen.timestamp(),
            detail.paper.title.lower(),
        )
    )

    resurfaced_follow_up = [
        detail
        for detail in paper_details
        if detail.feedback_status == "follow_up"
        and _is_same_iso_week(detail.last_seen, anchor)
        and (detail.active_days > 1 or detail.active_feeds > 1)
    ]
    resurfaced_follow_up.sort(
        key=lambda detail: (
            -detail.last_seen.timestamp(),
            -detail.active_days,
            -detail.active_feeds,
            -detail.paper.relevance_score,
            detail.paper.title.lower(),
        )
    )

    starred_backlog = [
        detail for detail in paper_details if detail.feedback_status == "star"
    ]
    starred_backlog.sort(
        key=lambda detail: (
            -(detail.feedback_updated_at or detail.last_seen).timestamp(),
            -detail.paper.relevance_score,
            detail.paper.title.lower(),
        )
    )

    sections: list[WeeklyReviewSection] = []
    if unreviewed:
        sections.append(
            WeeklyReviewSection(
                label="新出现且未标记",
                description="最近 7 天出现、相关性高但还没进入个人反馈状态的论文。",
                items=unreviewed[:12],
            )
        )
    if resurfaced_follow_up:
        sections.append(
            WeeklyReviewSection(
                label="待跟进再次出现",
                description="已经标记为待跟进、且本周又再次出现的论文。",
                items=resurfaced_follow_up[:12],
            )
        )
    if starred_backlog:
        sections.append(
            WeeklyReviewSection(
                label="标星待处理",
                description="已经标星、但还没有推进到阅读中或已完成阶段的论文。",
                items=starred_backlog[:12],
            )
        )
    return sections


def _render_review_queue_page(paper_details: list[PaperDetail]) -> str:
    sections = _build_review_queue_sections(paper_details)
    section_blocks = (
        "".join(
            _render_section_block(
                section.label,
                section.description,
                '<div class="subscription-grid">'
                + "\n".join(
                    _render_rising_paper_card(
                        item,
                        link_prefix="",
                        kicker="Review Queue",
                    )
                    for item in section.items
                )
                + "</div>",
            )
            for section in sections
        )
        if sections
        else _render_empty_state("当前还没有需要进入 review queue 的论文。")
    )
    pending_count = next(
        (len(section.items) for section in sections if section.label == "标星待处理"),
        0,
    )
    unreviewed_count = next(
        (
            len(section.items)
            for section in sections
            if section.label == "新出现且未标记"
        ),
        0,
    )
    resurfaced_count = next(
        (
            len(section.items)
            for section in sections
            if section.label == "待跟进再次出现"
        ),
        0,
    )
    stats = [
        ArchiveStats(
            "待判断",
            unreviewed_count,
            "篇高相关论文",
            pending_count,
            "篇标星待处理",
        ),
        ArchiveStats(
            "再次出现",
            resurfaced_count,
            "篇待跟进论文",
            len(sections),
            "个队列区块",
        ),
        ArchiveStats(
            "阅读推进",
            sum(1 for detail in paper_details if detail.feedback_status == "reading"),
            "篇阅读中",
            sum(1 for detail in paper_details if detail.feedback_status == "done"),
            "篇已完成",
        ),
    ]
    content = (
        '<section class="section-grid">'
        + "".join(_render_stats_card(item) for item in stats)
        + "</section>"
        + _render_section(
            "行动队列",
            "把未标记高相关论文、再次出现的待跟进论文，以及仍待处理的标星论文集中起来。",
            section_blocks,
        )
    )
    return _render_page(
        page_title="Paper Digest Review Queue",
        eyebrow="Action Queue",
        heading="Review Queue",
        description=(
            "这里汇总下一步最值得处理的论文，帮助你把每日研究情报转成明确的跟进动作。"
        ),
        hero_links=_render_hero_links(
            [
                ("index.html", "返回归档首页"),
                ("trends.html", "查看趋势总览"),
                ("reading-list.html", "阅读清单"),
                ("weekly-review.html", "周度回顾"),
            ]
        ),
        content=content,
        nav_current="review_queue",
    )


def _render_reading_list_page(paper_details: list[PaperDetail]) -> str:
    reading_list = _build_reading_list(paper_details)
    cards = "\n".join(
        _render_rising_paper_card(
            item,
            link_prefix="",
            kicker="Reading List",
        )
        for item in reading_list
    ) or _render_empty_state("当前还没有标星、待跟进或阅读中的论文。")
    stats = [
        ArchiveStats(
            "标星论文",
            sum(1 for item in reading_list if item.feedback_status == "star"),
            "篇",
            sum(1 for item in reading_list if item.feedback_status == "follow_up"),
            "篇待跟进",
        ),
        ArchiveStats(
            "阅读中",
            sum(1 for item in reading_list if item.feedback_status == "reading"),
            "篇论文",
            sum(1 for item in reading_list if item.active_days > 1),
            "篇跨天复现",
        ),
        ArchiveStats(
            "跨 Feed 复现",
            sum(1 for item in reading_list if item.active_feeds > 1),
            "篇论文",
            max((item.active_feeds for item in reading_list), default=0),
            "个最大 feed 覆盖",
        ),
    ]
    content = (
        '<section class="section-grid">'
        + "".join(_render_stats_card(item) for item in stats)
        + "</section>"
        + _render_section(
            "阅读清单",
            "把你标星、待跟进或已经进入阅读中的论文抽出来，作为长期阅读和复盘入口。",
            f'<div class="subscription-grid">{cards}</div>',
        )
    )
    return _render_page(
        page_title="Paper Digest Reading List",
        eyebrow="Feedback View",
        heading="阅读清单",
        description=(
            "这里汇总你按 canonical_id 标记为 star、follow_up 或 reading 的论文，"
            "方便建立自己的长期研究观察列表。"
        ),
        hero_links=_render_hero_links(
            [
                ("index.html", "返回归档首页"),
                ("trends.html", "查看趋势总览"),
                ("review-queue.html", "Review Queue"),
                ("momentum.html", "持续升温论文"),
                ("weekly-review.html", "周度回顾"),
            ]
        ),
        content=content,
        nav_current="reading_list",
    )


def _render_weekly_review_page(paper_details: list[PaperDetail]) -> str:
    reading_list = _build_reading_list(paper_details)
    sections = _build_weekly_review_sections(paper_details)
    weekly_blocks = (
        "".join(
            _render_section_block(
                section.label,
                section.description,
                '<div class="subscription-grid">'
                + "\n".join(
                    _render_rising_paper_card(
                        item,
                        link_prefix="",
                        kicker="Weekly Review",
                    )
                    for item in section.items
                )
                + "</div>",
            )
            for section in sections
        )
        if sections
        else _render_empty_state("当前还没有可汇总进周度回顾的论文。")
    )
    stats = [
        ArchiveStats(
            "待处理",
            sum(
                1
                for item in reading_list
                if item.feedback_status in {"star", "follow_up"}
            ),
            "篇论文",
            sum(1 for item in reading_list if item.feedback_status == "reading"),
            "篇阅读中",
        ),
        ArchiveStats(
            "已完成",
            sum(1 for item in paper_details if item.feedback_status == "done"),
            "篇论文",
            len(sections),
            "个回顾区块",
        ),
        ArchiveStats(
            "再次提醒",
            sum(
                1
                for item in paper_details
                if item.feedback_status in {"star", "follow_up", "reading"}
                and (item.active_days > 1 or item.active_feeds > 1)
            ),
            "篇持续升温论文",
            len(reading_list),
            "篇在读清单",
        ),
    ]
    content = (
        '<section class="section-grid">'
        + "".join(_render_stats_card(item) for item in stats)
        + "</section>"
        + _render_section(
            "周度回顾",
            "按周收口你已经标星或待跟进的论文，适合做周会前的快速回看。",
            weekly_blocks,
        )
    )
    return _render_page(
        page_title="Paper Digest Weekly Review",
        eyebrow="Feedback Review",
        heading="周度回顾",
        description=(
            "把待处理、正在看、已完成和再次提醒的论文拆开，"
            "帮助你把阅读清单变成真正可执行的周度研究回顾。"
        ),
        hero_links=_render_hero_links(
            [
                ("index.html", "返回归档首页"),
                ("trends.html", "查看趋势总览"),
                ("review-queue.html", "Review Queue"),
                ("reading-list.html", "阅读清单"),
                ("momentum.html", "持续升温论文"),
            ]
        ),
        content=content,
        nav_current="weekly_review",
    )


def _render_paper_page(detail: PaperDetail) -> str:
    paper = detail.paper
    source_links = _render_source_link_grid(paper)
    appearances = _render_paper_appearances(detail.appearances)
    related = _render_related_papers(detail.related_papers)
    content = (
        '<section class="section-grid">'
        + "".join(
            _render_stats_card(item)
            for item in (
                ArchiveStats(
                    "相关性",
                    paper.relevance_score,
                    "当前分数",
                    len(paper.source_variants),
                    "个合并来源",
                ),
                ArchiveStats(
                    "历史跨度",
                    detail.active_days,
                    "个活跃日期",
                    detail.active_feeds,
                    "个 feed",
                ),
                ArchiveStats(
                    "归档记录",
                    detail.appearance_count,
                    "次归档出现",
                    len(paper.source_variants),
                    "个合并来源",
                ),
                ArchiveStats(
                    "主题与标签",
                    len(paper.topics),
                    "个主题词",
                    len(paper.tags),
                    "个标签",
                ),
            )
        )
        + "</section>"
        + _render_section(
            "论文概览",
            _truncate(paper.summary or "这篇论文当前没有可显示的摘要。", 220),
            (
                '<div class="detail-grid">'
                + _render_meta_block("规范主键", paper.canonical_id)
                + _render_meta_block(
                    "合并来源",
                    _paper_source_label(paper),
                )
                + _render_meta_block(
                    "作者",
                    "，".join(paper.authors) if paper.authors else "作者信息缺失",
                )
                + _render_meta_block(
                    "分类",
                    ", ".join(paper.categories) if paper.categories else "未提供",
                )
                + _render_meta_block(
                    "标签",
                    " / ".join(paper.tags) if paper.tags else "未提供",
                )
                + _render_meta_block(
                    "主题词",
                    " / ".join(paper.topics) if paper.topics else "未提供",
                )
                + _render_meta_block(
                    "首次出现",
                    _format_seen_label(detail.first_seen),
                )
                + _render_meta_block(
                    "最近出现",
                    _format_seen_label(detail.last_seen),
                )
                + _render_meta_block(
                    "覆盖跨度",
                    (
                        f"{detail.active_days} 个活跃日期 / "
                        f"{detail.active_feeds} 个 feed / "
                        f"{detail.appearance_count} 次归档出现"
                    ),
                )
                + _render_meta_block(
                    "反馈状态",
                    feedback_label_zh(detail.feedback_status) or "未设置",
                )
                + _render_meta_block(
                    "个人备注",
                    detail.feedback_note or "未设置",
                )
                + _render_meta_block(
                    "命中原因",
                    paper.reason_summary or "未记录",
                )
                + "</div>"
            ),
        )
        + _render_section(
            "个人备注",
            "把你为什么标记这篇论文、接下来准备怎么处理，直接挂在规范化详情页上。",
            (
                '<div class="detail-grid">'
                + _render_meta_block("备注内容", detail.feedback_note or "")
                + "</div>"
                if detail.feedback_note
                else (
                    '<div class="empty">'
                    "当前还没有个人备注，可以先用本地 feedback CLI 补上。"
                    "</div>"
                )
            ),
        )
        + _render_section(
            "反馈操作",
            "复制规范主键或本地 CLI 命令，把这篇论文快速加入个人反馈状态文件。",
            _render_feedback_actions(detail),
        )
        + _render_section(
            "来源与外链",
            "优先展示这篇论文在各来源上的规范化入口，再补当前摘要页和 PDF。",
            source_links,
        )
        + _render_section(
            "历史命中",
            "按归档时间回看它在哪些 feed 中出现过，并保留当日 digest 产物入口。",
            appearances,
        )
        + _render_section(
            "相关推荐",
            "基于共享主题、标签和配置关键词做的轻量规则推荐。",
            related,
        )
    )
    return _render_page(
        page_title=f"{paper.title} | Paper Detail",
        eyebrow="Canonical Paper",
        heading=paper.title,
        description="这是一篇规范化归档后的论文详情页，聚合了多来源命中、历史出现记录和相关推荐。",
        hero_links=_render_hero_links(
            [
                ("../index.html", "返回归档首页"),
                ("../trends.html", "查看趋势总览"),
                ("../review-queue.html", "Review Queue"),
                ("../momentum.html", "持续升温论文"),
                ("../reading-list.html", "阅读清单"),
                ("../weekly-review.html", "周度回顾"),
                (paper.href, "打开当前主来源"),
                (
                    paper.pdf_url,
                    "打开 PDF",
                )
                if paper.pdf_url
                else (None, f"来源：{_paper_source_label(paper)}"),
            ]
        ),
        content=content,
        nav_current="papers",
        link_prefix="../",
        extra_script=_render_copy_script(),
    )


def _render_page(
    *,
    page_title: str,
    eyebrow: str,
    heading: str,
    description: str,
    hero_links: str,
    content: str,
    nav_current: str,
    link_prefix: str = "",
    rss_href: str | None = None,
    extra_script: str = "",
) -> str:
    rss_link = ""
    if rss_href is not None:
        rss_link = (
            '<link rel="alternate" type="application/rss+xml" '
            f'title="{escape(page_title)} RSS" href="{escape(rss_href)}">'
        )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(page_title)}</title>
  {rss_link}
  <style>{_site_styles()}</style>
</head>
<body>
  <main class="shell">
    {_render_nav(nav_current, link_prefix)}
    <section class="hero">
      <p class="eyebrow">{escape(eyebrow)}</p>
      <h1>{escape(heading)}</h1>
      <p>{escape(description)}</p>
      {hero_links}
    </section>
    {content}
  </main>
  {extra_script}
</body>
</html>
"""


def _render_feedback_actions(detail: PaperDetail) -> str:
    canonical_id = detail.paper.canonical_id
    note_command = (
        "python -m paper_digest feedback note "
        f"'{canonical_id}' 'TODO: add note' --config config.toml"
    )
    buttons = [
        ("复制 canonical_id", canonical_id),
        ("复制标星命令", feedback_command_snippet(canonical_id, "star")),
        (
            "复制待跟进命令",
            feedback_command_snippet(canonical_id, "follow_up"),
        ),
        ("复制阅读中命令", feedback_command_snippet(canonical_id, "reading")),
        ("复制已完成命令", feedback_command_snippet(canonical_id, "done")),
        ("复制忽略命令", feedback_command_snippet(canonical_id, "ignore")),
        ("复制备注命令", note_command),
    ]
    return (
        '<div class="chip-cloud">'
        + "".join(
            (
                '<button class="topic-chip copy-chip" type="button" '
                f'data-copy-text="{escape(payload)}" '
                f'data-copy-label="{escape(label)}">{escape(label)}</button>'
            )
            for label, payload in buttons
        )
        + "</div>"
    )


def _render_copy_script() -> str:
    return """
<script>
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy-text]");
    if (!button) {
      return;
    }
    const label = button.dataset.copyLabel || button.textContent;
    try {
      await navigator.clipboard.writeText(button.dataset.copyText || "");
      button.textContent = "已复制";
    } catch (error) {
      button.textContent = "复制失败";
    }
    window.setTimeout(() => {
      button.textContent = label;
    }, 1200);
  });
</script>
"""


def _render_feed_rss(overview: FeedOverview, archives: list[DayArchive]) -> str:
    items = _build_feed_subscription_items(overview, archives, link_prefix="../")
    return _render_rss(
        title=f"{overview.name} Feed Archive",
        link=f"{overview.slug}.html",
        description=f"{overview.name} 的长期订阅 RSS，汇总最近命中的论文和归档。",
        items=items,
    )


def _render_keyword_rss(overview: KeywordOverview) -> str:
    items = _build_keyword_subscription_items(overview, link_prefix="../")
    return _render_rss(
        title=f"{overview.term} Topic Archive",
        link=f"{overview.slug}.html",
        description=f"关键词 {overview.term} 的长期追踪 RSS，汇总历史命中文献。",
        items=items,
    )


def _build_feed_subscription_items(
    overview: FeedOverview,
    archives: list[DayArchive],
    *,
    link_prefix: str,
) -> list[SubscriptionItem]:
    items: list[SubscriptionItem] = []
    for day in archives:
        feed = _find_feed(day, overview.name)
        if feed is None or not feed.papers:
            continue
        for paper in feed.papers:
            items.append(
                SubscriptionItem(
                    title=paper.title,
                    link=link_prefix + paper.detail_href,
                    description=_truncate(
                        f"{paper.summary or feed.summary} 归档日期：{day.date}。", 500
                    ),
                    guid=f"{paper.href}#{day.date}#{overview.slug}",
                    published_at=day.generated_at,
                )
            )
    return items[:50]


def _build_keyword_subscription_items(
    overview: KeywordOverview,
    *,
    link_prefix: str,
) -> list[SubscriptionItem]:
    items: list[SubscriptionItem] = []
    for match in overview.matches[:50]:
        items.append(
            SubscriptionItem(
                title=match.title,
                link=link_prefix + match.detail_href,
                description=_truncate(
                    f"{match.summary} 来源分组：{match.feed_name}。"
                    f"归档日期：{match.date}。",
                    500,
                ),
                guid=f"{match.href}#{match.date}#{overview.slug}",
                published_at=match.generated_at,
            )
        )
    return items


def _render_rss(
    *,
    title: str,
    link: str,
    description: str,
    items: list[SubscriptionItem],
) -> str:
    rendered_items = "\n".join(_render_rss_item(item) for item in items)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "<channel>\n"
        f"<title>{escape(title)}</title>\n"
        f"<link>{escape(link)}</link>\n"
        f"<description>{escape(description)}</description>\n"
        "<language>zh-CN</language>\n"
        f"<lastBuildDate>{format_datetime(datetime.now().astimezone())}</lastBuildDate>\n"
        f"{rendered_items}\n"
        "</channel>\n"
        "</rss>\n"
    )


def _render_rss_item(item: SubscriptionItem) -> str:
    return (
        "<item>\n"
        f"<title>{escape(item.title)}</title>\n"
        f"<link>{escape(item.link)}</link>\n"
        f"<guid>{escape(item.guid)}</guid>\n"
        f"<pubDate>{format_datetime(item.published_at)}</pubDate>\n"
        f"<description>{escape(item.description)}</description>\n"
        "</item>"
    )


def _render_nav(current: str, link_prefix: str) -> str:
    items = [
        ("home", f"{link_prefix}index.html", "归档首页"),
        ("trends", f"{link_prefix}trends.html", "趋势总览"),
        ("review_queue", f"{link_prefix}review-queue.html", "行动队列"),
        ("momentum", f"{link_prefix}momentum.html", "持续升温"),
        ("weekly_review", f"{link_prefix}weekly-review.html", "周度回顾"),
        ("reading_list", f"{link_prefix}reading-list.html", "阅读清单"),
        ("papers", f"{link_prefix}index.html", "论文详情"),
    ]
    return (
        '<nav class="top-nav">'
        + "".join(
            (
                f'<a class="nav-link{" is-active" if current == key else ""}" '
                f'href="{escape(href)}">{escape(label)}</a>'
            )
            for key, href, label in items
        )
        + "</nav>"
    )


def _render_hero_links(items: Sequence[tuple[str | None, str]]) -> str:
    return (
        '<div class="hero-links">'
        + "".join(
            (
                f'<a class="hero-link" href="{escape(href)}">{escape(label)}</a>'
                if href is not None
                else f'<span class="hero-link">{escape(label)}</span>'
            )
            for href, label in items
        )
        + "</div>"
    )


def _render_subscription_panel(
    feed_overviews: list[FeedOverview],
    keyword_overviews: list[KeywordOverview],
) -> str:
    feed_cards = "\n".join(
        _render_feed_overview_card(item, link_prefix="") for item in feed_overviews
    ) or _render_empty_note("还没有可用的 feed 固定页。")
    keyword_cards = (
        '<div class="chip-cloud">'
        + "".join(
            _render_chip_link(
                f"topics/{item.slug}.html",
                f"{item.term} · {item.total_matches}",
            )
            for item in keyword_overviews
        )
        + "</div>"
        if keyword_overviews
        else _render_empty_note("当前没有配置关键词追踪页。")
    )
    trends_card = (
        '<a class="resource-card spotlight" href="trends.html">'
        '<p class="resource-kicker">Trends</p>'
        '<h3 class="resource-title">最近 7 天 / 30 天趋势总览</h3>'
        "<p>把 feed 命中和关键词命中压缩成可持续浏览的长期视角。</p>"
        "</a>"
    )
    momentum_card = (
        '<a class="resource-card" href="momentum.html">'
        '<p class="resource-kicker">Momentum</p>'
        '<h3 class="resource-title">持续升温论文</h3>'
        "<p class=\"resource-copy\">"
        "把跨多天或多 feed 反复出现的论文抽出来，作为长期观察入口。"
        "</p>"
        "</a>"
    )
    weekly_review_card = (
        '<a class="resource-card" href="weekly-review.html">'
        '<p class="resource-kicker">Weekly Review</p>'
        '<h3 class="resource-title">周度回顾</h3>'
        "<p class=\"resource-copy\">"
        "把标星和待跟进论文按周收口，适合做周会前的集中回看。"
        "</p>"
        "</a>"
    )
    review_queue_card = (
        '<a class="resource-card" href="review-queue.html">'
        '<p class="resource-kicker">Action Queue</p>'
        '<h3 class="resource-title">Review Queue</h3>'
        "<p class=\"resource-copy\">"
        "把高相关未标记论文、待跟进再次出现和标星待处理论文集中成行动列表。"
        "</p>"
        "</a>"
    )
    reading_card = (
        '<a class="resource-card" href="reading-list.html">'
        '<p class="resource-kicker">Reading List</p>'
        '<h3 class="resource-title">阅读清单</h3>'
        "<p class=\"resource-copy\">"
        "把你标星或待跟进的论文单独收口，形成长期个人研究清单。"
        "</p>"
        "</a>"
    )
    return _render_section(
        "订阅入口",
        "把站点从“按天翻”升级成“按主题长期追”。固定页更适合每天回看同一类研究信号。",
        '<div class="subscription-grid">'
        + trends_card
        + review_queue_card
        + momentum_card
        + weekly_review_card
        + reading_card
        + feed_cards
        + "</div>"
        + _render_section_block(
            "关键词长期追踪",
            "这些页来自你的 feed 关键词配置。",
            keyword_cards,
        ),
    )


def _render_filter_panel(feed_options: str) -> str:
    return f"""
    <section class="filter-panel">
      <div class="filter-grid">
        <div class="field">
          <label for="title-search">按标题关键词搜索</label>
          <input
            id="title-search"
            type="search"
            placeholder="例如 agent, benchmark, diffusion"
          >
        </div>
        <div class="field">
          <label for="feed-filter">按 feed 过滤</label>
          <select id="feed-filter">
            <option value="">全部 feed</option>
            {feed_options}
          </select>
        </div>
        <div class="field">
          <label>按最近时间查看</label>
          <div class="chip-row" id="window-filters">
            <button
              class="filter-chip"
              type="button"
              data-days="7"
              aria-pressed="false"
            >最近 7 天</button>
            <button
              class="filter-chip"
              type="button"
              data-days="30"
              aria-pressed="true"
            >最近 30 天</button>
            <button
              class="filter-chip"
              type="button"
              data-days="all"
              aria-pressed="false"
            >全部历史</button>
          </div>
        </div>
      </div>
    </section>
    """


def _render_section(title: str, description: str, body: str) -> str:
    return (
        '<section class="section-card">'
        '<div class="section-head">'
        f'<h2 class="section-title">{escape(title)}</h2>'
        f'<p class="section-copy">{escape(description)}</p>'
        "</div>"
        f"{body}"
        "</section>"
    )


def _render_section_block(title: str, description: str, body: str) -> str:
    return (
        '<div class="section-block">'
        f'<h3 class="block-title">{escape(title)}</h3>'
        f'<p class="block-copy">{escape(description)}</p>'
        f"{body}"
        "</div>"
    )


def _build_stats(
    label: str,
    archives: list[DayArchive],
    limit_days: int | None,
) -> ArchiveStats:
    if limit_days is None:
        relevant = archives
    else:
        relevant = [day for day in archives if day.days_ago < limit_days]
    return ArchiveStats(
        label=label,
        primary_value=sum(day.total_papers for day in relevant),
        primary_label="篇论文",
        secondary_value=len(relevant),
        secondary_label="个 digest",
    )


def _render_stats_card(stats: ArchiveStats) -> str:
    return (
        '<article class="metric">'
        f'<p class="metric-label">{escape(stats.label)}</p>'
        f'<p class="metric-value">{stats.primary_value}</p>'
        f'<p class="metric-subtle">{escape(stats.primary_label)}</p>'
        f'<p class="metric-meta">{stats.secondary_value} '
        f"{escape(stats.secondary_label)}</p>"
        "</article>"
    )


def _render_day_card(
    day: DayArchive,
    *,
    visible_feed: str | None = None,
    link_prefix: str = "",
) -> str:
    generated_label = (
        f"{day.generated_at.strftime('%Y-%m-%d %H:%M:%S')} ({day.timezone})"
    )
    feeds = (
        [feed for feed in day.feeds if feed.name == visible_feed]
        if visible_feed is not None
        else list(day.feeds)
    )
    feed_names = "|" + "|".join(feed.name.lower() for feed in feeds) + "|"
    feed_cards = "\n".join(
        _render_feed_card(
            feed,
            link_prefix=link_prefix,
            feed_page_link=visible_feed is None,
        )
        for feed in feeds
    )
    total_papers = sum(feed.count for feed in feeds)
    return (
        f'<article class="day-card" data-days-ago="{day.days_ago}" '
        f'data-search-text="{escape(day.search_text)}" '
        f'data-feed-names="{escape(feed_names)}">'
        '<header class="day-header">'
        "<div>"
        f'<h2 class="day-title">{escape(day.date)}</h2>'
        '<div class="day-meta">'
        f"<span>命中 {total_papers} 篇</span>"
        f"<span>生成于 {escape(generated_label)}</span>"
        "</div>"
        "</div>"
        '<div class="hero-links">'
        f'<a class="hero-link" href="{escape(link_prefix + day.markdown_href)}">'
        "Markdown</a>"
        f'<a class="hero-link" href="{escape(link_prefix + day.json_href)}">JSON</a>'
        "</div>"
        "</header>"
        f'<div class="feed-stack">{feed_cards}</div>'
        "</article>"
    )


def _render_feed_card(
    feed: FeedArchive,
    *,
    link_prefix: str,
    feed_page_link: bool,
) -> str:
    titles = "".join(
        (
            "<li>"
            f'<a href="{escape(link_prefix + item.detail_href)}">'
            f"{escape(item.title)}</a>"
            + (
                (
                    '<span class="paper-inline-meta">'
                    f" · Score {item.relevance_score}</span>"
                )
                if item.relevance_score > 0
                else ""
            )
            + (
                f'<div class="paper-inline-reason">'
                f'{escape(_truncate(item.reason_summary, 120))}</div>'
                if item.reason_summary
                else ""
            )
            + (
                '<div class="paper-inline-links">'
                f'<a href="{escape(item.href)}" target="_blank" rel="noreferrer">'
                "原始来源</a>"
                "</div>"
            )
            + "</li>"
        )
        for item in feed.papers[:5]
    )
    title_list = f'<ol class="paper-list">{titles}</ol>' if titles else ""
    feed_href = escape(link_prefix + "feeds/" + feed.slug + ".html")
    name_label = (
        f'<a class="feed-name-link" href="{feed_href}">{escape(feed.name)}</a>'
        if feed_page_link
        else escape(feed.name)
    )
    return (
        f'<section class="feed-card" data-feed-name="{escape(feed.name.lower())}">'
        '<div class="feed-head">'
        f'<span class="feed-name">{name_label}</span>'
        f'<span class="feed-count">{feed.count} 篇</span>'
        "</div>"
        f'<p class="feed-summary">{escape(feed.summary)}</p>'
        f"{title_list}"
        "</section>"
    )


def _render_feed_overview_card(overview: FeedOverview, *, link_prefix: str) -> str:
    feed_href = escape(link_prefix + "feeds/" + overview.slug + ".html")
    return (
        f'<a class="resource-card" href="{feed_href}">'
        '<p class="resource-kicker">Feed</p>'
        f'<h3 class="resource-title">{escape(overview.name)}</h3>'
        f'<p class="resource-copy">{escape(overview.latest_summary)}</p>'
        '<div class="resource-meta">'
        f"<span>{overview.recent_7_papers} / 7d</span>"
        f"<span>{overview.recent_30_papers} / 30d</span>"
        f"<span>{overview.total_papers} / all</span>"
        "</div>"
        "</a>"
    )


def _render_keyword_overview_card(
    overview: KeywordOverview,
    *,
    link_prefix: str,
) -> str:
    topic_href = escape(link_prefix + "topics/" + overview.slug + ".html")
    return (
        f'<a class="resource-card" href="{topic_href}">'
        '<p class="resource-kicker">Topic</p>'
        f'<h3 class="resource-title">{escape(overview.term)}</h3>'
        f'<p class="resource-copy">{escape(overview.latest_summary)}</p>'
        '<div class="resource-meta">'
        f"<span>{overview.recent_7_matches} / 7d</span>"
        f"<span>{overview.recent_30_matches} / 30d</span>"
        f"<span>{overview.total_matches} / all</span>"
        "</div>"
        "</a>"
    )


def _render_chip_link(href: str, label: str) -> str:
    return f'<a class="topic-chip" href="{escape(href)}">{escape(label)}</a>'


def _render_trend_list(
    daily_counts: list[CountPoint],
    *,
    limit: int = 14,
    empty_label: str,
) -> str:
    selected = list(reversed(daily_counts[:limit]))
    if not selected:
        return _render_empty_note(empty_label)
    max_count = max((item.count for item in selected), default=0)
    rows = "".join(_render_trend_row(item, max_count=max_count) for item in selected)
    return f'<div class="trend-list">{rows}</div>'


def _render_trend_row(point: CountPoint, *, max_count: int) -> str:
    width = 12 if max_count <= 0 else max(12, int(point.count / max_count * 100))
    return (
        '<div class="trend-row">'
        f'<span class="trend-label">{escape(point.label)}</span>'
        '<div class="trend-track">'
        f'<span class="trend-bar" style="width: {width}%"></span>'
        "</div>"
        f'<span class="trend-count">{point.count}</span>'
        "</div>"
    )


def _group_keyword_matches(
    matches: list[KeywordMatch],
) -> list[tuple[str, list[KeywordMatch]]]:
    groups: list[tuple[str, list[KeywordMatch]]] = []
    seen_dates: dict[str, list[KeywordMatch]] = {}
    order: list[str] = []
    for match in matches:
        bucket = seen_dates.setdefault(match.date, [])
        if match.date not in order:
            order.append(match.date)
        bucket.append(match)
    for date in order:
        groups.append((date, seen_dates[date]))
    return groups


def _render_keyword_match_group(date: str, matches: list[KeywordMatch]) -> str:
    generated_label = matches[0].generated_label if matches else ""
    items = "".join(_render_keyword_match_card(match) for match in matches)
    return (
        '<section class="match-day">'
        '<div class="match-head">'
        f'<h3 class="match-title">{escape(date)}</h3>'
        f'<p class="match-meta">{escape(generated_label)}</p>'
        "</div>"
        f'<div class="match-list">{items}</div>'
        "</section>"
    )


def _render_keyword_match_card(match: KeywordMatch) -> str:
    summary = (
        f'<p class="match-copy">{escape(_truncate(match.summary, 180))}</p>'
        if match.summary
        else ""
    )
    return (
        '<article class="match-card">'
        f'<span class="feed-pill">{escape(match.feed_name)}</span>'
        f'<h4 class="match-card-title"><a href="{escape("../" + match.detail_href)}">'
        f"{escape(match.title)}</a></h4>"
        f'<p class="match-meta-link"><a href="{escape(match.href)}" '
        f'target="_blank" rel="noreferrer">查看原始来源</a></p>'
        f"{summary}"
        "</article>"
    )


def _render_source_link_grid(paper: PaperArchive) -> str:
    links = _paper_source_links(paper)
    if not links:
        return _render_empty_note("当前没有可展示的来源链接。")
    return (
        '<div class="chip-cloud">'
        + "".join(
            f'<a class="topic-chip" href="{escape(href)}" target="_blank" '
            f'rel="noreferrer">{escape(label)}</a>'
            for label, href in links
        )
        + "</div>"
    )


def _render_paper_appearances(appearances: list[PaperAppearance]) -> str:
    if not appearances:
        return _render_empty_note("这篇论文还没有历史命中记录。")
    cards: list[str] = []
    for item in appearances:
        summary = (
            f'<p class="match-copy">{escape(_truncate(item.summary, 180))}</p>'
            if item.summary
            else ""
        )
        reasons = escape("；".join(item.match_reasons[:3]) or "无额外命中原因")
        cards.append(
            '<article class="match-card">'
            f'<span class="feed-pill">{escape(item.feed_name)}</span>'
            f'<h4 class="match-card-title">{escape(item.date)}</h4>'
            f'<p class="match-meta">{escape(item.generated_label)}</p>'
            f"{summary}"
            '<p class="match-copy">'
            f"Score {item.relevance_score} · {reasons}"
            "</p>"
            '<div class="chip-cloud">'
            f'<a class="topic-chip" href="../{escape(item.markdown_href)}">Markdown</a>'
            f'<a class="topic-chip" href="../{escape(item.json_href)}">JSON</a>'
            f'<a class="topic-chip" href="../feeds/{escape(item.feed_slug)}.html">'
            "对应 Feed 页</a>"
            "</div>"
            "</article>"
        )
    return (
        '<div class="match-list">'
        + "".join(cards)
        + "</div>"
    )


def _render_related_papers(related_papers: list[RelatedPaper]) -> str:
    if not related_papers:
        return _render_empty_note("暂时没有足够强的同主题相关推荐。")
    cards: list[str] = []
    for item in related_papers:
        cards.append(
            f'<a class="resource-card" href="../{escape(item.detail_href)}">'
            '<p class="resource-kicker">Related</p>'
            f'<h3 class="resource-title">{escape(item.title)}</h3>'
            f'<p class="resource-copy">{escape(item.relation_summary)}</p>'
            '<div class="resource-meta">'
            f"<span>Score {item.relevance_score}</span>"
            f"<span>{escape(item.source_label)}</span>"
            "</div>"
            "</a>"
        )
    return (
        '<div class="subscription-grid">'
        + "".join(cards)
        + "</div>"
    )


def _render_meta_block(label: str, value: str) -> str:
    return (
        '<article class="meta-card">'
        f'<p class="metric-label">{escape(label)}</p>'
        f'<p class="resource-copy">{escape(value)}</p>'
        "</article>"
    )


def _render_feedback_badge(status: FeedbackStatus | None) -> str:
    label = feedback_label_zh(status)
    if label is None:
        return ""
    return f'<span class="feed-pill">{escape(label)}</span>'


def _render_empty_state(label: str = "还没有可归档的 digest 输出。") -> str:
    return f'<div class="empty">{escape(label)}</div>'


def _render_empty_note(label: str) -> str:
    return f'<p class="empty-note">{escape(label)}</p>'


def _render_index_script() -> str:
    return """
<script>
  const searchInput = document.getElementById("title-search");
  const feedFilter = document.getElementById("feed-filter");
  const emptyState = document.getElementById("empty-state");
  const cards = Array.from(document.querySelectorAll(".day-card"));
  const chips = Array.from(document.querySelectorAll(".filter-chip"));
  let activeDays = "30";

  function setActiveChip(value) {
    activeDays = value;
    for (const chip of chips) {
      chip.setAttribute("aria-pressed", String(chip.dataset.days === value));
    }
    applyFilters();
  }

  function normalize(value) {
    return value.trim().toLowerCase();
  }

  function applyFilters() {
    const query = normalize(searchInput.value);
    const activeFeed = normalize(feedFilter.value);
    let visibleCount = 0;

    for (const card of cards) {
      const daysAgo = Number(card.dataset.daysAgo || "0");
      const searchText = normalize(card.dataset.searchText || "");
      const feedNames = normalize(card.dataset.feedNames || "");
      const matchesDays = activeDays === "all" || daysAgo < Number(activeDays);
      const matchesQuery = query === "" || searchText.includes(query);
      const matchesFeed =
        activeFeed === "" || feedNames.includes("|" + activeFeed + "|");
      const visible = matchesDays && matchesQuery && matchesFeed;
      card.classList.toggle("hidden", !visible);

      for (const feedCard of card.querySelectorAll(".feed-card")) {
        const feedName = normalize(feedCard.dataset.feedName || "");
        const feedVisible = activeFeed === "" || feedName === activeFeed;
        feedCard.classList.toggle("hidden", !feedVisible);
      }

      if (visible) {
        visibleCount += 1;
      }
    }

    emptyState.classList.toggle("hidden", visibleCount > 0);
  }

  searchInput.addEventListener("input", applyFilters);
  feedFilter.addEventListener("change", applyFilters);
  for (const chip of chips) {
    chip.addEventListener("click", () => setActiveChip(chip.dataset.days || "all"));
  }
    applyFilters();
</script>
"""


def _paper_detail_score(paper: PaperArchive) -> tuple[int, int, int, int, float]:
    return (
        paper.relevance_score,
        len(paper.source_variants),
        len(paper.summary),
        len(paper.authors),
        paper.updated_at.timestamp(),
    )


def _expand_reason_summary(value: str) -> list[str]:
    return [item.strip() for item in value.split("；") if item.strip()]


def _paper_source_label(paper: PaperArchive) -> str:
    return " / ".join(_source_display_label(item) for item in paper.source_variants)


def _paper_source_links(paper: PaperArchive) -> list[tuple[str, str]]:
    ordered_keys = [
        "arxiv",
        "doi",
        "openalex",
        "semantic_scholar",
        "pubmed",
        "crossref",
    ]
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for key in [*ordered_keys, *paper.source_urls.keys()]:
        href = paper.source_urls.get(key)
        if href is None or key in seen:
            continue
        seen.add(key)
        links.append((_source_display_label(key), href))
    if paper.pdf_url is not None:
        links.append(("PDF", paper.pdf_url))
    return links


def _build_related_papers(
    canonical_id: str,
    paper: PaperArchive,
    details_by_id: dict[str, PaperDetail],
    tracked_keywords: list[str],
) -> list[RelatedPaper]:
    related: list[tuple[int, PaperArchive, str]] = []
    self_topics = {item.casefold() for item in paper.topics}
    self_tags = {item.casefold() for item in paper.tags}
    self_keyword_hits = {
        keyword.casefold()
        for keyword in tracked_keywords
        if keyword.casefold() in paper.search_text
    }

    for other_id, detail in details_by_id.items():
        if other_id == canonical_id:
            continue
        other = detail.paper
        shared_topics = [
            item for item in other.topics if item.casefold() in self_topics
        ]
        shared_tags = [item for item in other.tags if item.casefold() in self_tags]
        shared_keywords = [
            keyword
            for keyword in tracked_keywords
            if keyword.casefold() in self_keyword_hits
            and keyword.casefold() in other.search_text
        ]
        score = len(shared_topics) * 4 + len(shared_tags) * 2 + len(shared_keywords)
        if score <= 0:
            continue
        related.append(
            (
                score,
                other,
                _related_reason_summary(
                    shared_topics,
                    shared_tags,
                    shared_keywords,
                ),
            )
        )

    related.sort(
        key=lambda item: (
            -item[0],
            -item[1].relevance_score,
            -item[1].updated_at.timestamp(),
            item[1].title.lower(),
        )
    )
    return [
        RelatedPaper(
            title=other.title,
            detail_href=other.detail_href,
            relation_summary=summary,
            relevance_score=other.relevance_score,
            source_label=_paper_source_label(other),
        )
        for _, other, summary in related[:6]
    ]


def _related_reason_summary(
    shared_topics: list[str],
    shared_tags: list[str],
    shared_keywords: list[str],
) -> str:
    segments: list[str] = []
    if shared_topics:
        segments.append(f"共享主题：{' / '.join(shared_topics[:3])}")
    if shared_tags:
        segments.append(f"共享标签：{' / '.join(shared_tags[:3])}")
    if shared_keywords:
        segments.append(f"共享关键词：{' / '.join(shared_keywords[:3])}")
    return "；".join(segments)


def _site_styles() -> str:
    return """
    :root {
      --bg: #f4efe6;
      --bg-accent: #e4dcc8;
      --panel: rgba(255, 252, 246, 0.9);
      --panel-strong: #fffaf1;
      --text: #1f1a16;
      --muted: #675e56;
      --line: rgba(74, 56, 42, 0.18);
      --brand: #9a3412;
      --brand-soft: #f97316;
      --shadow: 0 18px 40px rgba(86, 55, 25, 0.12);
      --radius: 22px;
      --max: 1180px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: "IBM Plex Sans", "Segoe UI Variable", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(249, 115, 22, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(180, 83, 9, 0.12), transparent 24%),
        linear-gradient(180deg, var(--bg) 0%, #f8f5ef 100%);
    }

    a {
      color: inherit;
    }

    .shell {
      width: min(calc(100vw - 32px), var(--max));
      margin: 0 auto;
      padding: 24px 0 64px;
    }

    .top-nav {
      display: flex;
      gap: 10px;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }

    .nav-link,
    .hero-link,
    .filter-chip,
    .topic-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.72);
      font-size: 0.96rem;
      text-decoration: none;
    }

    button.topic-chip,
    button.copy-chip {
      cursor: pointer;
      font: inherit;
      color: inherit;
    }

    .nav-link.is-active {
      background: linear-gradient(135deg, var(--brand), var(--brand-soft));
      color: white;
      border-color: transparent;
    }

    .hero {
      position: relative;
      overflow: hidden;
      padding: 32px;
      border: 1px solid var(--line);
      border-radius: calc(var(--radius) + 6px);
      background:
        linear-gradient(135deg, rgba(255, 250, 241, 0.98), rgba(243, 234, 215, 0.92));
      box-shadow: var(--shadow);
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: auto -80px -120px auto;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(249, 115, 22, 0.12), transparent 65%);
      pointer-events: none;
    }

    .eyebrow {
      margin: 0 0 12px;
      font-size: 13px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--brand);
    }

    h1 {
      margin: 0;
      font-family: "Source Serif 4", Georgia, serif;
      font-size: clamp(2.2rem, 5vw, 4.2rem);
      line-height: 0.98;
    }

    .hero p {
      max-width: 780px;
      margin: 18px 0 0;
      font-size: 1.03rem;
      line-height: 1.7;
      color: var(--muted);
    }

    .hero-links {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 24px;
    }

    .section-grid,
    .archive-grid,
    .subscription-grid,
    .match-grid,
    .detail-grid {
      display: grid;
      gap: 18px;
    }

    .section-grid {
      margin-top: 22px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }

    .section-card,
    .filter-panel,
    .day-card {
      margin-top: 24px;
      padding: 22px;
      border-radius: calc(var(--radius) + 2px);
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
    }

    .section-head {
      display: grid;
      gap: 10px;
      margin-bottom: 18px;
    }

    .section-title {
      margin: 0;
      font-family: "Source Serif 4", Georgia, serif;
      font-size: 1.6rem;
    }

    .section-copy,
    .block-copy,
    .resource-copy,
    .empty-note {
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
    }

    .section-block + .section-block {
      margin-top: 22px;
    }

    .block-title {
      margin: 0 0 8px;
      font-size: 1rem;
    }

    .chip-cloud {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }

    .subscription-grid {
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }

    .resource-card {
      display: grid;
      gap: 10px;
      padding: 18px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.78);
      text-decoration: none;
      min-height: 180px;
    }

    .resource-card.spotlight {
      background:
        linear-gradient(
          135deg,
          rgba(154, 52, 18, 0.94),
          rgba(249, 115, 22, 0.88)
        );
      color: white;
      border-color: transparent;
    }

    .resource-kicker {
      margin: 0;
      font-size: 0.8rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--brand);
    }

    .resource-card.spotlight .resource-kicker,
    .resource-card.spotlight .resource-copy {
      color: rgba(255, 255, 255, 0.88);
    }

    .resource-title {
      margin: 0;
      font-size: 1.15rem;
      line-height: 1.35;
    }

    .resource-meta {
      margin-top: auto;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .resource-card.spotlight .resource-meta {
      color: rgba(255, 255, 255, 0.88);
    }

    .metric {
      padding: 18px;
      border-radius: var(--radius);
      border: 1px solid var(--line);
      background: rgba(255, 252, 246, 0.95);
      box-shadow: var(--shadow);
    }

    .metric-label,
    .metric-subtle,
    .metric-meta {
      margin: 0;
      color: var(--muted);
    }

    .metric-value {
      margin: 10px 0 6px;
      font-size: 1.9rem;
      font-weight: 700;
    }

    .filter-grid {
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      align-items: end;
    }

    .field {
      display: grid;
      gap: 8px;
    }

    .field label {
      font-size: 0.92rem;
      color: var(--muted);
    }

    .field input,
    .field select {
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.86);
      color: var(--text);
      font: inherit;
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .filter-chip {
      cursor: pointer;
    }

    .filter-chip[aria-pressed="true"] {
      border-color: transparent;
      background: linear-gradient(135deg, var(--brand), var(--brand-soft));
      color: white;
    }

    .archive-grid {
      margin-top: 28px;
    }

    .day-card {
      background: var(--panel-strong);
    }

    .day-header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
    }

    .day-title {
      margin: 0;
      font-family: "Source Serif 4", Georgia, serif;
      font-size: 1.8rem;
    }

    .day-meta {
      margin-top: 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .feed-stack {
      display: grid;
      gap: 14px;
      margin-top: 22px;
    }

    .feed-card {
      padding: 16px 18px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(244, 239, 230, 0.68);
    }

    .feed-head {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
    }

    .feed-name {
      font-size: 1.02rem;
      font-weight: 700;
    }

    .feed-name-link {
      text-decoration: none;
      border-bottom: 1px dashed rgba(154, 52, 18, 0.4);
    }

    .feed-count {
      color: var(--brand);
      font-size: 0.92rem;
    }

    .feed-summary {
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.65;
    }

    .paper-list {
      margin: 12px 0 0;
      padding-left: 18px;
      display: grid;
      gap: 6px;
      color: var(--muted);
    }

    .paper-list a,
    .match-card-title a {
      text-decoration: none;
      border-bottom: 1px dashed rgba(154, 52, 18, 0.45);
    }

    .paper-inline-links,
    .match-meta-link {
      margin-top: 6px;
      font-size: 0.88rem;
    }

    .paper-inline-links a,
    .match-meta-link a {
      color: var(--brand);
      text-decoration: none;
      border-bottom: 1px dashed rgba(154, 52, 18, 0.45);
    }

    .trend-list {
      display: grid;
      gap: 10px;
    }

    .trend-row {
      display: grid;
      grid-template-columns: 96px 1fr 36px;
      gap: 12px;
      align-items: center;
    }

    .trend-label,
    .trend-count {
      font-size: 0.92rem;
      color: var(--muted);
    }

    .trend-track {
      height: 10px;
      border-radius: 999px;
      background: rgba(154, 52, 18, 0.08);
      overflow: hidden;
    }

    .trend-bar {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(135deg, var(--brand), var(--brand-soft));
    }

    .match-grid {
      margin-top: 12px;
    }

    .detail-grid {
      margin-top: 14px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }

    .meta-card {
      padding: 16px 18px;
      border-radius: 18px;
      border: 1px solid rgba(74, 56, 42, 0.12);
      background: rgba(255, 255, 255, 0.82);
      display: grid;
      gap: 8px;
    }

    .match-day {
      padding: 18px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.78);
    }

    .match-head {
      display: grid;
      gap: 6px;
      margin-bottom: 14px;
    }

    .match-title,
    .match-card-title {
      margin: 0;
    }

    .match-meta {
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .match-list {
      display: grid;
      gap: 12px;
    }

    .match-card {
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(74, 56, 42, 0.12);
      background: rgba(244, 239, 230, 0.58);
    }

    .match-copy {
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.6;
    }

    .feed-pill {
      display: inline-flex;
      margin-bottom: 10px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(154, 52, 18, 0.1);
      color: var(--brand);
      font-size: 0.88rem;
      font-weight: 600;
    }

    .empty {
      padding: 28px;
      text-align: center;
      border-radius: calc(var(--radius) + 2px);
      border: 1px dashed var(--line);
      color: var(--muted);
      background: rgba(255, 252, 246, 0.75);
    }

    .empty-note {
      margin-top: 14px;
    }

    .hidden {
      display: none !important;
    }

    @media (max-width: 720px) {
      .shell {
        width: min(calc(100vw - 20px), var(--max));
        padding-top: 18px;
      }

      .hero,
      .section-card,
      .filter-panel,
      .day-card {
        padding: 20px;
      }

      .day-title {
        font-size: 1.45rem;
      }

      .trend-row {
        grid-template-columns: 78px 1fr 32px;
        gap: 8px;
      }
    }
    """


def _latest_label(day: DayArchive | None) -> str:
    if day is None:
        return "No digest runs yet"
    return f"{day.generated_at.strftime('%Y-%m-%d %H:%M:%S')} ({day.timezone})"


def _format_seen_label(value: datetime) -> str:
    timezone = value.tzname() or "UTC"
    return f"{value.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})"


def _sum_counts(points: list[CountPoint], limit: int) -> int:
    return sum(point.count for point in points[:limit])


def _sum_active_days(points: list[CountPoint], limit: int) -> int:
    return sum(1 for point in points[:limit] if point.count > 0)


def _find_feed(day: DayArchive, name: str) -> FeedArchive | None:
    for feed in day.feeds:
        if feed.name == name:
            return feed
    return None


def _parse_optional_datetime(
    value: object,
    *,
    fallback: datetime,
    digest_json_path: Path,
) -> datetime:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        raise ArchiveSiteError(f"naive paper datetime in {digest_json_path}")
    return parsed


def _optional_clean_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _optional_feedback_status(value: object) -> FeedbackStatus | None:
    cleaned = _optional_clean_string(value)
    if cleaned is None:
        return None
    normalized = cleaned.lower()
    if normalized not in {"star", "follow_up", "reading", "done", "ignore"}:
        return None
    return cast(FeedbackStatus, normalized)


def _normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        key = stripped.casefold()
        if not stripped or key in seen:
            continue
        seen.add(key)
        normalized.append(stripped)
    return normalized


def _normalize_source_url_map(
    value: object,
    *,
    source: str,
    abstract_url: str,
    paper_id: str,
    doi: str | None,
    arxiv_id: str | None,
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not isinstance(item, str):
                continue
            stripped_key = key.strip().lower()
            stripped_value = item.strip()
            if stripped_key and stripped_value:
                normalized[stripped_key] = stripped_value
    if source and abstract_url:
        normalized.setdefault(source, abstract_url)
    if doi:
        normalized.setdefault("doi", f"https://doi.org/{doi}")
    if arxiv_id:
        normalized.setdefault("arxiv", f"https://arxiv.org/abs/{arxiv_id}")
    if source == "pubmed" and paper_id.startswith("pubmed:"):
        normalized.setdefault(
            "pubmed",
            f"https://pubmed.ncbi.nlm.nih.gov/{paper_id.removeprefix('pubmed:')}/",
        )
    if source == "openalex" and paper_id.startswith("openalex:"):
        normalized.setdefault(
            "openalex",
            f"https://openalex.org/{paper_id.removeprefix('openalex:')}",
        )
    return normalized


def _resolve_feedback_status(
    canonical_id: str,
    archived_status: FeedbackStatus | None,
    feedback_state: FeedbackState | None,
) -> FeedbackStatus | None:
    if feedback_state is not None:
        entry = feedback_state.papers.get(canonical_id)
        if entry is not None:
            return entry.status
    return archived_status


def _resolve_feedback_updated_at(
    canonical_id: str,
    feedback_state: FeedbackState | None,
) -> datetime | None:
    if feedback_state is None:
        return None
    entry = feedback_state.papers.get(canonical_id)
    if entry is None:
        return None
    return entry.updated_at


def _resolve_feedback_note(
    canonical_id: str,
    archived_note: str | None,
    feedback_state: FeedbackState | None,
) -> str | None:
    if feedback_state is not None:
        entry = feedback_state.papers.get(canonical_id)
        if entry is not None and entry.note is not None:
            return entry.note
    return archived_note


def _canonical_id_from_payload(
    canonical_id: object,
    paper_id: object,
    abstract_url: str,
    title: str,
) -> str:
    if isinstance(canonical_id, str) and canonical_id.strip():
        return canonical_id.strip()
    raw_paper_id = _optional_clean_string(paper_id)
    if raw_paper_id:
        normalized = raw_paper_id.lower()
        if normalized.startswith("https://doi.org/"):
            return f"doi:{normalized.removeprefix('https://doi.org/')}"
        if normalized.startswith("pubmed:"):
            return normalized
    if "arxiv.org/abs/" in abstract_url:
        return "arxiv:" + abstract_url.rstrip("/").split("/")[-1].lower().split("v")[0]
    normalized_title = re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
    return "title:" + " ".join(normalized_title.split())


def _paper_slug(canonical_id: str) -> str:
    prefix = canonical_id.split(":", 1)[0]
    digest = hashlib.sha1(canonical_id.encode("utf-8")).hexdigest()[:12]
    return f"{_slugify(prefix)}-{digest}"


def _source_display_label(value: str) -> str:
    labels = {
        "arxiv": "arXiv",
        "doi": "DOI",
        "openalex": "OpenAlex",
        "semantic_scholar": "Semantic Scholar",
        "pubmed": "PubMed",
        "crossref": "Crossref",
    }
    return labels.get(value.lower(), value)


def _normalize_keywords(keywords: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for keyword in keywords:
        stripped = keyword.strip()
        key = stripped.lower()
        if not stripped or key in seen:
            continue
        seen.add(key)
        normalized.append(stripped)
    return normalized


def _normalize_search(value: str) -> str:
    return " ".join(value.lower().split())


def _slugify(value: str) -> str:
    ascii_value = value.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    if slug:
        return slug
    return "item-" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _truncate(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
