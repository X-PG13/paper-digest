# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic
Versioning.

## [Unreleased]

- Static archive-site generation from historical digest outputs, including
  daily hit counts, per-feed summaries, and lightweight client-side search.
- GitHub Pages deployment from the scheduled `Daily Digest` workflow.

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
