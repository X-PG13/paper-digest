# Paper Digest

[![CI](https://img.shields.io/github/actions/workflow/status/X-PG13/paper-digest/ci.yml?branch=main&label=CI)](https://github.com/X-PG13/paper-digest/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/X-PG13/paper-digest?display_name=tag)](https://github.com/X-PG13/paper-digest/releases)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Paper Digest is a small but production-minded Python project for pulling the
latest research papers every day and turning them into a readable digest.

The current scope is intentionally narrow:

- Fetch the newest papers from arXiv, Crossref, PubMed, Semantic Scholar, and OpenAlex.
- Apply include and exclude keyword filters on title and abstract.
- Optionally enrich selected papers with structured LLM analysis.
- Generate machine-readable `JSON` and human-readable `Markdown`.
- Build a static archive site with search, feed subscriptions, topic tracking,
  trend views, and RSS subscription feeds.
- Persist state to avoid repeating already-sent papers.
- Optionally deliver the digest through SMTP email, Feishu webhooks, WeCom
  webhooks, Slack incoming webhooks, Discord incoming webhooks, or Telegram bots.
- Stay easy to automate from `cron`, GitHub Actions, or a notification bot.

## Project Goals

This repository is structured to grow like a real open-source project rather
than a one-off script. The baseline includes:

- Clear packaging metadata and typed Python modules.
- Config validation with actionable error messages.
- Unit tests for config loading, parsing, filtering, and service orchestration.
- CI-ready commands for tests, linting, and type checking.
- Contributor-facing docs such as `LICENSE`, `CONTRIBUTING.md`, and `SECURITY.md`.
- Maintainer automation such as `pre-commit`, Dependabot, and tag-based release builds.

## Installation

Create a virtual environment and install the project:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Quick Start

1. Copy the example config:

```bash
cp config.example.toml config.toml
```

2. Generate the digest:

```bash
python -m paper_digest --config config.toml
```

3. Inspect the outputs:

- `output/latest.json`
- `output/latest.md`
- `output/site/index.html`
- `output/YYYY-MM-DD/digest.json`
- `output/YYYY-MM-DD/digest.md`

## Configuration

Example:

```toml
[app]
timezone = "Asia/Shanghai"
lookback_hours = 24
output_dir = "output"
request_delay_seconds = 3
request_timeout_seconds = 60
fetch_retry_attempts = 4
fetch_retry_backoff_seconds = 10

[[feeds]]
name = "LLM"
categories = ["cs.AI", "cs.CL", "cs.LG"]
keywords = ["agent", "reasoning", "alignment"]
exclude_keywords = ["survey"]
max_results = 100
max_items = 15
```

Field reference:

- `timezone`: Timezone used for display and output folder naming.
- `lookback_hours`: Papers older than this time window are ignored.
- `output_dir`: Directory where dated and latest digests are written.
- `request_delay_seconds`: Delay between arXiv API requests.
- `request_timeout_seconds`: Per-request timeout for arXiv, Crossref, PubMed,
  Semantic Scholar, and OpenAlex fetches.
- `fetch_retry_attempts`: Maximum number of fetch attempts for transient failures.
- `fetch_retry_backoff_seconds`: Base backoff used between retry attempts.
- `openalex_api_key_env`: Optional environment variable name for an OpenAlex API
  key on manual or scheduled runs.
- `state`: Persistent history used for deduplication across runs.
- `source`: `arxiv`, `crossref`, `pubmed`, `semantic_scholar`, or `openalex`.
- `categories`: arXiv categories such as `cs.AI`, `cs.CL`, or `cs.CV`.
- `queries`: Required for `crossref`, `pubmed`, `semantic_scholar`, and
  `openalex` feeds.
- `types`: Optional Crossref work types such as `journal-article`, PubMed
  publication types such as `Journal Article` or `Review`, or Semantic Scholar
  publication types such as `Review` or `JournalArticle`, or OpenAlex work
  types such as `article` or `preprint`.
- `keywords`: Keep a paper when any keyword matches title or abstract.
- `exclude_keywords`: Drop a paper when any excluded keyword matches.
- `max_results`: Number of newest candidates fetched before local filtering.
- `max_items`: Maximum number of papers emitted for that feed.
- `digest`: Rendering options for template selection and feed-level briefings.
- `analysis`: Optional structured paper analysis, currently backed by OpenAI.
- `deliveries`: Optional notification outputs such as email, Feishu webhook,
  WeCom webhook, Slack webhook, Discord webhook, or Telegram bot.
- `output/site`: Generated static archive site for historical browsing.

Digest rendering:

```toml
[digest]
template = "default"
top_highlights = 3
feed_key_points = 3
```

Optional LLM analysis:

```toml
[analysis]
enabled = true
provider = "openai"
model = "gpt-5-mini"
api_key_env = "OPENAI_API_KEY"
base_url = "https://api.openai.com/v1/responses"
timeout_seconds = 60
max_papers = 8
max_output_tokens = 600
language = "English"
reasoning_effort = "minimal"
```

Digest notes:

- `feed_key_points` controls how many feed-level "today's key points" lines
  appear before the detailed paper list.
- `template = "zh_daily_brief"` switches the output into a Chinese briefing
  layout with a topic-organized "今日重点" section plus per-feed "本组速览".
- `zh_daily_brief` works even when analysis is disabled. In that mode, the
  project generates rule-based Chinese briefing scaffolding around the raw
  paper title and abstract summary, including high-frequency topic extraction,
  rule-based tags such as `方法` / `数据` / `应用`, and topic-oriented highlights.

Analysis notes:

- Analysis is disabled by default. If the section is omitted or `enabled = false`,
  the digest keeps using the original abstract summary only.
- Analysis runs after filtering and deduplication, so you only spend tokens on
  papers that actually make it into the digest.
- `max_papers` caps analysis cost for a single run. Papers beyond that limit
  still appear in the digest with their raw abstract summaries.
- When analysis is enabled, the Markdown and notification outputs add:
  top-of-digest highlights, a one-sentence conclusion per paper, contribution
  bullets, best-fit audience, and likely limitations.
- A practical Chinese setup is `language = "Chinese"` plus
  `[digest] template = "zh_daily_brief"`.
- For backward compatibility, legacy `template`, `top_highlights`, and
  `feed_key_points` values under `[analysis]` are still accepted when `[digest]`
  is omitted.

Preferred notification setup:

```toml
[[deliveries]]
type = "email"
smtp_host = "smtp.example.com"
smtp_port = 465
username = "bot@example.com"
password_env = "PAPER_DIGEST_SMTP_PASSWORD"
from_address = "bot@example.com"
to_addresses = ["you@example.com"]
use_tls = true
use_starttls = false
subject_prefix = "[Paper Digest]"
skip_if_empty = true
target = "digest"

[[deliveries]]
type = "feishu_webhook"
webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/your-token"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"

[[deliveries]]
type = "wecom_webhook"
webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"

[[deliveries]]
type = "slack_webhook"
webhook_url = "https://hooks.slack.com/services/T000/B000/your-secret"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"

[[deliveries]]
type = "discord_webhook"
webhook_url = "https://discord.com/api/webhooks/123456789012345678/your-secret"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"

[[deliveries]]
type = "telegram_bot"
bot_token = "123456:telegram-bot-token"
chat_id = "-1001234567890"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"
```

Notes:

- Keep the SMTP password in an environment variable instead of the config file.
- Feishu delivery uses the incoming webhook URL directly; keep it in your
  untracked `config.toml` or a GitHub secret-backed config.
- WeCom delivery uses the group robot webhook URL directly; keep it in your
  untracked `config.toml` or a GitHub secret-backed config.
- Slack delivery uses an incoming webhook URL directly; keep it in your
  untracked `config.toml` or a GitHub secret-backed config.
- Discord delivery uses an incoming webhook URL directly; keep it in your
  untracked `config.toml` or a GitHub secret-backed config.
- Telegram delivery uses a bot token plus target chat ID; keep them in your
  untracked `config.toml` or a GitHub secret-backed config.
- OpenAlex can run without an API key for lightweight usage, but an
  `OPENALEX_API_KEY` wired through `app.openalex_api_key_env` is the safer
  production path for newer OpenAlex rate-limit rules.
- Use either `use_tls = true` for implicit TLS, usually port `465`, or
  `use_starttls = true` for STARTTLS, usually port `587`.
- `skip_if_empty = true` suppresses notifications when a digest or feed has no
  new papers.
- `target = "digest"` sends one message for the whole run.
- `target = "per_feed"` sends one message per feed, with the title including
  the date and that feed's hit count.
- Legacy `[email]` config is still supported for backward compatibility.
- Delivery failures return a non-zero exit code, keep generated artifacts on
  disk, and do not persist dedup state for that run.

Additional source examples:

```toml
[[feeds]]
name = "Crossref AI"
source = "crossref"
queries = ["agent reasoning benchmark"]
types = ["journal-article", "proceedings-article"]
keywords = ["agent", "reasoning"]
exclude_keywords = []
max_results = 50
max_items = 10

[[feeds]]
name = "PubMed AI"
source = "pubmed"
queries = ["agent systems", "clinical benchmark"]
types = ["Journal Article", "Review"]
keywords = ["agent", "benchmark"]
exclude_keywords = ["protocol"]
max_results = 50
max_items = 10

[[feeds]]
name = "Semantic Scholar AI"
source = "semantic_scholar"
queries = ["large language model", "agent systems"]
types = ["Review", "JournalArticle"]
keywords = ["agent", "benchmark"]
exclude_keywords = ["survey"]
max_results = 50
max_items = 10

[[feeds]]
name = "OpenAlex AI"
source = "openalex"
queries = ["large language model", "agent systems"]
types = ["article", "preprint"]
keywords = ["agent", "benchmark"]
exclude_keywords = ["survey"]
max_results = 50
max_items = 10
```

## Development

Common commands:

```bash
pre-commit install
make test
make lint
make typecheck
make coverage
make build
make release-check
make run
```

The project currently uses only the Python standard library at runtime.

Additional maintainer docs:

- `docs/architecture.md`
- `docs/maintainer-guide.md`
- `RELEASING.md`

## Scheduling

The repository includes a scheduled workflow at
[`daily-digest.yml`](./.github/workflows/daily-digest.yml).

The default schedule is `5 0 * * *`, which means:

- `00:05 UTC` every day
- `08:05` every day in `Asia/Shanghai`

To use it, create these GitHub repository secrets:

- `PAPER_DIGEST_CONFIG_TOML`: your full `config.toml` content
- `OPENAI_API_KEY`: needed when `[analysis] enabled = true`
- `OPENALEX_API_KEY`: optional, only needed when an OpenAlex feed sets
  `app.openalex_api_key_env = "OPENALEX_API_KEY"`
- `PAPER_DIGEST_SMTP_PASSWORD`: only needed when email delivery is enabled

For manual validation runs, `workflow_dispatch` also accepts an optional
`config_toml_override` input. When you provide it, that run uses the temporary
config instead of `PAPER_DIGEST_CONFIG_TOML`.

The workflow restores and saves `.paper-digest-state/` through the GitHub
Actions cache so deduplication survives across runs.

It also restores and saves `output/` history through the GitHub Actions cache.
That keeps dated digest folders alive across runs, so feed pages, keyword pages,
trend views, and RSS subscriptions can reflect accumulated history instead of
only the latest execution.

Temporary manual runs with `config_toml_override` are intentionally isolated:

- they skip digest state cache restore and save
- they skip archive history cache restore and save
- they skip GitHub Pages deployment

That makes them safe for validating new feeds or delivery channels without
polluting the formal archive, dedup state, or live Pages site.

For repositories that added archive caching after the project was already
running, there is also a manual backfill workflow at
[`backfill-archive-history.yml`](./.github/workflows/backfill-archive-history.yml).
It downloads historical successful `Daily Digest` artifacts, imports the
strongest snapshot for each day into `output/YYYY-MM-DD/`, rebuilds the archive
site and RSS feeds, and then seeds the same `output/` cache used by the daily
workflow. Synthetic validation runs such as delivery-check digests are skipped
so they do not pollute the long-term archive.

That workflow now accepts three manual inputs:

- `run_limit`: how many successful `Daily Digest` runs to inspect
- `date_from`: optional inclusive earliest digest date to import
- `date_to`: optional inclusive latest digest date to import
- `dry_run`: preview what would change without writing `output/`, cache, or Pages

That makes it practical to do a narrow backfill such as "only recover the last
30 successful runs" or "rebuild just 2026-04-01 through 2026-04-07" without
editing workflow code. It also lets you preview a risky backfill first, inspect
the run log for imported and replaced dates, and then re-run without `dry_run`.

For scheduled stability, source fetches use bounded retry and backoff for
transient `429`, `5xx`, and timeout-style failures. You can tune that behavior
through `request_timeout_seconds`, `fetch_retry_attempts`, and
`fetch_retry_backoff_seconds` in `[app]`.

The CLI also rebuilds `output/site/index.html` on every run. That static site:

- shows daily hit counts and per-feed summaries
- links to each day's Markdown and JSON
- supports feed filtering, title keyword search, and recent `7d` / `30d` windows
- emits fixed feed pages under `output/site/feeds/`
- emits feed RSS files under `output/site/feeds/*.xml`
- emits keyword tracking pages under `output/site/topics/` from configured feed keywords
- emits keyword RSS files under `output/site/topics/*.xml`
- emits a `output/site/trends.html` overview for feed and keyword subscription trends

When GitHub Pages is enabled for the repository, the scheduled workflow uploads
`output/site` and deploys it automatically after each successful digest run.

On macOS or Linux you can run the digest every morning with `cron`:

```cron
0 8 * * * /absolute/path/to/.venv/bin/python -m paper_digest --config /absolute/path/to/config.toml
```

## Roadmap

- Add more literature sources such as Lens or CORE.
- Support more output adapters such as Matrix.
- Support additional LLM providers and richer feed-level briefings.

## Status

The project is usable today for daily arXiv monitoring, but it is still early.
Expect API and config changes while the repository matures.
