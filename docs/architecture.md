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

### `paper_digest.digest`

- Applies filtering rules such as lookback windows and keyword matching.
- Renders digest output for JSON and Markdown.
- Contains formatting-specific helpers rather than network logic.

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

## Design Constraints

- Runtime dependencies should stay low unless a new dependency clearly improves
  correctness or maintainability.
- Modules that hit the network should be easy to mock in tests.
- Config validation should fail fast and point to the exact broken field.
