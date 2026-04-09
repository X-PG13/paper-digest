"""Delivery orchestration across supported notification channels."""

from __future__ import annotations

from dataclasses import dataclass

from .config import (
    AppConfig,
    DeliveryConfig,
    DiscordWebhookConfig,
    EmailConfig,
    FeishuWebhookConfig,
    SlackWebhookConfig,
    TelegramBotConfig,
    WeComWebhookConfig,
)
from .digest import (
    DigestRun,
    FeedDigest,
    TopicDigest,
    digest_has_papers,
    render_markdown,
    summarize_digest,
)
from .discord_delivery import DiscordDeliveryError, send_discord_message
from .email_delivery import EmailDeliveryError, send_email_message
from .feishu_delivery import FeishuDeliveryError, send_feishu_message
from .slack_delivery import SlackDeliveryError, send_slack_message
from .telegram_delivery import TelegramDeliveryError, send_telegram_message
from .wecom_delivery import WeComDeliveryError, send_wecom_message


class DeliveryError(RuntimeError):
    """Raised when one or more configured deliveries fail."""


@dataclass(slots=True, frozen=True)
class NotificationMessage:
    title: str
    body: str
    summary: str
    feed_name: str | None = None


def configured_deliveries(
    config: AppConfig,
) -> list[DeliveryConfig]:
    """Return all configured deliveries, including legacy email config."""

    deliveries = list(config.deliveries)
    if config.email is not None:
        deliveries.insert(0, config.email)
    return deliveries


def build_notification_messages(
    delivery: DeliveryConfig,
    digest: DigestRun,
) -> list[NotificationMessage]:
    """Build delivery messages according to channel policy."""

    if _delivery_target(delivery) == "per_feed":
        return [
            _build_notification_message(
                delivery,
                _single_feed_digest(digest, feed),
                feed.name,
            )
            for feed in digest.feeds
            if feed.papers or not _skip_if_empty(delivery)
        ]

    if _skip_if_empty(delivery) and not digest_has_papers(digest):
        return []
    return [_build_notification_message(delivery, digest)]


def send_configured_deliveries(config: AppConfig, digest: DigestRun) -> list[str]:
    """Send notifications for every configured delivery and return success receipts."""

    errors: list[str] = []
    receipts: list[str] = []

    for delivery in configured_deliveries(config):
        messages = build_notification_messages(delivery, digest)
        if not messages:
            continue

        try:
            receipts.extend(_send_messages(delivery, messages))
        except (
            EmailDeliveryError,
            DiscordDeliveryError,
            FeishuDeliveryError,
            WeComDeliveryError,
            SlackDeliveryError,
            TelegramDeliveryError,
        ) as exc:
            errors.append(str(exc))

    if errors:
        raise DeliveryError("; ".join(errors))
    return receipts


def _build_notification_message(
    delivery: DeliveryConfig,
    digest: DigestRun,
    feed_name: str | None = None,
) -> NotificationMessage:
    return NotificationMessage(
        title=_build_title(delivery, digest),
        body=render_markdown(digest),
        summary=summarize_digest(digest),
        feed_name=feed_name,
    )


def _build_title(
    delivery: DeliveryConfig,
    digest: DigestRun,
) -> str:
    date_label = digest.generated_at.strftime("%Y-%m-%d")
    prefix = _title_prefix(delivery).strip()
    return f"{prefix} {date_label} | {summarize_digest(digest)}".strip()


def _single_feed_digest(digest: DigestRun, feed: FeedDigest) -> DigestRun:
    topic_sections = _build_feed_topic_sections(feed)
    highlights = _filter_highlights_for_feed(digest.highlights, feed.name)
    if not highlights and topic_sections:
        highlights = [_format_topic_highlight(topic) for topic in topic_sections]

    return DigestRun(
        generated_at=digest.generated_at,
        timezone=digest.timezone,
        lookback_hours=digest.lookback_hours,
        feeds=[
            FeedDigest(
                name=feed.name,
                papers=list(feed.papers),
                key_points=list(feed.key_points),
            )
        ],
        highlights=highlights,
        topic_sections=topic_sections,
        template=digest.template,
    )


