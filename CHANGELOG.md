# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic
Versioning.

## [Unreleased]

- Papers now carry a canonical identity, relevance score, and match reasons so
  the digest can deduplicate across sources, keep richer merged records, and
  explain why each paper surfaced.
- The manual `Daily Digest` workflow now accepts a temporary `config.toml`
  override input and isolates those validation runs from caches and Pages
  deployment.
- OpenAlex joins arXiv, Crossref, PubMed, and Semantic Scholar as a supported
  literature source.
- Semantic Scholar joins arXiv, Crossref, and PubMed as a supported literature
  source.
- PubMed joins arXiv and Crossref as a third supported literature source.
- Slack incoming webhook delivery joins email, Feishu, and WeCom as a
  first-class notification channel.
- Discord incoming webhook delivery joins email, Feishu, WeCom, and Slack as a
  first-class notification channel.
- Telegram bot delivery joins email, Feishu, WeCom, Slack, and Discord as a
  first-class notification channel.
- Static archive site now includes fixed feed subscription pages, keyword
  tracking pages, and a trends overview alongside the daily archive index.
- Archive subscription pages now publish RSS feeds for both fixed feed views
  and keyword tracking views.
- The scheduled GitHub Actions workflow now restores and saves `output/`
  history, so archive pages, trends, and RSS feeds can accumulate across runs.
- A manual archive backfill workflow can import historical successful
  `Daily Digest` artifacts into `output/`, rebuild the site and RSS, and seed
  the archive cache in one pass while skipping synthetic validation digests.
- The manual backfill workflow now supports configurable run limits and
  inclusive date windows for targeted archive recovery.
- The manual backfill workflow can also run in dry-run mode to preview imports
  and replacements without mutating `output/`, cache, or Pages.
- WeCom webhook delivery joins email and Feishu as a first-class notification
  channel.
- Rule-based Chinese briefing mode now extracts recurring topic terms, assigns
  lightweight paper tags, and organizes "今日重点" around topics instead of
  only feed order.

## [0.4.1] - 2026-04-09

- Configurable request timeout, retry attempts, and retry backoff for upstream
  source fetches.
- Shared network retry handling for transient timeout, `429`, and `5xx` source
  failures across arXiv and Crossref fetches.
- GitHub Actions workflows updated for Node 24 compatibility, including the
  Pages deployment and release paths.

## [0.4.0] - 2026-04-09

- Static archive-site generation from historical digest outputs, including
  daily hit counts, per-feed summaries, and lightweight client-side search.
- GitHub Pages deployment from the scheduled `Daily Digest` workflow.
- Bounded retry and backoff handling for transient arXiv `429` and `5xx`
  responses during scheduled fetches.

## [0.3.0] - 2026-04-08

- Optional OpenAI-backed structured paper analysis with configurable cost caps.
- Top-of-digest highlights plus richer per-paper conclusions, contributions,
  audience guidance, and limitations in Markdown, email, and Feishu output.
- A stronger digest templating path with feed-level key points and a Chinese
  `zh_daily_brief` layout for "今日重点"-style reports.
- Digest template selection is now independent from LLM analysis, so the
  Chinese daily brief can run in rule-based mode without any API key.

## [0.2.0] - 2026-04-08

- Optional SMTP email delivery for generated digests.
- Persistent state-based deduplication across runs.
- Crossref support as a second paper source.
- A scheduled GitHub Actions workflow for daily digest generation.
- A unified delivery layer with feed-level notification fan-out.
- Feishu webhook delivery support.
- Expanded unit coverage for arXiv parsing, Crossref parsing, digest rendering,
  output writing, delivery orchestration, and state management.

## [0.1.0] - 2026-04-08

### Added

- Initial arXiv-backed daily paper digest generator.
- TOML-based configuration with category and keyword filtering.
- Markdown and JSON output writers.
- Local unit tests, CI workflow, and core contributor documentation.
- Pre-commit configuration for local repository hygiene.
- Dependabot configuration for dependency and GitHub Actions updates.
- Release workflow, release checklist, and maintainer-facing documentation.
- Coverage, build, and distribution validation commands.
- CLI-focused unit tests and single-source version metadata.
