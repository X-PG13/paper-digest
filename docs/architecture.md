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

### `paper_digest.analysis`

- Selects which papers should be enriched in a given run.
- Applies structured paper analysis and builds top-of-digest highlights plus
  per-feed key points.
- Also supports rule-based briefing generation when a richer digest template is
  requested without enabling any LLM provider.
- Keeps analysis policy out of the fetch and delivery layers.

### `paper_digest.openai_analysis`

- Calls the OpenAI Responses API for structured per-paper analysis.
- Converts raw responses into the shared `PaperAnalysis` model.

### `paper_digest.digest`

- Applies filtering rules such as lookback windows and keyword matching.
- Renders digest output for JSON and Markdown, including optional highlights,
  structured per-paper analysis, and alternate templates such as the Chinese
  daily-brief layout.
- Contains formatting-specific helpers rather than network logic.

### `paper_digest.archive_site`

- Scans historical `output/YYYY-MM-DD/digest.json` files.
- Builds a static archive site with daily cards, feed summaries, feed-specific
  fixed pages, keyword tracking pages, and a trend overview page.
- Provides client-side filtering for feed, title keyword, and recent date
  windows on the main archive page.
- Copies dated Markdown and JSON files into a Pages-friendly output tree.

### `paper_digest.network`

- Centralizes bounded retry, timeout, and backoff behavior for upstream source
  fetches.
- Keeps transient network handling consistent across arXiv and Crossref.

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

1. Add a new source client module such as `pubmed_client.py`.
2. Normalize foreign payloads into the existing `Paper` model, or extract a
   source-agnostic protocol if the model starts diverging.
3. Add output adapters for Slack, WeCom, or other destinations without putting
   transport code into the CLI.
4. Add more analysis providers behind the existing analysis interface rather
   than coupling the service layer to a single LLM vendor.

## Design Constraints

- Runtime dependencies should stay low unless a new dependency clearly improves
  correctness or maintainability.
- Modules that hit the network should be easy to mock in tests.
- Config validation should fail fast and point to the exact broken field.
