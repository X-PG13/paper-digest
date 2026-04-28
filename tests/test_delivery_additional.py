from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from paper_digest.arxiv_client import Paper, PaperAnalysis
from paper_digest.config import (
    AppConfig,
    EmailConfig,
    FeishuWebhookConfig,
    StateConfig,
    WeComWebhookConfig,
)
from paper_digest.delivery import (
    DeliveryError,
    NotificationMessage,
    _build_feed_topic_sections,
    _build_receipt,
    _notification_summary,
    _single_feed_digest,
    build_notification_messages,
    configured_deliveries,
    send_configured_deliveries,
)
from paper_digest.digest import ActionItem, DigestRun, FeedDigest, FocusItem
from paper_digest.feishu_delivery import FeishuDeliveryError
from paper_digest.wecom_delivery import WeComDeliveryError


def build_digest() -> DigestRun:
    paper = Paper(
        title="Agent systems",
        summary="Digest summary",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id="https://arxiv.org/abs/1",
        abstract_url="https://arxiv.org/abs/1",
        pdf_url=None,
        published_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        tags=["评测"],
        topics=["Agents"],
        analysis=PaperAnalysis(
            conclusion="Structured topic conclusion.",
            contributions=[],
            audience="readers",
            limitations=[],
        ),
    )
    return DigestRun(
        generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
        timezone="UTC",
        lookback_hours=24,
        feeds=[
            FeedDigest(name="LLM", papers=[paper]),
            FeedDigest(name="Vision", papers=[]),
        ],
        template="zh_daily_brief",
    )


