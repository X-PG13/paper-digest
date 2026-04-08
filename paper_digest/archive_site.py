"""Static archive site generation for digest history."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path


class ArchiveSiteError(RuntimeError):
    """Raised when the archive site cannot be generated."""


@dataclass(slots=True, frozen=True)
class FeedArchive:
    name: str
    count: int
    summary: str
    titles: list[dict[str, str]]


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
    digests: int
    papers: int


def build_archive_site(output_dir: Path) -> Path:
    """Build a static HTML archive under ``output_dir / 'site'``."""

    site_root = output_dir / "site"
    digests_root = site_root / "digests"
    if site_root.exists():
        shutil.rmtree(site_root)
    digests_root.mkdir(parents=True, exist_ok=True)

    archives = _load_archives(output_dir, digests_root)
    _copy_latest_files(output_dir, site_root)
    site_root.joinpath("index.html").write_text(
        _render_index(archives),
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
        feed = _parse_feed(raw_feed, digest_json_path)
        feeds.append(feed)
        total_papers += feed.count
        search_terms.append(feed.name.lower())
        search_terms.extend(title["title"].lower() for title in feed.titles)

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


def _parse_feed(raw_feed: object, digest_json_path: Path) -> FeedArchive:
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

    titles: list[dict[str, str]] = []
    for raw_paper in raw_papers[:5]:
        if not isinstance(raw_paper, dict):
            continue
        title = raw_paper.get("title")
        abstract_url = raw_paper.get("abstract_url")
        if isinstance(title, str) and isinstance(abstract_url, str):
            titles.append({"title": title, "href": abstract_url})

    raw_key_points = raw_feed.get("key_points")
    key_points = (
        [item for item in raw_key_points if isinstance(item, str) and item.strip()]
        if isinstance(raw_key_points, list)
        else []
    )

    summary = _build_feed_summary(name, len(raw_papers), key_points, titles)
    return FeedArchive(
        name=name.strip(),
        count=len(raw_papers),
        summary=summary,
        titles=titles,
    )


def _build_feed_summary(
    name: str,
    count: int,
    key_points: list[str],
    titles: list[dict[str, str]],
) -> str:
    if count == 0:
        return f"{name} 今日没有新的命中文献。"
    if key_points:
        return _truncate("；".join(key_points[:2]), 220)
    if titles:
        label = "、".join(f"《{item['title']}》" for item in titles[:2])
        return _truncate(f"收录 {count} 篇，重点包括{label}。", 220)
    return f"收录 {count} 篇新论文。"


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


def _render_index(archives: list[DayArchive]) -> str:
    latest_archive = archives[0] if archives else None
    feed_names = sorted({feed.name for day in archives for feed in day.feeds})
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
    latest_label = (
        (
            f"{latest_archive.generated_at.strftime('%Y-%m-%d %H:%M:%S')} "
            f"({latest_archive.timezone})"
        )
        if latest_archive is not None
        else "No digest runs yet"
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Paper Digest Archive</title>
  <style>
    :root {{
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
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "IBM Plex Sans", "Segoe UI Variable", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(249, 115, 22, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(180, 83, 9, 0.12), transparent 24%),
        linear-gradient(180deg, var(--bg) 0%, #f8f5ef 100%);
    }}

    a {{
      color: inherit;
    }}

    .shell {{
      width: min(calc(100vw - 32px), var(--max));
      margin: 0 auto;
      padding: 32px 0 64px;
    }}

    .hero {{
      position: relative;
      overflow: hidden;
      padding: 32px;
      border: 1px solid var(--line);
      border-radius: calc(var(--radius) + 6px);
      background:
        linear-gradient(135deg, rgba(255, 250, 241, 0.98), rgba(243, 234, 215, 0.92));
      box-shadow: var(--shadow);
    }}

    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -80px -120px auto;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(249, 115, 22, 0.12), transparent 65%);
      pointer-events: none;
    }}

    .eyebrow {{
      margin: 0 0 12px;
      font-size: 13px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--brand);
    }}

    h1 {{
      margin: 0;
      font-family: "Source Serif 4", Georgia, serif;
      font-size: clamp(2.2rem, 5vw, 4.2rem);
      line-height: 0.98;
    }}

    .hero p {{
      max-width: 760px;
      margin: 18px 0 0;
      font-size: 1.03rem;
      line-height: 1.7;
      color: var(--muted);
    }}

    .hero-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 24px;
    }}

    .hero-link, .filter-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.72);
      font-size: 0.96rem;
      text-decoration: none;
    }}

    .meta-grid, .filter-grid, .archive-grid {{
      display: grid;
      gap: 18px;
    }}

    .meta-grid {{
      margin-top: 22px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }}

    .metric {{
      padding: 18px;
      border-radius: var(--radius);
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
    }}

    .metric-label {{
      margin: 0;
      font-size: 0.9rem;
      color: var(--muted);
    }}

    .metric-value {{
      margin: 10px 0 0;
      font-size: 1.9rem;
      font-weight: 700;
    }}

    .filter-panel {{
      margin-top: 28px;
      padding: 22px;
      border-radius: var(--radius);
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
    }}

    .filter-grid {{
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      align-items: end;
    }}

    .field {{
      display: grid;
      gap: 8px;
    }}

    .field label {{
      font-size: 0.92rem;
      color: var(--muted);
    }}

    .field input, .field select {{
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.86);
      color: var(--text);
      font: inherit;
    }}

    .chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .filter-chip {{
      cursor: pointer;
    }}

    .filter-chip[aria-pressed="true"] {{
      border-color: transparent;
      background: linear-gradient(135deg, var(--brand), var(--brand-soft));
      color: white;
    }}

    .archive-grid {{
      margin-top: 28px;
    }}

    .day-card {{
      padding: 24px;
      border-radius: calc(var(--radius) + 2px);
      border: 1px solid var(--line);
      background: var(--panel-strong);
      box-shadow: var(--shadow);
    }}

    .day-header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
    }}

    .day-title {{
      margin: 0;
      font-family: "Source Serif 4", Georgia, serif;
      font-size: 1.8rem;
    }}

    .day-meta {{
      margin-top: 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      color: var(--muted);
      font-size: 0.92rem;
    }}

    .feed-stack {{
      display: grid;
      gap: 14px;
      margin-top: 22px;
    }}

    .feed-card {{
      padding: 16px 18px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(244, 239, 230, 0.68);
    }}

    .feed-head {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
    }}

    .feed-name {{
      font-size: 1.02rem;
      font-weight: 700;
    }}

    .feed-count {{
      color: var(--brand);
      font-size: 0.92rem;
    }}

    .feed-summary {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.65;
    }}

    .paper-list {{
      margin: 12px 0 0;
      padding-left: 18px;
      display: grid;
      gap: 6px;
      color: var(--muted);
    }}

    .paper-list a {{
      text-decoration: none;
      border-bottom: 1px dashed rgba(154, 52, 18, 0.45);
    }}

    .empty {{
      padding: 28px;
      text-align: center;
      border-radius: calc(var(--radius) + 2px);
      border: 1px dashed var(--line);
      color: var(--muted);
      background: rgba(255, 252, 246, 0.75);
    }}

    .hidden {{
      display: none !important;
    }}

    @media (max-width: 720px) {{
      .shell {{
        width: min(calc(100vw - 20px), var(--max));
        padding-top: 20px;
      }}

      .hero, .filter-panel, .day-card {{
        padding: 20px;
      }}

      .day-title {{
        font-size: 1.45rem;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">Paper Digest Archive</p>
      <h1>研究日报归档页</h1>
      <p>
        汇总每天生成的 digest.json 和 digest.md，支持按 feed 过滤、按标题关键词搜索，
        以及按最近 7 天、30 天或全部历史查看归档。
      </p>
      <div class="hero-links">
        <a class="hero-link" href="latest.md">查看最新 Markdown</a>
        <a class="hero-link" href="latest.json">查看最新 JSON</a>
        <span class="hero-link">最近构建：{escape(latest_label)}</span>
      </div>
      <div class="meta-grid">
        {"".join(_render_stats_card(item) for item in stats)}
      </div>
    </section>

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

    <section class="archive-grid" id="archive-grid">
      {cards_html}
    </section>
    <section class="empty hidden" id="empty-state">
      当前筛选条件下没有匹配的归档。
    </section>
  </main>

  <script>
    const searchInput = document.getElementById("title-search");
    const feedFilter = document.getElementById("feed-filter");
    const emptyState = document.getElementById("empty-state");
    const cards = Array.from(document.querySelectorAll(".day-card"));
    const chips = Array.from(document.querySelectorAll(".filter-chip"));
    let activeDays = "30";

    function setActiveChip(value) {{
      activeDays = value;
      for (const chip of chips) {{
        chip.setAttribute("aria-pressed", String(chip.dataset.days === value));
      }}
      applyFilters();
    }}

    function normalize(value) {{
      return value.trim().toLowerCase();
    }}

    function applyFilters() {{
      const query = normalize(searchInput.value);
      const activeFeed = normalize(feedFilter.value);
      let visibleCount = 0;

      for (const card of cards) {{
        const daysAgo = Number(card.dataset.daysAgo || "0");
        const searchText = normalize(card.dataset.searchText || "");
        const feedNames = normalize(card.dataset.feedNames || "");
        const matchesDays = activeDays === "all" || daysAgo < Number(activeDays);
        const matchesQuery = query === "" || searchText.includes(query);
        const matchesFeed =
          activeFeed === "" || feedNames.includes("|" + activeFeed + "|");
        const visible = matchesDays && matchesQuery && matchesFeed;
        card.classList.toggle("hidden", !visible);

        for (const feedCard of card.querySelectorAll(".feed-card")) {{
          const feedName = normalize(feedCard.dataset.feedName || "");
          const feedVisible = activeFeed === "" || feedName === activeFeed;
          feedCard.classList.toggle("hidden", !feedVisible);
        }}

        if (visible) {{
          visibleCount += 1;
        }}
      }}

      emptyState.classList.toggle("hidden", visibleCount > 0);
    }}

    searchInput.addEventListener("input", applyFilters);
    feedFilter.addEventListener("change", applyFilters);
    for (const chip of chips) {{
      chip.addEventListener("click", () => setActiveChip(chip.dataset.days || "all"));
    }}
    applyFilters();
  </script>
</body>
</html>
"""


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
        digests=len(relevant),
        papers=sum(day.total_papers for day in relevant),
    )


