# Architecture

This project is intentionally small, but the module boundaries are designed to
scale as new paper sources and output channels are added.

## Current Layers

### `paper_digest.config`

- Loads TOML configuration from disk.
- Validates user input early.
- Resolves relative paths against the config file location.

### `paper_digest.arxiv_client`

- Builds arXiv API queries.
- Fetches Atom feeds.
- Parses raw XML into typed `Paper` objects.

### `paper_digest.crossref_client`

- Fetches newly indexed works from Crossref.
- Normalizes Crossref JSON into the shared `Paper` model.

### `paper_digest.pubmed_client`

- Searches PubMed for recently entered records with configured free-text
  queries.
- Fetches PubMed XML for matching PMID batches.
- Normalizes PubMed metadata, abstracts, authors, and publication types into
  the shared `Paper` model.

### `paper_digest.semantic_scholar_client`

- Fetches recently published records from the Semantic Scholar Graph API bulk
  search endpoint.
- Normalizes Semantic Scholar JSON metadata, authors, publication dates, and
  open-access links into the shared `Paper` model.

### `paper_digest.openalex_client`

- Fetches recently published works from the OpenAlex Works API with free-text
  search, date-window filters, and optional type filtering.
- Normalizes OpenAlex JSON metadata, reconstructed abstracts, authors, and
  topic/type metadata into the shared `Paper` model.

### `paper_digest.analysis`

- Selects which papers should be enriched in a given run.
- Applies structured paper analysis and builds top-of-digest highlights,
  topic clusters, and per-feed key points.
- Also supports rule-based briefing generation when a richer digest template is
  requested without enabling any LLM provider, including high-frequency topic
  extraction and rule-based paper tags.
- Keeps analysis policy out of the fetch and delivery layers.

### `paper_digest.openai_analysis`

- Calls the OpenAI Responses API for structured per-paper analysis.
- Converts raw responses into the shared `PaperAnalysis` model.

### `paper_digest.digest`

- Applies filtering rules such as lookback windows and keyword matching.
- Renders digest output for JSON and Markdown, including optional highlights,
  topic sections, structured per-paper analysis, and alternate templates such
  as the Chinese daily-brief layout.
- Contains formatting-specific helpers rather than network logic.

### `paper_digest.archive_site`

- Scans historical `output/YYYY-MM-DD/digest.json` files.
- Builds a static archive site with daily cards, feed summaries, feed-specific
  fixed pages, keyword tracking pages, canonical paper detail pages, RSS
  subscription feeds, and a trend overview page.
- Provides client-side filtering for feed, title keyword, and recent date
  windows on the main archive page.
- Normalizes merged-source papers into stable detail pages so feed, topic, and
  RSS views can link through a canonical archive record instead of only the
  current upstream source URL.
- Copies dated Markdown and JSON files into a Pages-friendly output tree.

### `paper_digest.archive_backfill`

- Scans downloaded GitHub Actions digest artifacts from past runs.
- Selects the strongest non-synthetic snapshot for each day and merges it into
  `output/YYYY-MM-DD/`.
- Supports one-time date-window filtering so manual backfills can target only a
  specific slice of historical output.
- Supports dry-run previews so maintainers can inspect which dates would be
  imported or replaced before mutating cached archive history.
- Refreshes `latest.*` and rebuilds the archive site so Pages and RSS can be
  seeded from pre-cache history in one manual pass.

### `paper_digest.network`

- Centralizes bounded retry, timeout, and backoff behavior for upstream source
  fetches.
- Keeps transient network handling consistent across arXiv, Crossref, PubMed,
  Semantic Scholar, and OpenAlex.

### `paper_digest.delivery`

- Builds channel-agnostic notification messages from a digest.
- Applies delivery policies such as `skip_if_empty` and `per_feed`.
- Keeps notification orchestration out of the CLI.

### `paper_digest.email_delivery`

- Sends email notifications through SMTP.
- Only handles email transport and authentication concerns.

### `paper_digest.feishu_delivery`

- Sends structured messages to Feishu incoming webhooks.
- Translates rendered digest text into Feishu post payloads.

### `paper_digest.wecom_delivery`

- Sends markdown notifications to WeCom incoming webhooks.
- Normalizes rendered digest markdown into a WeCom-friendly webhook payload.

### `paper_digest.slack_delivery`

- Sends digest notifications to Slack incoming webhooks.
- Normalizes rendered digest markdown into Slack mrkdwn blocks while keeping
  links and feed-level fan-out compatible with the existing delivery layer.

### `paper_digest.discord_delivery`

- Sends digest notifications to Discord incoming webhooks.
- Normalizes rendered digest markdown into Discord embed payloads while keeping
  fan-out and delivery receipts aligned with the existing webhook adapters.

### `paper_digest.telegram_delivery`

- Sends digest notifications to Telegram chats via the Bot API.
- Normalizes rendered digest markdown into Telegram HTML messages while keeping
  fan-out and delivery receipts aligned with the existing delivery layer.

### `paper_digest.state`

- Persists the set of already-seen papers.
- Prunes old state entries and removes duplicates across runs.

### `paper_digest.service`

- Orchestrates the end-to-end digest generation flow.
- Keeps the CLI thin.
- Provides a stable place for future business rules.
- Supports deferred state persistence so failed deliveries do not drop papers.

### `paper_digest.cli`

- Handles argument parsing and exit codes.
- Converts domain errors into concise user-facing messages.

## Extension Strategy

The next clean extension points are:

1. Add a new source client module such as `openalex_client.py`.
2. Normalize foreign payloads into the existing `Paper` model, or extract a
   source-agnostic protocol if the model starts diverging.
3. Add output adapters for Matrix or other destinations without putting
   transport code into the CLI.
4. Add more analysis providers behind the existing analysis interface rather
   than coupling the service layer to a single LLM vendor.

## Design Constraints

- Runtime dependencies should stay low unless a new dependency clearly improves
  correctness or maintainability.
- Modules that hit the network should be easy to mock in tests.
- Config validation should fail fast and point to the exact broken field.
