from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

import paper_digest.discord_delivery as discord_delivery
import paper_digest.email_delivery as email_delivery
import paper_digest.feishu_delivery as feishu_delivery
import paper_digest.slack_delivery as slack_delivery
import paper_digest.telegram_delivery as telegram_delivery
import paper_digest.wecom_delivery as wecom_delivery
from paper_digest.arxiv_client import Paper
from paper_digest.config import (
    DiscordWebhookConfig,
    EmailConfig,
    FeishuWebhookConfig,
    SlackWebhookConfig,
    TelegramBotConfig,
    WeComWebhookConfig,
)
from paper_digest.digest import DigestRun, FeedDigest


class FakeSMTP:
    instances: list[FakeSMTP] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.login_args: tuple[str, str] | None = None
        self.message = None
        FakeSMTP.instances.append(self)

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message: object) -> None:
        self.message = message


class SlackHelperTests(unittest.TestCase):
    @patch("paper_digest.slack_delivery.urlopen", side_effect=OSError("network down"))
    def test_send_slack_message_wraps_network_errors(self, _mock_urlopen) -> None:
        config = SlackWebhookConfig(
            webhook_url="https://hooks.slack.com/services/T000/B000/secret",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaisesRegex(
            slack_delivery.SlackDeliveryError,
            "failed to send Slack webhook notification: network down",
        ):
            slack_delivery.send_slack_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )

    def test_slack_markdown_helpers_cover_chunking_and_truncation(self) -> None:
        normalized = slack_delivery._normalize_markdown(
            "Title",
            "## Heading\n### Tiny\n- Bullet\nBody [link](https://example.com)\n",
        )
        self.assertIn("*Heading*", normalized)
        self.assertIn("*Tiny*", normalized)
        self.assertIn("• Bullet", normalized)
        self.assertIn("<https://example.com|link>", normalized)

        branch_chunks = slack_delivery._chunk_text(
            "short line\n" + ("x" * (slack_delivery._MAX_SECTION_TEXT + 10))
        )
        self.assertEqual(len(branch_chunks), 2)

        long_line = "x" * (slack_delivery._MAX_SECTION_TEXT + 10)
        chunks = slack_delivery._chunk_text(
            "\n".join([long_line] * (slack_delivery._MAX_BLOCKS + 2))
        )
        self.assertEqual(len(chunks), slack_delivery._MAX_BLOCKS)
        self.assertEqual(chunks[-1], "_Message truncated for Slack block limits._")


class DiscordHelperTests(unittest.TestCase):
    @patch("paper_digest.discord_delivery.urlopen", side_effect=OSError("network down"))
    def test_send_discord_message_wraps_network_errors(self, _mock_urlopen) -> None:
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/1/secret",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaisesRegex(
            discord_delivery.DiscordDeliveryError,
            "failed to send Discord webhook notification: network down",
        ):
            discord_delivery.send_discord_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )

    def test_discord_helpers_cover_normalization_and_validation(self) -> None:
        normalized = discord_delivery._normalize_markdown(
            "## Heading\n### Tiny\n  - Nested bullet\n   - Deep bullet\n"
            "1. [Link](https://example.com)\n"
        )
        self.assertIn("**Heading**", normalized)
        self.assertIn("**Tiny**", normalized)
        self.assertIn("• Nested bullet", normalized)
        self.assertIn("• Deep bullet", normalized)
        self.assertIn("1. **Link**", normalized)
        self.assertIn("<https://example.com>", normalized)

        truncated = discord_delivery._truncate_description(
            "x" * (discord_delivery._MAX_EMBED_TOTAL + 20)
        )
        self.assertIn("_Message truncated for Discord embed limits._", truncated)

        branch_chunks = discord_delivery._chunk_text(
            "short line\n" + ("x" * (discord_delivery._MAX_EMBED_DESCRIPTION + 10))
        )
        self.assertEqual(len(branch_chunks), 2)
        self.assertEqual(
            discord_delivery._chunk_text(""),
            ["_No digest content available._"],
        )
        self.assertEqual(
            len(
                discord_delivery._chunk_text(
                    "x" * (discord_delivery._MAX_EMBED_DESCRIPTION + 10)
                )
            ),
            2,
        )

        with self.assertRaisesRegex(
            discord_delivery.DiscordDeliveryError,
            "received malformed JSON",
        ):
            discord_delivery._validate_response(b"not json")
        with self.assertRaisesRegex(
            discord_delivery.DiscordDeliveryError,
            "payload is invalid",
        ):
            discord_delivery._validate_response(b"[]")


