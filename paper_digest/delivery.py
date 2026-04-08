"""Delivery orchestration across supported notification channels."""

from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig, EmailConfig, FeishuWebhookConfig
from .digest import (
    DigestRun,
    FeedDigest,
    digest_has_papers,
    render_markdown,
    summarize_digest,
)
from .email_delivery import EmailDeliveryError, send_email_message
from .feishu_delivery import FeishuDeliveryError, send_feishu_message


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
) -> list[EmailConfig | FeishuWebhookConfig]:
    """Return all configured deliveries, including legacy email config."""

    deliveries = list(config.deliveries)
    if config.email is not None:
        deliveries.insert(0, config.email)
    return deliveries


def build_notification_messages(
    delivery: EmailConfig | FeishuWebhookConfig,
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
        except (EmailDeliveryError, FeishuDeliveryError) as exc:
            errors.append(str(exc))

    if errors:
        raise DeliveryError("; ".join(errors))
    return receipts


def _build_notification_message(
    delivery: EmailConfig | FeishuWebhookConfig,
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
    delivery: EmailConfig | FeishuWebhookConfig,
    digest: DigestRun,
) -> str:
    date_label = digest.generated_at.strftime("%Y-%m-%d")
    prefix = _title_prefix(delivery).strip()
    return f"{prefix} {date_label} | {summarize_digest(digest)}".strip()


def _single_feed_digest(digest: DigestRun, feed: FeedDigest) -> DigestRun:
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
        highlights=_filter_highlights_for_feed(digest.highlights, feed.name),
        template=digest.template,
    )


def _filter_highlights_for_feed(highlights: list[str], feed_name: str) -> list[str]:
    prefixes = (f"{feed_name}: ", f"{feed_name}：")
    return [highlight for highlight in highlights if highlight.startswith(prefixes)]


def _send_messages(
    delivery: EmailConfig | FeishuWebhookConfig,
    messages: list[NotificationMessage],
) -> list[str]:
    receipts: list[str] = []
    if isinstance(delivery, EmailConfig):
        recipient_label = ", ".join(delivery.to_addresses)
        for message in messages:
            send_email_message(delivery, subject=message.title, body=message.body)
            receipts.append(_build_receipt("Email", recipient_label, message))
        return receipts

    for message in messages:
        send_feishu_message(delivery, title=message.title, body=message.body)
        receipts.append(_build_receipt("Feishu webhook", delivery.webhook_url, message))
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


def _skip_if_empty(delivery: EmailConfig | FeishuWebhookConfig) -> bool:
    return delivery.skip_if_empty


def _title_prefix(delivery: EmailConfig | FeishuWebhookConfig) -> str:
    if isinstance(delivery, EmailConfig):
        return delivery.subject_prefix
    return delivery.title_prefix


def _delivery_target(delivery: EmailConfig | FeishuWebhookConfig) -> str:
    return delivery.target
