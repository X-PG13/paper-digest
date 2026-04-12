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
  canonical paper detail pages, rising-paper views, trend views, and RSS
  subscription feeds.
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
- `output/site/reading-list.html`
- `output/site/review-queue.html`
- `output/site/weekly-review.html`
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
- `feedback`: Local per-paper feedback state keyed by `canonical_id`.
- `notify`: Feedback-driven notification focus rules.
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
- `sort_by`: Optional per-feed override for `relevance`, `published_at`, or
  `hybrid`.
- `digest`: Rendering options for template selection and feed-level briefings.
- `ranking`: Default ranking strategy and relevance-weight tuning.
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

Ranking strategy:

```toml
[ranking]
sort_by = "hybrid"
title_match_weight = 40
summary_match_weight = 18
doi_weight = 12
pdf_weight = 8
rich_summary_weight = 6
metadata_weight = 4
multi_source_weight = 10
freshness_weight_cap = 24
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
- `sort_by = "hybrid"` is the default and keeps the current behavior:
  relevance-first ranking with `published_at` as the tie-breaker.
- `sort_by = "published_at"` keeps the newest papers first and uses
  `relevance_score` only as an explanatory secondary signal.
- `sort_by = "relevance"` keeps the strongest keyword and metadata matches at
  the top, even when several papers are similarly recent.
- `template = "zh_daily_brief"` switches the output into a Chinese briefing
  layout with a topic-organized "今日重点" section plus per-feed "本组速览".
- `zh_daily_brief` works even when analysis is disabled. In that mode, the
  project generates rule-based Chinese briefing scaffolding around the raw
  paper title and abstract summary, including high-frequency topic extraction,
  rule-based tags such as `方法` / `数据` / `应用`, and topic-oriented highlights.
- The JSON output now records the active sorting summary, per-feed `sort_by`,
  `relevance_score`, and `match_reasons` so downstream archive pages and
  integrations can explain why each paper surfaced.

Feedback loop:

```toml
[feedback]
enabled = true
path = ".paper-digest-state/feedback.json"
star_boost = 80
follow_up_boost = 35
reading_boost = 18
done_penalty = 20
ignore_penalty = 120
hide_ignored = true
```

- Feedback is keyed by canonical paper identity: DOI first, then arXiv id,
  then a normalized title fallback.
- Supported statuses are `star`, `follow_up`, `reading`, `done`, and `ignore`.
- `star`, `follow_up`, and `reading` boost ranking; `done` lowers priority;
  `ignore` either hides papers or down-ranks them, depending on
  `hide_ignored`.
- Each feedback entry can also carry a free-form `note`, a concrete
  `next_action`, an optional `due_date`, a temporary `snoozed_until`, and an
  optional `review_interval_days`, so you can record both why you marked a
  paper and how it should re-enter your workflow later.
- The archive site exposes a dedicated `output/site/reading-list.html` page
  that aggregates starred, follow-up, and in-progress papers.
- The archive site also exposes `output/site/weekly-review.html`, which groups
  papers into pending, in-progress, completed, and resurfaced buckets.
- The archive site exposes `output/site/review-queue.html`, which highlights
  overdue items, papers due within 3 days, queued next actions, newly surfaced
  unmarked papers, and resurfaced follow-ups.
- Paper detail pages, reading lists, weekly review sections, review queues, and
  Focus outputs all surface those feedback notes, next actions, and due dates
  once they are present.

Notification focus:

```toml
[notify]
feedback_only = false
include_new_starred = true
include_follow_up_resurfaced = true
include_starred_momentum = true
max_focus_items = 5
max_action_items = 5
action_overdue_only = false
# action_due_within_days = 7
```

- Notification outputs now include a dedicated `Focus` block when a paper was
  newly starred, a `follow_up` paper resurfaced in the current scan, or a
  starred paper newly entered the momentum view.
- `feedback_only = true` turns webhook or email notifications into a
  feedback-driven briefing that only pushes the Focus and action sections.
- Focus items explain why they were pushed, preserve the paper's
  `star` / `follow_up` status, and surface coverage context such as active days,
  feed span, and appearance count.
- Daily digests now also include a dedicated "本周该处理什么" section for
  overdue items, papers due within 3 days, and queued next actions on
  `star` / `follow_up` / `reading` papers.
- `max_action_items` caps how many action reminders get rendered into one run.
- `action_overdue_only = true` narrows action reminders to already overdue
  items.
- `action_due_within_days = 7` is the lighter-weight alternative when you want
  to keep only near-term action reminders.
- These `[notify]` action settings define the global action pool before any
  delivery-specific filters are applied.

Example feedback file:

```json
{
  "version": 1,
  "papers": {
    "doi:10.5555/paper-circle": {
      "status": "star",
      "updated_at": "2026-04-10T09:15:00+08:00",
      "note": "use this as the anchor paper for next week's review"
    },
    "arxiv:2604.00001": "reading",
    "title:example-normalized-title": "done"
  }
}
```

You can manage that file without editing JSON directly:

```bash
python -m paper_digest feedback set 'doi:10.5555/paper-circle' star --config config.toml
python -m paper_digest feedback set 'doi:10.5555/paper-circle' follow_up --config config.toml
python -m paper_digest feedback set 'doi:10.5555/paper-circle' reading --config config.toml
python -m paper_digest feedback set 'doi:10.5555/paper-circle' done --config config.toml
python -m paper_digest feedback set 'doi:10.5555/paper-circle' star --note 'anchor paper for review' --config config.toml
python -m paper_digest feedback note 'doi:10.5555/paper-circle' 'compare section 4 with baseline table' --config config.toml
python -m paper_digest feedback action set 'doi:10.5555/paper-circle' 'compare baseline table' --config config.toml
python -m paper_digest feedback due set 'doi:10.5555/paper-circle' 2026-04-18 --config config.toml
python -m paper_digest feedback snooze set 'doi:10.5555/paper-circle' 2026-04-20 --config config.toml
python -m paper_digest feedback interval set 'doi:10.5555/paper-circle' 14 --config config.toml
python -m paper_digest feedback action clear 'doi:10.5555/paper-circle' --config config.toml
python -m paper_digest feedback due clear 'doi:10.5555/paper-circle' --config config.toml
python -m paper_digest feedback snooze clear 'doi:10.5555/paper-circle' --config config.toml
python -m paper_digest feedback interval clear 'doi:10.5555/paper-circle' --config config.toml
python -m paper_digest feedback clear-note 'doi:10.5555/paper-circle' --config config.toml
python -m paper_digest feedback sync-github-secret --config config.toml
python -m paper_digest feedback clear 'doi:10.5555/paper-circle' --config config.toml
python -m paper_digest feedback list --config config.toml
```

To sync your local feedback state into GitHub Actions without hand-copying JSON:

```bash
python -m paper_digest feedback sync-github-secret --config config.toml
python -m paper_digest feedback sync-github-secret --repo X-PG13/paper-digest --secret-name PAPER_DIGEST_FEEDBACK_JSON --config config.toml
```

Notes:

- `feedback sync-github-secret` writes the current local feedback payload into a
  GitHub Actions repository secret by calling `gh secret set`.
- If `--repo` is omitted, the command derives `owner/repo` from the current git
  `origin` remote.
- Pulling the secret value back from GitHub is intentionally not supported
  because GitHub Actions secrets are write-only.

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
include_focus = true
focus_target = "digest"
focus_statuses = ["star", "follow_up"]
focus_reasons = ["new_starred", "follow_up_resurfaced", "starred_momentum"]
focus_max_items = 5
include_actions = true
action_target = "digest"
action_only = false
action_statuses = ["star", "follow_up", "reading"]
action_reasons = ["overdue", "due_soon", "next_action_pending"]
action_max_items = 5
action_overdue_only = false
action_due_within_days = 7

[[deliveries]]
type = "feishu_webhook"
webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/your-token"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"
include_focus = true
focus_target = "separate"
focus_statuses = ["star"]
focus_reasons = ["new_starred", "starred_momentum"]
focus_max_items = 3
include_actions = true
action_target = "separate"
action_only = false
action_statuses = ["reading"]
action_reasons = ["overdue"]
action_max_items = 2
action_overdue_only = true
action_due_within_days = 3

[[deliveries]]
type = "wecom_webhook"
webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"
include_focus = false
focus_target = "digest"
include_actions = true
action_target = "digest"
action_only = false
action_statuses = ["follow_up"]
action_reasons = ["due_soon", "next_action_pending"]
action_max_items = 3
action_overdue_only = false
action_due_within_days = 7

[[deliveries]]
type = "slack_webhook"
webhook_url = "https://hooks.slack.com/services/T000/B000/your-secret"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"
include_actions = true
action_target = "separate"
action_only = false
action_statuses = ["follow_up"]
action_reasons = ["due_soon"]
action_max_items = 2
action_overdue_only = false
action_due_within_days = 3

[[deliveries]]
type = "discord_webhook"
webhook_url = "https://discord.com/api/webhooks/123456789012345678/your-secret"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"
include_actions = true
action_target = "digest"
action_only = false
action_statuses = ["star"]
action_reasons = ["next_action_pending"]
action_max_items = 2
action_overdue_only = false
action_due_within_days = 14

[[deliveries]]
type = "telegram_bot"
bot_token = "123456:telegram-bot-token"
chat_id = "-1001234567890"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "per_feed"
include_actions = true
action_target = "digest"
action_only = false
action_statuses = ["star", "follow_up", "reading"]
action_reasons = ["overdue", "due_soon", "next_action_pending"]
action_max_items = 4
action_overdue_only = false
action_due_within_days = 7
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
- `include_focus = false` keeps the delivery on the normal digest path without
  the feedback-driven Focus block.
- `focus_target = "digest"` keeps Focus inline with the main digest, while
  `focus_target = "separate"` emits a second `Focus Brief` message for that
  delivery when focus items exist.
- `include_actions = false` keeps one delivery on the normal digest path
  without the weekly action section.
- `action_target = "digest"` keeps action reminders inline with the main
  digest, while `action_target = "separate"` emits a dedicated `Action Brief`
  message for that delivery when action items exist.
- `action_only = true` turns one delivery into an action-reminder-only channel
  without suppressing the normal digest for other deliveries.
- `action_statuses = ["star", "follow_up", "reading"]` narrows action
  reminders to specific feedback states for that delivery.
- `action_reasons = ["overdue", "overdue_7d", "due_soon", "next_action_pending", "recurring_review"]`
  narrows action reminders by why they surfaced.
- `action_max_items = 2` caps how many action reminders one delivery gets,
  independent of the global `[notify].max_action_items`.
- `action_overdue_only = true` keeps one delivery focused on overdue work only.
- `action_due_within_days = 3` keeps one delivery focused on near-term work.
- Delivery-level action filters only narrow the global action pool; they do not
  widen past what `[notify]` already emitted.
- `focus_statuses = ["star", "follow_up"]` narrows Focus to specific feedback
  states for that delivery. Leave it empty to accept all Focus statuses.
- `focus_reasons = ["new_starred", "follow_up_resurfaced", "starred_momentum"]`
  narrows Focus to specific trigger types for that delivery. Leave it empty to
  accept all Focus reasons.
- `focus_max_items = 3` overrides the global `[notify].max_focus_items` cap for
  one delivery, so you can keep chat channels tighter than email digests.
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
- `PAPER_DIGEST_FEEDBACK_JSON`: optional local `feedback.json` content used to
  seed `.paper-digest-state/feedback.json` before each run
- `OPENAI_API_KEY`: needed when `[analysis] enabled = true`
- `OPENALEX_API_KEY`: optional, only needed when an OpenAlex feed sets
  `app.openalex_api_key_env = "OPENALEX_API_KEY"`
- `PAPER_DIGEST_SMTP_PASSWORD`: only needed when email delivery is enabled

For manual validation runs, `workflow_dispatch` also accepts an optional
`config_toml_override` input. When you provide it, that run uses the temporary
config instead of `PAPER_DIGEST_CONFIG_TOML`.

The same workflow also accepts an optional `feedback_json_override` input.
When you provide it, that run materializes the given JSON into
`.paper-digest-state/feedback.json` before digest generation. This is useful
for syncing a local reading-list state into GitHub Actions without hand-editing
repository secrets first.

The workflow restores and saves `.paper-digest-state/` through the GitHub
Actions cache so deduplication and local feedback state survive across runs.

Feedback-state precedence for scheduled and manual runs is:

1. `feedback_json_override`
2. `PAPER_DIGEST_FEEDBACK_JSON`
3. cached `.paper-digest-state/feedback.json`

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
- emits canonical paper detail pages under `output/site/papers/` with merged
  source links, match reasons, and lightweight related-paper suggestions
- emits a `output/site/momentum.html` view for papers that keep resurfacing
  across multiple dates or feeds, with first-seen and last-seen timestamps
- emits a `output/site/reading-list.html` view for papers you have starred or
  marked as follow-up or reading in the local feedback state
- emits a `output/site/review-queue.html` view for actionable review work:
  new high-signal unmarked papers, resurfaced follow-ups, starred papers that
  still need attention, and recurring reviews ordered by effective due date
- emits a `output/site/weekly-review.html` view that groups papers into
  overdue, snoozed, pending, reading, completed, and resurfaced weekly review sections
- surfaces personal feedback notes across detail pages, the reading list,
  review queue, weekly review, and feedback-driven Focus blocks
- surfaces `snoozed_until`, recurring review intervals, next actions, and
  effective due dates across detail pages and feedback-centric archive views
- emits fixed feed pages under `output/site/feeds/`
- emits feed RSS files under `output/site/feeds/*.xml`
- emits keyword tracking pages under `output/site/topics/` from configured feed keywords
- emits keyword RSS files under `output/site/topics/*.xml`
- emits a `output/site/trends.html` overview for feed and keyword subscription trends
- exposes `canonical_id` plus copyable feedback CLI snippets on each canonical
  paper detail page, so you can move from browsing to local feedback updates quickly

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