class TelegramHelperTests(unittest.TestCase):
    @patch(
        "paper_digest.telegram_delivery.urlopen",
        side_effect=OSError("network down"),
    )
    def test_send_telegram_message_wraps_network_errors(self, _mock_urlopen) -> None:
        config = TelegramBotConfig(
            bot_token="123456:token",
            chat_id="-1001234567890",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaisesRegex(
            telegram_delivery.TelegramDeliveryError,
            "failed to send Telegram notification: network down",
        ):
            telegram_delivery.send_telegram_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )

    def test_telegram_helpers_cover_html_chunking_and_validation(self) -> None:
        normalized = telegram_delivery._normalize_markdown(
            "Title <x>",
            "## Heading\n### Tiny\n  - Nested bullet\n   - Deep bullet\n"
            "1. [Link](https://example.com?a=1&b=2)\n"
            "prefix [Inline](https://example.com/inline) suffix\n",
        )
        self.assertIn("<b>Title &lt;x&gt;</b>", normalized)
        self.assertIn("<b>Heading</b>", normalized)
        self.assertIn("<b>Tiny</b>", normalized)
        self.assertIn("• Nested bullet", normalized)
        self.assertIn("• Deep bullet", normalized)
        self.assertIn(
            '1. <a href="https://example.com?a=1&amp;b=2">Link</a>',
            normalized,
        )
        self.assertIn(
            'prefix <a href="https://example.com/inline">Inline</a> suffix',
            normalized,
        )
        self.assertEqual(
            telegram_delivery._convert_links("[Only](https://example.com/only)"),
            '<a href="https://example.com/only">Only</a>',
        )

        branch_chunks = telegram_delivery._chunk_text(
            "short line\n" + ("x" * (telegram_delivery._MAX_MESSAGE_TEXT + 10))
        )
        self.assertEqual(len(branch_chunks), 2)
        self.assertEqual(
            telegram_delivery._chunk_text(""),
            ["<i>No digest content available.</i>"],
        )
        self.assertEqual(
            len(
                telegram_delivery._chunk_text(
                    "x" * (telegram_delivery._MAX_MESSAGE_TEXT + 10)
                )
            ),
            2,
        )

        with self.assertRaisesRegex(
            telegram_delivery.TelegramDeliveryError,
            "received malformed JSON",
        ):
            telegram_delivery._validate_response(b"not json")
        with self.assertRaisesRegex(
            telegram_delivery.TelegramDeliveryError,
            "payload is invalid",
        ):
            telegram_delivery._validate_response(b"[]")


class WeComAndFeishuHelperTests(unittest.TestCase):
    @patch("paper_digest.feishu_delivery.urlopen", side_effect=OSError("network down"))
    def test_send_feishu_message_wraps_network_errors(self, _mock_urlopen) -> None:
        config = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaisesRegex(
            feishu_delivery.FeishuDeliveryError,
            "failed to send Feishu webhook notification: network down",
        ):
            feishu_delivery.send_feishu_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )

    @patch("paper_digest.wecom_delivery.urlopen", side_effect=OSError("network down"))
    def test_send_wecom_message_wraps_network_errors(self, _mock_urlopen) -> None:
        config = WeComWebhookConfig(
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaisesRegex(
            wecom_delivery.WeComDeliveryError,
            "failed to send WeCom webhook notification: network down",
        ):
            wecom_delivery.send_wecom_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )

    def test_wecom_helpers_cover_truncation_and_validation(self) -> None:
        normalized = wecom_delivery._normalize_markdown(
            "Title",
            "1. [Link](https://example.com)\n   - Nested bullet\n",
        )
        self.assertIn("1. Link", normalized)
        self.assertIn("> https://example.com", normalized)
        self.assertIn("- Nested bullet", normalized)

        truncated = wecom_delivery._truncate_markdown("中" * 3000)
        self.assertTrue(truncated.endswith("> 内容过长，已截断。"))
        suffix_bytes = len("\n\n> 内容过长，已截断。".encode())
        with patch.object(wecom_delivery, "_MAX_MARKDOWN_BYTES", suffix_bytes + 2):
            self.assertEqual(
                wecom_delivery._truncate_markdown("中" * 20),
                "> 内容过长，已截断。",
            )

        with self.assertRaisesRegex(
            wecom_delivery.WeComDeliveryError,
            "received malformed JSON",
        ):
            wecom_delivery._validate_response(b"not json")
        with self.assertRaisesRegex(
            wecom_delivery.WeComDeliveryError,
            "payload is invalid",
        ):
            wecom_delivery._validate_response(b"[]")

    def test_feishu_helpers_cover_rows_and_validation(self) -> None:
        rows = feishu_delivery._build_post_content(
            "# Heading\n## Subheading\n- Bullet\n1. [Link](https://example.com)\n"
        )
        self.assertEqual(rows[0][0]["text"], "Heading")
        self.assertEqual(rows[1][0]["text"], "Subheading")
        self.assertEqual(rows[2][0]["text"], "Bullet")
        self.assertEqual(rows[3][1]["href"], "https://example.com")

        with self.assertRaisesRegex(
            feishu_delivery.FeishuDeliveryError,
            "received malformed JSON",
        ):
            feishu_delivery._validate_response(b"not json")
        with self.assertRaisesRegex(
            feishu_delivery.FeishuDeliveryError,
            "payload is invalid",
        ):
            feishu_delivery._validate_response(b"[]")
        feishu_delivery._validate_response(b'{"StatusCode":0,"StatusMessage":"ok"}')


class EmailHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeSMTP.instances.clear()

    def test_send_digest_email_uses_ssl_and_builds_subject(self) -> None:
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=465,
            username="bot@example.com",
            password_env="SMTP_PASSWORD",
            from_address="bot@example.com",
            to_addresses=["reader@example.com"],
            use_tls=True,
            use_starttls=False,
            subject_prefix="[Digest]",
            skip_if_empty=True,
        )
        paper = Paper(
            title="Agent systems",
            summary="Summary",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="https://arxiv.org/abs/1",
            abstract_url="https://arxiv.org/abs/1",
            pdf_url=None,
            published_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        )
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[paper])],
        )

        with patch("paper_digest.email_delivery.smtplib.SMTP_SSL", FakeSMTP):
            with patch.dict(os.environ, {"SMTP_PASSWORD": "secret"}, clear=False):
                email_delivery.send_digest_email(config, digest)

        server = FakeSMTP.instances[0]
        assert server.message is not None
        self.assertEqual(server.login_args, ("bot@example.com", "secret"))
        self.assertEqual(server.message["Subject"], "[Digest] 2026-04-08 | LLM=1")
        self.assertIn("# Daily Paper Digest", server.message.get_content())