def _build_feed_topic_sections(feed: FeedDigest) -> list[TopicDigest]:
    buckets: dict[str, TopicDigest] = {}
    for paper in feed.papers:
        for topic_name in paper.topics:
            bucket = buckets.setdefault(
                topic_name,
                TopicDigest(
                    name=topic_name,
                    paper_count=0,
                    feed_names=[feed.name],
                    paper_titles=[],
                    key_points=[],
                ),
            )
            bucket.paper_count += 1
            if paper.title not in bucket.paper_titles:
                bucket.paper_titles.append(paper.title)
            point = _format_topic_key_point(paper)
            if point not in bucket.key_points and len(bucket.key_points) < 2:
                bucket.key_points.append(point)

    return sorted(
        buckets.values(),
        key=lambda topic: (-topic.paper_count, topic.name),
    )


def _filter_highlights_for_feed(highlights: list[str], feed_name: str) -> list[str]:
    prefixes = (f"{feed_name}: ", f"{feed_name}：")
    return [highlight for highlight in highlights if highlight.startswith(prefixes)]


def _format_topic_highlight(topic: TopicDigest) -> str:
    title_label = "、".join(f"《{title}》" for title in topic.paper_titles[:2])
    return (
        f"主题「{topic.name}」：命中 {topic.paper_count} 篇，"
        f"覆盖 {topic.feed_names[0]}，"
        f"代表论文包括 {title_label}。"
    )


def _format_topic_key_point(paper: object) -> str:
    title = getattr(paper, "title", "")
    tags = getattr(paper, "tags", [])
    analysis = getattr(paper, "analysis", None)
    summary = getattr(paper, "summary", "")
    summary_line = analysis.conclusion if analysis is not None else summary
    tag_label = f"〔{' / '.join(tags)}〕" if tags else ""
    return f"《{title}》{tag_label}：{summary_line}"


def _send_messages(
    delivery: DeliveryConfig,
    messages: list[NotificationMessage],
) -> list[str]:
    receipts: list[str] = []
    if isinstance(delivery, EmailConfig):
        recipient_label = ", ".join(delivery.to_addresses)
        for message in messages:
            send_email_message(delivery, subject=message.title, body=message.body)
            receipts.append(_build_receipt("Email", recipient_label, message))
        return receipts

    if isinstance(delivery, FeishuWebhookConfig):
        for message in messages:
            send_feishu_message(delivery, title=message.title, body=message.body)
            receipts.append(
                _build_receipt("Feishu webhook", delivery.webhook_url, message)
            )
        return receipts

    if isinstance(delivery, WeComWebhookConfig):
        for message in messages:
            send_wecom_message(delivery, title=message.title, body=message.body)
            receipts.append(
                _build_receipt("WeCom webhook", delivery.webhook_url, message)
            )
        return receipts

    if isinstance(delivery, SlackWebhookConfig):
        for message in messages:
            send_slack_message(delivery, title=message.title, body=message.body)
            receipts.append(
                _build_receipt("Slack webhook", delivery.webhook_url, message)
            )
        return receipts

    if isinstance(delivery, DiscordWebhookConfig):
        for message in messages:
            send_discord_message(delivery, title=message.title, body=message.body)
            receipts.append(
                _build_receipt("Discord webhook", delivery.webhook_url, message)
            )
        return receipts

    assert isinstance(delivery, TelegramBotConfig)
    for message in messages:
        send_telegram_message(delivery, title=message.title, body=message.body)
        receipts.append(
            _build_receipt("Telegram bot", delivery.chat_id, message)
        )
    return receipts


def _build_receipt(
    channel_name: str,
    destination: str,
    message: NotificationMessage,
) -> str:
    if message.feed_name is not None:
        return (
            f"{channel_name} sent to {destination} "
            f"for {message.feed_name} ({message.summary})"
        )
    return f"{channel_name} sent to {destination} ({message.summary})"


def _skip_if_empty(
    delivery: DeliveryConfig,
) -> bool:
    return delivery.skip_if_empty


def _title_prefix(
    delivery: DeliveryConfig,
) -> str:
    if isinstance(delivery, EmailConfig):
        return delivery.subject_prefix
    return delivery.title_prefix


def _delivery_target(
    delivery: DeliveryConfig,
) -> str:
    return delivery.target
