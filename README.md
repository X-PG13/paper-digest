# Paper Digest

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Paper Digest is a small but production-minded Python project for pulling the
latest arXiv papers every day and turning them into a readable research digest.

The current scope is intentionally narrow:

- Fetch the newest arXiv submissions by category.
- Apply include and exclude keyword filters on title and abstract.
- Generate machine-readable `JSON` and human-readable `Markdown`.
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
- `categories`: arXiv categories such as `cs.AI`, `cs.CL`, or `cs.CV`.
- `keywords`: Keep a paper when any keyword matches title or abstract.
- `exclude_keywords`: Drop a paper when any excluded keyword matches.
- `max_results`: Number of newest candidates fetched before local filtering.
- `max_items`: Maximum number of papers emitted for that feed.

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

On macOS or Linux you can run the digest every morning with `cron`:

```cron
0 8 * * * /absolute/path/to/.venv/bin/python -m paper_digest --config /absolute/path/to/config.toml
```

## Roadmap

- Add more literature sources such as PubMed, Crossref, and Semantic Scholar.
- Support output adapters for email, Slack, Feishu, and WeCom.
- Add deduplication and persistent history across days.
- Support feed-level templates or LLM-generated summaries.

## Status

The project is usable today for daily arXiv monitoring, but it is still early.
Expect API and config changes while the repository matures.
