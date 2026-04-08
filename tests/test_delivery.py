from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from paper_digest.arxiv_client import Paper
from paper_digest.config import AppConfig, EmailConfig, FeishuWebhookConfig, StateConfig
from paper_digest.delivery import (
    build_notification_messages,
    send_configured_deliveries,
)
from paper_digest.digest import DigestRun, FeedDigest


def build_digest() -> DigestRun:
    return DigestRun(
        generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
        timezone="UTC",
        lookback_hours=24,
        highlights=[
            "LLM：Agent systems：适合直接放进中文日报头部的结论。",
            "Vision：Vision paper：这一条不该出现在 LLM 单独通知里。",
        ],
        feeds=[
            FeedDigest(
                name="LLM",
                papers=[
                    Paper(
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
                ],
                key_points=["Agent systems：更适合作为今日重点的摘要。"],
            ),
            FeedDigest(name="Vision", papers=[]),
        ],
        template="zh_daily_brief",
    )


class DeliveryTests(unittest.TestCase):
    def test_build_notification_messages_splits_per_feed(self) -> None:
        delivery = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=465,
            username=None,
            password_env=None,
            from_address="bot@example.com",
            to_addresses=["reader@example.com"],
            use_tls=True,
            use_starttls=False,
            subject_prefix="[Digest]",
            skip_if_empty=True,
            target="per_feed",
        )

        messages = build_notification_messages(delivery, build_digest())

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].feed_name, "LLM")
        self.assertIn("[Digest] 2026-04-08 | LLM=1", messages[0].title)
        self.assertIn("# 每日论文简报", messages[0].body)
        self.assertIn("### 今日重点", messages[0].body)
        self.assertIn("Agent systems：更适合作为今日重点的摘要。", messages[0].body)
        self.assertIn(
            "LLM：Agent systems：适合直接放进中文日报头部的结论。", messages[0].body
        )
        self.assertNotIn("Vision paper", messages[0].body)

    def test_build_notification_messages_skips_empty_digest(self) -> None:
        delivery = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
            target="digest",
        )
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[])],
        )

        messages = build_notification_messages(delivery, digest)

        self.assertEqual(messages, [])

    @patch("paper_digest.delivery.send_feishu_message")
    @patch("paper_digest.delivery.send_email_message")
    def test_send_configured_deliveries_uses_legacy_email_and_feishu(
        self,
        mock_send_email_message,
        mock_send_feishu_message,
    ) -> None:
        digest = build_digest()
        config = AppConfig(
            timezone="UTC",
            lookback_hours=24,
            output_dir=Path("output"),
            request_delay_seconds=0.0,
            feeds=[],
            state=StateConfig(
                enabled=True,
                path=Path("state.json"),
                retention_days=90,
            ),
            deliveries=[
                FeishuWebhookConfig(
                    webhook_url="https://open.feishu.cn/example",
                    title_prefix="[Robot]",
                    skip_if_empty=True,
                    target="per_feed",
                )
            ],
            email=EmailConfig(
                smtp_host="smtp.example.com",
                smtp_port=465,
                username=None,
                password_env=None,
                from_address="bot@example.com",
                to_addresses=["reader@example.com"],
                use_tls=True,
                use_starttls=False,
                subject_prefix="[Digest]",
                skip_if_empty=True,
            ),
        )

        receipts = send_configured_deliveries(config, digest)

        self.assertEqual(mock_send_email_message.call_count, 1)
        self.assertEqual(mock_send_feishu_message.call_count, 1)
        self.assertEqual(len(receipts), 2)