class DeliveryAdditionalTests(unittest.TestCase):
    def test_configured_deliveries_inserts_legacy_email_first(self) -> None:
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

        deliveries = configured_deliveries(config)

        self.assertIsInstance(deliveries[0], EmailConfig)
        self.assertIsInstance(deliveries[1], FeishuWebhookConfig)

    def test_build_notification_messages_respects_action_only_switches(self) -> None:
        digest = build_digest()
        digest.action_items = [
            ActionItem(
                canonical_id="doi:1",
                title="Action",
                abstract_url="https://example.com/1",
                summary="summary",
                source_label="arxiv",
                feedback_status="star",
                reasons=["overdue"],
                feed_names=["LLM"],
            )
        ]
        disabled = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
            include_actions=False,
            action_only=True,
        )
        empty_feedback = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
            include_actions=True,
            action_only=True,
        )

        self.assertEqual(build_notification_messages(disabled, digest), [])
        self.assertEqual(
            build_notification_messages(
                empty_feedback,
                DigestRun(
                    generated_at=digest.generated_at,
                    timezone=digest.timezone,
                    lookback_hours=digest.lookback_hours,
                    feeds=digest.feeds,
                ),
                feedback_only=True,
            ),
            [],
        )

    def test_build_notification_messages_keeps_empty_digest_when_not_skipping(
        self,
    ) -> None:
        delivery = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=False,
            target="digest",
        )
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[])],
        )

        messages = build_notification_messages(delivery, digest)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].kind, "digest")
        self.assertIn("LLM=0", messages[0].title)

    def test_single_feed_digest_builds_topic_highlights_from_analysis(self) -> None:
        digest = build_digest()

        single_feed = _single_feed_digest(digest, digest.feeds[0])

        self.assertEqual(single_feed.feeds[0].name, "LLM")
        self.assertEqual(
            single_feed.highlights,
            ["主题「Agents」：命中 1 篇，覆盖 LLM，代表论文包括 《Agent systems》。"],
        )
        self.assertEqual(
            single_feed.topic_sections[0].key_points,
            ["《Agent systems》〔评测〕：Structured topic conclusion."],
        )

    def test_build_feed_topic_sections_deduplicates_titles_and_key_points(self) -> None:
        published_at = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
        feed = FeedDigest(
            name="LLM",
            papers=[
                build_digest().feeds[0].papers[0],
                Paper(
                    title="Agent systems",
                    summary="Digest summary",
                    authors=["Alice"],
                    categories=["cs.AI"],
                    paper_id="https://arxiv.org/abs/2",
                    abstract_url="https://arxiv.org/abs/2",
                    pdf_url=None,
                    published_at=published_at,
                    updated_at=published_at,
                    tags=["评测"],
                    topics=["Agents"],
                    analysis=PaperAnalysis(
                        conclusion="Structured topic conclusion.",
                        contributions=[],
                        audience="readers",
                        limitations=[],
                    ),
                ),
            ],
        )

        sections = _build_feed_topic_sections(feed)

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].paper_titles, ["Agent systems"])
        self.assertEqual(
            sections[0].key_points,
            ["《Agent systems》〔评测〕：Structured topic conclusion."],
        )

    def test_build_notification_messages_omit_empty_separate_focus_and_action(
        self,
    ) -> None:
        delivery = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
            focus_target="separate",
            action_target="separate",
        )

        messages = build_notification_messages(delivery, build_digest())

        self.assertEqual([message.kind for message in messages], ["digest"])

    @patch(
        "paper_digest.delivery.send_wecom_message",
        side_effect=WeComDeliveryError("wecom failed"),
    )
    @patch(
        "paper_digest.delivery.send_feishu_message",
        side_effect=FeishuDeliveryError("feishu failed"),
    )
    def test_send_configured_deliveries_collects_channel_failures(
        self,
        _mock_send_feishu_message,
        _mock_send_wecom_message,
    ) -> None:
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
                ),
                WeComWebhookConfig(
                    webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc",
                    title_prefix="[WeCom]",
                    skip_if_empty=True,
                ),
            ],
        )

        with self.assertRaisesRegex(
            DeliveryError,
            "feishu failed; wecom failed",
        ):
            send_configured_deliveries(config, build_digest())

    def test_build_receipt_formats_focus_action_feed_and_digest_messages(self) -> None:
        self.assertEqual(
            _build_receipt(
                "Feishu webhook",
                "https://open.feishu.cn/example",
                NotificationMessage(
                    title="t",
                    body="b",
                    summary="Focus=1",
                    kind="focus",
                ),
            ),
            "Feishu webhook sent to https://open.feishu.cn/example for Focus (Focus=1)",
        )
        self.assertEqual(
            _build_receipt(
                "Feishu webhook",
                "https://open.feishu.cn/example",
                NotificationMessage(
                    title="t",
                    body="b",
                    summary="Actions=1",
                    kind="action",
                ),
            ),
            (
                "Feishu webhook sent to https://open.feishu.cn/example "
                "for Action (Actions=1)"
            ),
        )
        self.assertEqual(
            _build_receipt(
                "Feishu webhook",
                "https://open.feishu.cn/example",
                NotificationMessage(
                    title="t",
                    body="b",
                    summary="LLM=1",
                    feed_name="LLM",
                ),
            ),
            "Feishu webhook sent to https://open.feishu.cn/example for LLM (LLM=1)",
        )
        self.assertEqual(
            _build_receipt(
                "Feishu webhook",
                "https://open.feishu.cn/example",
                NotificationMessage(
                    title="t",
                    body="b",
                    summary="LLM=1",
                ),
            ),
            "Feishu webhook sent to https://open.feishu.cn/example (LLM=1)",
        )

    def test_build_notification_messages_cover_feedback_only_skip_paths(self) -> None:
        digest = build_digest()
        digest.focus_items = [
            FocusItem(
                canonical_id="doi:focus",
                title="Focus",
                abstract_url="https://example.com/focus",
                summary="focus summary",
                source_label="arxiv",
                feedback_status="star",
                reasons=["new_starred"],
            )
        ]
        digest.action_items = [
            ActionItem(
                canonical_id="doi:1",
                title="Action",
                abstract_url="https://example.com/1",
                summary="summary",
                source_label="arxiv",
                feedback_status="star",
                reasons=["overdue"],
                feed_names=["LLM"],
            )
        ]
        feedback_only_delivery = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
            include_actions=False,
        )
        feedback_action_only = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
            include_actions=True,
            action_only=True,
        )
        empty_action_only = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
            include_actions=True,
            action_only=True,
        )

        feedback_messages = build_notification_messages(
            feedback_only_delivery,
            digest,
            feedback_only=True,
        )
        self.assertEqual(len(feedback_messages), 1)
        self.assertEqual(feedback_messages[0].kind, "feedback")
        self.assertNotIn("What To Review This Week", feedback_messages[0].body)

        action_messages = build_notification_messages(
            feedback_action_only,
            digest,
            feedback_only=True,
        )
        self.assertEqual(len(action_messages), 1)
        self.assertEqual(action_messages[0].kind, "action")

        self.assertEqual(
            build_notification_messages(
                empty_action_only,
                DigestRun(
                    generated_at=digest.generated_at,
                    timezone=digest.timezone,
                    lookback_hours=digest.lookback_hours,
                    feeds=digest.feeds,
                ),
            ),
            [],
        )
        self.assertEqual(
            build_notification_messages(
                feedback_only_delivery,
                DigestRun(
                    generated_at=digest.generated_at,
                    timezone=digest.timezone,
                    lookback_hours=digest.lookback_hours,
                    feeds=digest.feeds,
                ),
                feedback_only=True,
            ),
            [],
        )

    def test_notification_summary_covers_focus_and_action_only_variants(self) -> None:
        digest = build_digest()
        digest.focus_items = [
            FocusItem(
                canonical_id="focus-as-summary",
                title="placeholder",
                abstract_url="https://example.com/focus",
                summary="focus",
                source_label="arxiv",
                feedback_status="star",
                reasons=["new_starred"],
            )
        ]
        digest.action_items = []
        focus_only_summary = _notification_summary(
            digest,
            feedback_only=False,
            kind="digest",
        )

        digest.focus_items = []
        digest.action_items = [
            ActionItem(
                canonical_id="doi:1",
                title="Action",
                abstract_url="https://example.com/1",
                summary="summary",
                source_label="arxiv",
                feedback_status="reading",
                reasons=["due_soon"],
            )
        ]
        action_only_summary = _notification_summary(
            digest,
            feedback_only=False,
            kind="digest",
        )
        feedback_action_summary = _notification_summary(
            digest,
            feedback_only=True,
            kind="digest",
        )
        digest.focus_items = [
            FocusItem(
                canonical_id="doi:focus",
                title="Focus",
                abstract_url="https://example.com/focus",
                summary="focus summary",
                source_label="arxiv",
                feedback_status="star",
                reasons=["new_starred"],
            )
        ]
        combined_summary = _notification_summary(
            digest,
            feedback_only=False,
            kind="digest",
        )

        self.assertIn("Focus=1", focus_only_summary)
        self.assertIn("Actions=1", action_only_summary)
        self.assertEqual(feedback_action_summary, "Actions=1, due_soon=1")
        self.assertIn("Focus=1", combined_summary)
        self.assertIn("Actions=1", combined_summary)

    def test_send_configured_deliveries_skips_empty_channels(self) -> None:
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
                )
            ],
        )
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[])],
        )

        self.assertEqual(send_configured_deliveries(config, digest), [])