def _render_stats_card(stats: ArchiveStats) -> str:
    return (
        '<article class="metric">'
        f'<p class="metric-label">{escape(stats.label)}</p>'
        f'<p class="metric-value">{stats.papers}</p>'
        f'<p class="metric-label">{stats.digests} 个 digest</p>'
        "</article>"
    )


def _render_day_card(day: DayArchive) -> str:
    generated_label = (
        f"{day.generated_at.strftime('%Y-%m-%d %H:%M:%S')} ({day.timezone})"
    )
    feed_names = "|" + "|".join(feed.name.lower() for feed in day.feeds) + "|"
    feed_cards = "\n".join(_render_feed_card(feed) for feed in day.feeds)
    return (
        f'<article class="day-card" data-days-ago="{day.days_ago}" '
        f'data-search-text="{escape(day.search_text)}" '
        f'data-feed-names="{escape(feed_names)}">'
        '<header class="day-header">'
        "<div>"
        f'<h2 class="day-title">{escape(day.date)}</h2>'
        '<div class="day-meta">'
        f"<span>命中 {day.total_papers} 篇</span>"
        f"<span>生成于 {escape(generated_label)}</span>"
        "</div>"
        "</div>"
        '<div class="hero-links">'
        f'<a class="hero-link" href="{escape(day.markdown_href)}">Markdown</a>'
        f'<a class="hero-link" href="{escape(day.json_href)}">JSON</a>'
        "</div>"
        "</header>"
        f'<div class="feed-stack">{feed_cards}</div>'
        "</article>"
    )


def _render_feed_card(feed: FeedArchive) -> str:
    titles = "".join(
        "<li>"
        f'<a href="{escape(item["href"])}" target="_blank" '
        f'rel="noreferrer">{escape(item["title"])}</a>'
        "</li>"
        for item in feed.titles
    )
    title_list = f'<ol class="paper-list">{titles}</ol>' if titles else ""
    return (
        f'<section class="feed-card" data-feed-name="{escape(feed.name.lower())}">'
        '<div class="feed-head">'
        f'<span class="feed-name">{escape(feed.name)}</span>'
        f'<span class="feed-count">{feed.count} 篇</span>'
        "</div>"
        f'<p class="feed-summary">{escape(feed.summary)}</p>'
        f"{title_list}"
        "</section>"
    )


def _render_empty_state() -> str:
    return '<div class="empty">还没有可归档的 digest 输出。</div>'


def _truncate(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
