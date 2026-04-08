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
        self.assertEqual(config.feeds[0].name, "LLM")
        self.assertTrue(config.state.enabled)

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
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(len(config.deliveries), 2)
        self.assertEqual(config.deliveries[0].target, "per_feed")
        self.assertEqual(config.deliveries[1].target, "digest")

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
