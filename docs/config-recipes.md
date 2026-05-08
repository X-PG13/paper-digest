# Config Recipes

These recipes are small starting points meant to be copied into `config.toml`
and then expanded. Use [`config.example.toml`](../config.example.toml) for the
fully commented field reference.

## 1. Local Smoke Test

Use this when you want the shortest path to a local run with no external
credentials and no delivery channels.

```toml
[app]
timezone = "UTC"
lookback_hours = 24
output_dir = "output"
request_delay_seconds = 3

[state]
enabled = true
path = ".paper-digest-state/state.json"
retention_days = 90

[feedback]
enabled = true
path = ".paper-digest-state/feedback.json"

[[feeds]]
name = "LLM"
source = "arxiv"
categories = ["cs.AI", "cs.CL"]
keywords = ["agent", "reasoning"]
exclude_keywords = ["survey"]
max_results = 50
max_items = 10
```

## 2. GitHub Actions Scheduled Run

Use this when the repository secret `PAPER_DIGEST_CONFIG_TOML` will hold the
full config and the workflow should preserve local state through the cache.

```toml
[app]
timezone = "Asia/Shanghai"
lookback_hours = 24
output_dir = "output"
request_delay_seconds = 3
request_timeout_seconds = 60
fetch_retry_attempts = 4
fetch_retry_backoff_seconds = 10

[state]
enabled = true
path = ".paper-digest-state/state.json"
retention_days = 90

[feedback]
enabled = true
path = ".paper-digest-state/feedback.json"

[[feeds]]
name = "LLM"
source = "arxiv"
categories = ["cs.AI", "cs.CL", "cs.LG"]
keywords = ["agent", "benchmark", "alignment"]
exclude_keywords = ["survey"]
max_results = 100
max_items = 15
```

## 3. Feishu LM/arXiv Morning Digest

Use [`examples/feishu-lm-arxiv.toml`](../examples/feishu-lm-arxiv.toml) when
you want the scheduled GitHub workflow to send one Chinese Feishu message each
morning for new LM papers plus agent runtime security papers from arXiv.

Operational steps:

1. Replace the placeholder Feishu webhook URL.
2. Store the full TOML content in the `PAPER_DIGEST_CONFIG_TOML` repository
   secret.
3. Trigger `Daily Digest` manually once on `main`.
4. Let the default workflow schedule deliver at about `09:07 Asia/Shanghai`.

The example keeps two feed sections:

- `LM`: language-model papers from `cs.CL`, `cs.AI`, and `cs.LG`.
- `Agent Runtime Security`: agent runtime, tool-use, sandboxing, prompt
  injection, privilege-escalation, and policy-enforcement papers from `cs.AI`,
  `cs.CL`, `cs.CR`, and `cs.SE`.

Keep `target = "digest"`, `focus_target = "digest"`, and
`action_target = "digest"` when you want one combined Feishu message instead
of separate per-feed, Focus, or Action messages.

## 4. Chinese Daily Brief Without LLM Calls

Use this when you want the Chinese briefing layout but do not want to spend API
tokens yet.

```toml
[digest]
template = "zh_daily_brief"
top_highlights = 3
feed_key_points = 3

[analysis]
enabled = false
provider = "openai"
model = "gpt-5-mini"
api_key_env = "OPENAI_API_KEY"
base_url = "https://api.openai.com/v1/responses"
timeout_seconds = 60
max_papers = 8
max_output_tokens = 600
language = "Chinese"
reasoning_effort = "minimal"
```

## 5. Action-Oriented Reminder Channel

Use this when one delivery should only push due work instead of the whole
digest.

```toml
[notify]
feedback_only = false
max_action_items = 5
action_due_within_days = 7

[[deliveries]]
type = "feishu_webhook"
webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/your-token"
title_prefix = "[Paper Digest]"
skip_if_empty = true
target = "digest"
include_focus = false
include_actions = true
action_target = "separate"
action_only = true
action_statuses = ["star", "follow_up", "reading"]
action_reasons = ["due_soon", "overdue", "overdue_7d", "recurring_due"]
action_max_items = 5
action_overdue_only = false
action_due_within_days = 7
```

## Notes

- Keep `config.example.toml` as the source of truth for field-level comments.
- Keep these recipes small; they are for "start here" paths, not exhaustive
  configuration showcases.
- When you add a new major configuration surface, update both this file and
  `config.example.toml`.
