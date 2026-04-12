from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.config import ConfigError, load_config


class LoadConfigTests(unittest.TestCase):
    def test_load_config_resolves_output_relative_to_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "configs" / "digest.toml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "Asia/Shanghai"
                    lookback_hours = 48
                    output_dir = "../artifacts"
                    request_delay_seconds = 1.5
                    request_timeout_seconds = 60
                    fetch_retry_attempts = 4
                    fetch_retry_backoff_seconds = 6.5

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]
                    keywords = ["agent"]
                    exclude_keywords = ["survey"]
                    max_results = 50
                    max_items = 5
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.timezone, "Asia/Shanghai")
        self.assertEqual(config.lookback_hours, 48)
        self.assertEqual(
            config.output_dir,
            (config_path.parent / "../artifacts").resolve(),
        )
        self.assertEqual(config.request_delay_seconds, 1.5)
        self.assertEqual(config.request_timeout_seconds, 60)
        self.assertEqual(config.fetch_retry_attempts, 4)
        self.assertEqual(config.fetch_retry_backoff_seconds, 6.5)
        self.assertIsNone(config.openalex_api_key_env)
        self.assertEqual(config.feeds[0].name, "LLM")
        self.assertTrue(config.state.enabled)

    def test_load_config_reads_optional_openalex_api_key_env(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"
                    openalex_api_key_env = "OPENALEX_API_KEY"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.openalex_api_key_env, "OPENALEX_API_KEY")

    def test_invalid_timezone_raises_config_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "Mars/Olympus_Mons"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_invalid_fetch_retry_attempts_raises_config_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"
                    fetch_retry_attempts = 0

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_load_config_reads_email_settings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [email]
                    enabled = true
                    smtp_host = "smtp.example.com"
                    smtp_port = 587
                    username = "bot@example.com"
                    password_env = "SMTP_PASSWORD"
                    from_address = "bot@example.com"
                    to_addresses = ["reader@example.com"]
                    use_tls = false
                    use_starttls = true
                    subject_prefix = "[Digest]"
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertIsNotNone(config.email)
        assert config.email is not None
        self.assertEqual(config.email.smtp_host, "smtp.example.com")
        self.assertEqual(config.email.smtp_port, 587)
        self.assertEqual(config.email.username, "bot@example.com")
        self.assertEqual(config.email.password_env, "SMTP_PASSWORD")
        self.assertEqual(config.email.to_addresses, ["reader@example.com"])
        self.assertFalse(config.email.use_tls)
        self.assertTrue(config.email.use_starttls)
        self.assertEqual(config.email.target, "digest")

    def test_load_config_reads_delivery_settings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [[deliveries]]
                    type = "email"
                    smtp_host = "smtp.example.com"
                    smtp_port = 465
                    from_address = "bot@example.com"
                    to_addresses = ["reader@example.com"]
                    use_tls = true
                    subject_prefix = "[Digest]"
                    skip_if_empty = true
                    target = "per_feed"

                    [[deliveries]]
                    type = "feishu_webhook"
                    webhook_url = "https://open.feishu.cn/example"
                    title_prefix = "[Robot]"
                    skip_if_empty = true
                    target = "digest"
                    include_focus = false
                    focus_target = "digest"
                    focus_statuses = ["star"]
                    focus_reasons = ["new_starred"]
                    focus_max_items = 2
                    include_actions = true
                    action_target = "separate"

                    [[deliveries]]
                    type = "wecom_webhook"
                    webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc"
                    title_prefix = "[WeCom]"
                    skip_if_empty = false
                    target = "digest"
                    focus_target = "separate"
                    action_only = true

                    [[deliveries]]
                    type = "slack_webhook"
                    webhook_url = "https://hooks.slack.com/services/T000/B000/secret"
                    title_prefix = "[Slack]"
                    skip_if_empty = true
                    target = "per_feed"

                    [[deliveries]]
                    type = "discord_webhook"
                    webhook_url = "https://discord.com/api/webhooks/123456789012345678/secret"
                    title_prefix = "[Discord]"
                    skip_if_empty = false
                    target = "digest"

                    [[deliveries]]
                    type = "telegram_bot"
                    bot_token = "123456:telegram-token"
                    chat_id = "-1001234567890"
                    title_prefix = "[Telegram]"
                    skip_if_empty = true
                    target = "per_feed"
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(len(config.deliveries), 6)
        self.assertEqual(config.deliveries[0].target, "per_feed")
        self.assertEqual(config.deliveries[1].target, "digest")
        self.assertEqual(config.deliveries[2].target, "digest")
        self.assertEqual(config.deliveries[3].target, "per_feed")
        self.assertEqual(config.deliveries[4].target, "digest")
        self.assertEqual(config.deliveries[5].target, "per_feed")
        self.assertFalse(config.deliveries[1].include_focus)
        self.assertEqual(config.deliveries[1].focus_statuses, ["star"])
        self.assertEqual(config.deliveries[1].focus_reasons, ["new_starred"])
        self.assertEqual(config.deliveries[1].focus_max_items, 2)
        self.assertTrue(config.deliveries[1].include_actions)
        self.assertEqual(config.deliveries[1].action_target, "separate")
        self.assertEqual(config.deliveries[2].focus_target, "separate")
        self.assertTrue(config.deliveries[2].action_only)

    def test_load_config_reads_analysis_settings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [digest]
                    template = "zh_daily_brief"
                    top_highlights = 4
                    feed_key_points = 2

                    [analysis]
                    enabled = true
                    provider = "openai"
                    model = "gpt-5-mini"
                    api_key_env = "OPENAI_API_KEY"
                    base_url = "https://api.openai.com/v1/responses"
                    timeout_seconds = 45
                    max_papers = 8
                    max_output_tokens = 500
                    language = "Chinese"
                    reasoning_effort = "low"
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        assert config.analysis is not None
        self.assertEqual(config.digest.template, "zh_daily_brief")
        self.assertEqual(config.digest.top_highlights, 4)
        self.assertEqual(config.digest.feed_key_points, 2)
        self.assertEqual(config.analysis.model, "gpt-5-mini")
        self.assertEqual(config.analysis.max_papers, 8)
        self.assertEqual(config.analysis.language, "Chinese")
        self.assertEqual(config.analysis.reasoning_effort, "low")

    def test_load_config_reads_ranking_settings_and_feed_sort_override(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [ranking]
                    sort_by = "published_at"
                    title_match_weight = 55
                    multi_source_weight = 14

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]
                    sort_by = "relevance"
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.ranking.sort_by, "published_at")
        self.assertEqual(config.ranking.weights.title_match_weight, 55)
        self.assertEqual(config.ranking.weights.multi_source_weight, 14)
        self.assertEqual(config.feeds[0].sort_by, "relevance")

    def test_load_config_reads_digest_settings_from_legacy_analysis_section(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [analysis]
                    enabled = false
                    top_highlights = 5
                    feed_key_points = 2
                    template = "zh_daily_brief"
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertIsNone(config.analysis)
        self.assertEqual(config.digest.template, "zh_daily_brief")
        self.assertEqual(config.digest.top_highlights, 5)
        self.assertEqual(config.digest.feed_key_points, 2)

    def test_analysis_reasoning_effort_must_be_valid(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [analysis]
                    enabled = true
                    reasoning_effort = "extreme"
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_digest_template_must_be_valid(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [digest]
                    template = "newsletter"
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_ranking_sort_mode_must_be_valid(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [ranking]
                    sort_by = "manual"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_delivery_target_must_be_valid(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [[deliveries]]
                    type = "feishu_webhook"
                    webhook_url = "https://open.feishu.cn/example"
                    target = "unknown"
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_load_config_reads_state_settings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [state]
                    enabled = true
                    path = ".cache/custom-state.json"
                    retention_days = 30
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertTrue(config.state.enabled)
        self.assertEqual(config.state.retention_days, 30)
        self.assertEqual(
            config.state.path,
            (config_path.parent / ".cache/custom-state.json").resolve(),
        )

    def test_load_config_reads_feedback_settings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [feedback]
                    enabled = true
                    path = ".cache/feedback.json"
                    star_boost = 90
                    follow_up_boost = 40
                    reading_boost = 20
                    done_penalty = 25
                    ignore_penalty = 150
                    hide_ignored = false
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertTrue(config.feedback.enabled)
        self.assertEqual(
            config.feedback.path,
            (config_path.parent / ".cache/feedback.json").resolve(),
        )
        self.assertEqual(config.feedback.star_boost, 90)
        self.assertEqual(config.feedback.follow_up_boost, 40)
        self.assertEqual(config.feedback.reading_boost, 20)
        self.assertEqual(config.feedback.done_penalty, 25)
        self.assertEqual(config.feedback.ignore_penalty, 150)
        self.assertFalse(config.feedback.hide_ignored)

    def test_email_auth_requires_username_and_password_env_together(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [email]
                    enabled = true
                    smtp_host = "smtp.example.com"
                    from_address = "bot@example.com"
                    to_addresses = ["reader@example.com"]
                    username = "bot@example.com"
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_crossref_feed_requires_queries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "Crossref"
                    source = "crossref"
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_pubmed_feed_requires_queries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "PubMed"
                    source = "pubmed"
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_semantic_scholar_feed_requires_queries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "Semantic Scholar AI"
                    source = "semantic_scholar"
                    keywords = ["agent"]
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_openalex_feed_requires_queries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "OpenAlex AI"
                    source = "openalex"
                    keywords = ["agent"]
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_load_config_accepts_pubmed_feed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "PubMed AI"
                    source = "pubmed"
                    queries = ["agent systems", "clinical benchmark"]
                    types = ["Journal Article", "Review"]
                    keywords = ["agent"]
                    max_results = 40
                    max_items = 8
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.feeds[0].source, "pubmed")
        self.assertEqual(
            config.feeds[0].queries,
            ["agent systems", "clinical benchmark"],
        )
        self.assertEqual(config.feeds[0].types, ["Journal Article", "Review"])

    def test_load_config_accepts_semantic_scholar_feed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "Semantic Scholar AI"
                    source = "semantic_scholar"
                    queries = ["large language model", "agent systems"]
                    types = ["Review"]
                    keywords = ["agent"]
                    exclude_keywords = ["survey"]
                    max_results = 25
                    max_items = 5
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.feeds[0].source, "semantic_scholar")
        self.assertEqual(
            config.feeds[0].queries,
            ["large language model", "agent systems"],
        )
        self.assertEqual(config.feeds[0].types, ["Review"])

    def test_load_config_accepts_openalex_feed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"
                    openalex_api_key_env = "OPENALEX_API_KEY"

                    [[feeds]]
                    name = "OpenAlex AI"
                    source = "openalex"
                    queries = ["large language model", "agent systems"]
                    types = ["article", "preprint"]
                    keywords = ["agent"]
                    exclude_keywords = ["survey"]
                    max_results = 25
                    max_items = 5
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.openalex_api_key_env, "OPENALEX_API_KEY")
        self.assertEqual(config.feeds[0].source, "openalex")
        self.assertEqual(
            config.feeds[0].queries,
            ["large language model", "agent systems"],
        )
        self.assertEqual(config.feeds[0].types, ["article", "preprint"])

    def test_load_config_reads_notify_settings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "UTC"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]

                    [notify]
                    feedback_only = true
                    include_new_starred = false
                    include_follow_up_resurfaced = true
                    include_starred_momentum = false
                    max_focus_items = 7
                    max_action_items = 4
                    action_overdue_only = true
                    action_due_within_days = 2
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertTrue(config.notify.feedback_only)
        self.assertFalse(config.notify.include_new_starred)
        self.assertTrue(config.notify.include_follow_up_resurfaced)
        self.assertFalse(config.notify.include_starred_momentum)
        self.assertEqual(config.notify.max_focus_items, 7)
        self.assertEqual(config.notify.max_action_items, 4)
        self.assertTrue(config.notify.action_overdue_only)
        self.assertEqual(config.notify.action_due_within_days, 2)
