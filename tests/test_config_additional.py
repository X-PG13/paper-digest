from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_digest import config as config_module
from paper_digest.config import ConfigError, load_config


class ConfigAdditionalTests(unittest.TestCase):
    def _write_config(self, root: Path, body: str) -> Path:
        config_path = root / "config.toml"
        config_path.write_text(textwrap.dedent(body).strip(), encoding="utf-8")
        return config_path

    def test_load_config_covers_invalid_toml_root_and_loader_error_paths(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            invalid_toml = self._write_config(
                root,
                """
                [app
                """,
            )
            with self.assertRaisesRegex(ConfigError, "invalid TOML"):
                load_config(invalid_toml)

            valid_config = self._write_config(
                root,
                """
                [app]
                timezone = "UTC"

                [[feeds]]
                name = "LLM"
                categories = ["cs.AI"]
                """,
            )
            with patch("paper_digest.config.tomllib.loads", return_value=[]):
                with self.assertRaisesRegex(
                    ConfigError,
                    "config root must be a TOML table",
                ):
                    load_config(valid_config)

            missing_feed_name = self._write_config(
                root,
                """
                [app]
                timezone = "UTC"

                [[feeds]]
                name = "   "
                categories = ["cs.AI"]
                """,
            )
            with self.assertRaisesRegex(ConfigError, "feeds\\[1\\]\\.name"):
                load_config(missing_feed_name)

            email_disabled = self._write_config(
                root,
                """
                [app]
                timezone = "UTC"

                [[feeds]]
                name = "LLM"
                categories = ["cs.AI"]

                [email]
                enabled = false
                """,
            )
            self.assertIsNone(load_config(email_disabled).email)

            email_conflict = self._write_config(
                root,
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
                use_tls = true
                use_starttls = true
                """,
            )
            with self.assertRaisesRegex(ConfigError, "use_tls.*use_starttls"):
                load_config(email_conflict)

            email_without_recipients = self._write_config(
                root,
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
                to_addresses = []
                """,
            )
            with self.assertRaisesRegex(ConfigError, "to_addresses must not be empty"):
                load_config(email_without_recipients)

        with self.assertRaisesRegex(ConfigError, "email must be a TOML table"):
            config_module._load_email("bad")
        with self.assertRaisesRegex(
            ConfigError,
            "deliveries must be an array of tables",
        ):
            config_module._load_deliveries("bad")

    def test_load_config_validates_required_feed_and_delivery_constraints(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            no_feeds = self._write_config(
                root,
                """
                [app]
                timezone = "UTC"
                """,
            )
            with self.assertRaisesRegex(
                ConfigError,
                r"config must define at least one \[\[feeds\]\] entry",
            ):
                load_config(no_feeds)

            arxiv_without_categories = self._write_config(
                root,
                """
                [app]
                timezone = "UTC"

                [[feeds]]
                name = "LLM"
                source = "arxiv"
                categories = []
                """,
            )
            with self.assertRaisesRegex(
                ConfigError,
                r"feeds\[1\]\.categories must not be empty for arxiv",
            ):
                load_config(arxiv_without_categories)

            delivery_conflict = self._write_config(
                root,
                """
                [app]
                timezone = "UTC"

                [[feeds]]
                name = "LLM"
                categories = ["cs.AI"]

                [[deliveries]]
                type = "feishu_webhook"
                webhook_url = "https://open.feishu.cn/example"
                include_actions = false
                action_only = true
                """,
            )
            with self.assertRaisesRegex(
                ConfigError,
                (
                    r"deliveries\[1\]\.action_only cannot be true when "
                    r"deliveries\[1\]\.include_actions is false"
                ),
            ):
                load_config(delivery_conflict)

    def test_scalar_validation_helpers_cover_success_and_error_branches(self) -> None:
        with self.assertRaisesRegex(ConfigError, "items must be an array of strings"):
            config_module._string_list("bad", "items")
        with self.assertRaisesRegex(ConfigError, "contain only strings"):
            config_module._string_list(["ok", 1], "items")
        with self.assertRaisesRegex(ConfigError, "empty strings"):
            config_module._string_list(["ok", "  "], "items")
        self.assertEqual(config_module._string_list([" a ", "b"], "items"), ["a", "b"])

        with self.assertRaisesRegex(ConfigError, "field must be a non-empty string"):
            config_module._required_string(1, "field")
        with self.assertRaisesRegex(ConfigError, "field must be a non-empty string"):
            config_module._required_string("   ", "field")
        self.assertEqual(config_module._required_string(" ok ", "field"), "ok")
        self.assertIsNone(config_module._optional_string(None, "field"))
        self.assertEqual(
            config_module._default_prefixed_string(None, "field", "[Paper Digest]"),
            "[Paper Digest]",
        )

        with self.assertRaisesRegex(ConfigError, "flag must be true or false"):
            config_module._bool("yes", "flag")
        self.assertTrue(config_module._bool(True, "flag"))

        with self.assertRaisesRegex(ConfigError, "count must be a positive integer"):
            config_module._positive_int("bad", "count")
        with self.assertRaisesRegex(ConfigError, "count must be a positive integer"):
            config_module._positive_int(0, "count")
        self.assertEqual(config_module._positive_int(2, "count"), 2)
        self.assertIsNone(config_module._optional_positive_int(None, "count"))

        with self.assertRaisesRegex(
            ConfigError,
            "count must be a non-negative integer",
        ):
            config_module._non_negative_int("bad", "count")
        with self.assertRaisesRegex(
            ConfigError,
            "count must be a non-negative integer",
        ):
            config_module._non_negative_int(-1, "count")
        self.assertEqual(config_module._non_negative_int(0, "count"), 0)
        self.assertIsNone(config_module._optional_non_negative_int(None, "count"))

        with self.assertRaisesRegex(
            ConfigError,
            "delay must be a non-negative number",
        ):
            config_module._non_negative_float("bad", "delay")
        with self.assertRaisesRegex(
            ConfigError,
            "delay must be a non-negative number",
        ):
            config_module._non_negative_float(-1, "delay")
        self.assertEqual(config_module._non_negative_float(1.5, "delay"), 1.5)

        config_path = Path("/tmp/project/config.toml")
        self.assertEqual(
            config_module._resolve_output_dir(config_path, "output"),
            Path("/tmp/project/output").resolve(),
        )
        self.assertEqual(
            config_module._resolve_output_dir(config_path, Path("/var/tmp/output")),
            Path("/var/tmp/output").resolve(),
        )

    def test_enum_and_status_helpers_cover_all_return_paths(self) -> None:
        with self.assertRaisesRegex(ConfigError, "source must be 'arxiv'"):
            config_module._feed_source(1, "source")
        with self.assertRaisesRegex(ConfigError, "source must be 'arxiv'"):
            config_module._feed_source("bad", "source")
        self.assertEqual(config_module._feed_source("pubmed", "source"), "pubmed")
        self.assertEqual(
            config_module._feed_source("semantic_scholar", "source"),
            "semantic_scholar",
        )
        self.assertEqual(config_module._feed_source("openalex", "source"), "openalex")

        with self.assertRaisesRegex(ConfigError, "type must be 'email'"):
            config_module._delivery_type(1, "type")
        with self.assertRaisesRegex(ConfigError, "type must be 'email'"):
            config_module._delivery_type("bad", "type")
        self.assertEqual(
            config_module._delivery_type("wecom_webhook", "type"),
            "wecom_webhook",
        )
        self.assertEqual(
            config_module._delivery_type("slack_webhook", "type"),
            "slack_webhook",
        )
        self.assertEqual(
            config_module._delivery_type("discord_webhook", "type"),
            "discord_webhook",
        )
        self.assertEqual(
            config_module._delivery_type("telegram_bot", "type"),
            "telegram_bot",
        )

        with self.assertRaisesRegex(
            ConfigError,
            "target must be 'digest' or 'per_feed'",
        ):
            config_module._delivery_target(1, "target")
        self.assertEqual(config_module._delivery_target("digest", "target"), "digest")
        self.assertEqual(
            config_module._delivery_target("per_feed", "target"),
            "per_feed",
        )

        with self.assertRaisesRegex(
            ConfigError,
            "focus must be 'digest' or 'separate'",
        ):
            config_module._delivery_focus_target(1, "focus")
        with self.assertRaisesRegex(
            ConfigError,
            "focus must be 'digest' or 'separate'",
        ):
            config_module._delivery_focus_target("bad", "focus")
        self.assertEqual(
            config_module._delivery_focus_target("digest", "focus"),
            "digest",
        )
        self.assertEqual(
            config_module._delivery_focus_target("separate", "focus"),
            "separate",
        )

        with self.assertRaisesRegex(
            ConfigError,
            "action must be 'digest' or 'separate'",
        ):
            config_module._delivery_action_target(1, "action")
        with self.assertRaisesRegex(
            ConfigError,
            "action must be 'digest' or 'separate'",
        ):
            config_module._delivery_action_target("bad", "action")
        self.assertEqual(
            config_module._delivery_action_target("digest", "action"),
            "digest",
        )
        self.assertEqual(
            config_module._delivery_action_target("separate", "action"),
            "separate",
        )

        with self.assertRaisesRegex(ConfigError, "provider must be 'openai'"):
            config_module._analysis_provider(1, "provider")
        with self.assertRaisesRegex(ConfigError, "provider must be 'openai'"):
            config_module._analysis_provider("bad", "provider")
        self.assertEqual(
            config_module._analysis_provider("openai", "provider"),
            "openai",
        )

        with self.assertRaisesRegex(ConfigError, "effort must be one of"):
            config_module._analysis_reasoning_effort(1, "effort")
        with self.assertRaisesRegex(ConfigError, "effort must be one of"):
            config_module._analysis_reasoning_effort("bad", "effort")
        self.assertEqual(
            [
                config_module._analysis_reasoning_effort(item, "effort")
                for item in ["none", "minimal", "low", "medium", "high", "xhigh"]
            ],
            ["none", "minimal", "low", "medium", "high", "xhigh"],
        )

        with self.assertRaisesRegex(ConfigError, "template must be 'default'"):
            config_module._digest_template(1, "template")
        self.assertEqual(
            config_module._digest_template("default", "template"),
            "default",
        )
        self.assertEqual(
            config_module._digest_template("zh_daily_brief", "template"),
            "zh_daily_brief",
        )

        with self.assertRaisesRegex(ConfigError, "sort must be 'relevance'"):
            config_module._sort_mode(1, "sort")
        with self.assertRaisesRegex(ConfigError, "sort must be 'relevance'"):
            config_module._sort_mode("manual", "sort")
        self.assertEqual(config_module._sort_mode("relevance", "sort"), "relevance")
        self.assertEqual(
            config_module._sort_mode("published_at", "sort"),
            "published_at",
        )
        self.assertEqual(config_module._sort_mode("hybrid", "sort"), "hybrid")
        self.assertIsNone(config_module._optional_sort_mode(None, "sort"))

    def test_feedback_and_reason_helpers_validate_and_normalize_lists(self) -> None:
        with self.assertRaisesRegex(ConfigError, "focus_statuses must contain only"):
            config_module._focus_feedback_status_value("reading", "focus_statuses")
        self.assertEqual(
            config_module._focus_feedback_status_value("star", "focus_statuses"),
            "star",
        )
        self.assertEqual(
            config_module._focus_feedback_status_value(
                "follow_up",
                "focus_statuses",
            ),
            "follow_up",
        )

        with self.assertRaisesRegex(ConfigError, "focus_reasons must contain only"):
            config_module._focus_reason_value("bad", "focus_reasons")
        self.assertEqual(
            [
                config_module._focus_reason_value(item, "focus_reasons")
                for item in [
                    "new_starred",
                    "follow_up_resurfaced",
                    "starred_momentum",
                ]
            ],
            ["new_starred", "follow_up_resurfaced", "starred_momentum"],
        )

        with self.assertRaisesRegex(ConfigError, "action_statuses must contain only"):
            config_module._action_feedback_status_value("done", "action_statuses")
        self.assertEqual(
            [
                config_module._action_feedback_status_value(item, "action_statuses")
                for item in ["star", "follow_up", "reading"]
            ],
            ["star", "follow_up", "reading"],
        )

        with self.assertRaisesRegex(ConfigError, "action_reasons must contain only"):
            config_module._action_reason_value("bad", "action_reasons")
        self.assertEqual(
            [
                config_module._action_reason_value(item, "action_reasons")
                for item in [
                    "overdue_1d",
                    "overdue_3d",
                    "due_soon",
                    "recurring_review",
                    "recurring_due",
                    "next_action_pending",
                ]
            ],
            [
                "overdue_1d",
                "overdue_3d",
                "due_soon",
                "recurring_review",
                "recurring_due",
                "next_action_pending",
            ],
        )

        self.assertEqual(
            config_module._focus_status_list(
                ["star", "follow_up"],
                "focus_statuses",
            ),
            ["star", "follow_up"],
        )
        self.assertEqual(
            config_module._focus_reason_list(
                ["new_starred", "starred_momentum"],
                "focus_reasons",
            ),
            ["new_starred", "starred_momentum"],
        )
        self.assertEqual(
            config_module._action_status_list(
                ["star", "reading"],
                "action_statuses",
            ),
            ["star", "reading"],
        )
        self.assertEqual(
            config_module._action_reason_list(
                ["overdue_7d", "recurring_due"],
                "action_reasons",
            ),
            ["overdue_7d", "recurring_due"],
        )
