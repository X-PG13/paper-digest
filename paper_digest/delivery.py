"""Delivery orchestration across supported notification channels."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

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
    ActionItem,
    DigestRun,
    FeedDigest,
    FocusItem,
    TopicDigest,
    digest_has_papers,
    render_action_brief_markdown,
    render_feedback_brief_markdown,
    render_focus_brief_markdown,
    render_notification_markdown,
    summarize_action_items,
    summarize_digest,
    summarize_focus_items,
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
    kind: str = "digest"


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
    *,
    feedback_only: bool = False,
) -> list[NotificationMessage]:
    """Build delivery messages according to channel policy."""

    filtered_digest = _filter_focus_for_delivery(digest, delivery)

    if feedback_only:
        feedback_digest = filtered_digest
        if not _include_focus(delivery):
            feedback_digest = _digest_without_focus(feedback_digest)
        if not _include_actions(delivery):
            feedback_digest = _digest_without_actions(feedback_digest)
        if _action_only(delivery):
            if _skip_if_empty(delivery) and not feedback_digest.action_items:
                return []
            return [_build_action_notification_message(delivery, feedback_digest)]
        if _skip_if_empty(delivery) and not _digest_has_notification_content(
            feedback_digest,
            feedback_only=True,
        ):
            return []
        return [_build_feedback_notification_message(delivery, feedback_digest)]

    if _action_only(delivery):
        if not _include_actions(delivery):
            return []
        if _skip_if_empty(delivery) and not filtered_digest.action_items:
            return []
        return [_build_action_notification_message(delivery, filtered_digest)]

    digest_for_digest = filtered_digest
    if not _include_focus(delivery) or _focus_target(delivery) == "separate":
        digest_for_digest = _digest_without_focus(digest_for_digest)
    if not _include_actions(delivery) or _action_target(delivery) == "separate":
        digest_for_digest = _digest_without_actions(digest_for_digest)

    messages: list[NotificationMessage] = []
    if _delivery_target(delivery) == "per_feed":
        for feed in digest_for_digest.feeds:
            feed_digest = _single_feed_digest(digest_for_digest, feed)
            if _skip_if_empty(delivery) and not _digest_has_notification_content(
                feed_digest,
                feedback_only=False,
            ):
                continue
            messages.append(
                _build_digest_notification_message(
                    delivery,
                    feed_digest,
                    feed_name=feed.name,
                )
            )
    else:
        if not (_skip_if_empty(delivery) and not _digest_has_notification_content(
            digest_for_digest,
            feedback_only=False,
        )):
            messages.append(
                _build_digest_notification_message(
                    delivery,
                    digest_for_digest,
                )
            )

    if _include_focus(delivery) and _focus_target(delivery) == "separate":
        if filtered_digest.focus_items:
            messages.append(
                _build_focus_notification_message(delivery, filtered_digest)
            )
    if _include_actions(delivery) and _action_target(delivery) == "separate":
        if filtered_digest.action_items:
            messages.append(
                _build_action_notification_message(delivery, filtered_digest)
            )
    return messages


def _build_digest_notification_message(
    delivery: DeliveryConfig,
    digest: DigestRun,
    *,
    feed_name: str | None = None,
) -> NotificationMessage:
    return _build_notification_message(
        delivery,
        digest,
        feed_name=feed_name,
        feedback_only=False,
        kind="digest",
    )


def _build_focus_notification_message(
    delivery: DeliveryConfig,
    digest: DigestRun,
) -> NotificationMessage:
    return _build_notification_message(
        delivery,
        digest,
        kind="focus",
    )


def _build_feedback_notification_message(
    delivery: DeliveryConfig,
    digest: DigestRun,
) -> NotificationMessage:
    return _build_notification_message(
        delivery,
        digest,
        feedback_only=True,
        kind="feedback",
    )


def _build_action_notification_message(
    delivery: DeliveryConfig,
    digest: DigestRun,
) -> NotificationMessage:
    return _build_notification_message(
        delivery,
        digest,
        kind="action",
    )


def _build_notification_message(
    delivery: DeliveryConfig,
    digest: DigestRun,
    feed_name: str | None = None,
    *,
    feedback_only: bool = False,
    kind: str = "digest",
) -> NotificationMessage:
    summary = _notification_summary(digest, feedback_only=feedback_only, kind=kind)
    if kind == "focus":
        body = render_focus_brief_markdown(digest)
    elif kind == "action":
        body = render_action_brief_markdown(digest)
    elif feedback_only:
        body = render_feedback_brief_markdown(digest)
    else:
        body = render_notification_markdown(digest, feedback_only=False)
    return NotificationMessage(
        title=_build_title(
            delivery,
            generated_at=digest.generated_at,
            summary=summary,
            kind=kind,
        ),
        body=body,
        summary=summary,
        feed_name=feed_name,
        kind=kind,
    )


def _digest_without_focus(digest: DigestRun) -> DigestRun:
    return _clone_digest(
        digest,
        focus_items=[],
        action_items=list(digest.action_items),
    )


def _digest_without_actions(digest: DigestRun) -> DigestRun:
    return _clone_digest(
        digest,
        focus_items=list(digest.focus_items),
        action_items=[],
    )


def _clone_digest(
    digest: DigestRun,
    *,
    focus_items: list[FocusItem],
    action_items: list[ActionItem],
) -> DigestRun:
    return DigestRun(
        generated_at=digest.generated_at,
        timezone=digest.timezone,
        lookback_hours=digest.lookback_hours,
        feeds=[
            FeedDigest(
                name=feed.name,
                papers=list(feed.papers),
                key_points=list(feed.key_points),
                sort_by=feed.sort_by,
            )
            for feed in digest.feeds
        ],
        highlights=list(digest.highlights),
        focus_items=list(focus_items),
        action_items=list(action_items),
        topic_sections=list(digest.topic_sections),
        template=digest.template,
        default_sort_by=digest.default_sort_by,
        sort_summary=digest.sort_summary,
        ranking_weights=dict(digest.ranking_weights),
    )


def _filter_focus_for_delivery(
    digest: DigestRun,
    delivery: DeliveryConfig,
) -> DigestRun:
    if not digest.focus_items:
        return digest

    filtered_items = list(digest.focus_items)
    allowed_statuses = set(_focus_statuses(delivery))
    if allowed_statuses:
        filtered_items = [
            item
            for item in filtered_items
            if item.feedback_status in allowed_statuses
        ]

    allowed_reasons = set(_focus_reasons(delivery))
    if allowed_reasons:
        filtered_items = [
            item
            for item in filtered_items
            if any(reason in allowed_reasons for reason in item.reasons)
        ]

    max_items = _focus_max_items(delivery)
    if max_items is not None:
        filtered_items = filtered_items[:max_items]

    if filtered_items == digest.focus_items:
        return digest
    return _clone_digest(
        digest,
        focus_items=filtered_items,
        action_items=list(digest.action_items),
    )


def send_configured_deliveries(config: AppConfig, digest: DigestRun) -> list[str]:
    """Send notifications for every configured delivery and return success receipts."""

    errors: list[str] = []
    receipts: list[str] = []

    for delivery in configured_deliveries(config):
        messages = build_notification_messages(
            delivery,
            digest,
            feedback_only=config.notify.feedback_only,
        )
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


def _build_title(
    delivery: DeliveryConfig,
    *,
    generated_at: datetime,
    summary: str,
    kind: str,
) -> str:
    prefix = _title_prefix(delivery).strip()
    suffix = ""
    if kind in {"focus", "feedback"}:
        suffix = " Focus Brief"
    elif kind == "action":
        suffix = " Action Brief"
    dated_prefix = f"{prefix}{suffix}".strip()
    date_label = generated_at.strftime("%Y-%m-%d")
    return f"{dated_prefix} {date_label} | {summary}".strip()


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
                sort_by=feed.sort_by,
            )
        ],
        highlights=highlights,
        focus_items=_filter_focus_items_for_feed(digest.focus_items, feed.name),
        action_items=_filter_action_items_for_feed(digest.action_items, feed.name),
        topic_sections=topic_sections,
        template=digest.template,
        default_sort_by=digest.default_sort_by,
        sort_summary=digest.sort_summary,
        ranking_weights=dict(digest.ranking_weights),
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


def _filter_focus_items_for_feed(
    focus_items: list[FocusItem],
    feed_name: str,
) -> list[FocusItem]:
    return [item for item in focus_items if feed_name in item.feed_names]


def _filter_action_items_for_feed(
    action_items: list[ActionItem],
    feed_name: str,
) -> list[ActionItem]:
    return [item for item in action_items if feed_name in item.feed_names]


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


def _notification_summary(
    digest: DigestRun,
    *,
    feedback_only: bool,
    kind: str,
) -> str:
    focus_summary = summarize_focus_items(digest)
    action_summary = summarize_action_items(digest)
    digest_summary = summarize_digest(digest)
    if kind == "focus":
        return focus_summary
    if kind == "action":
        return action_summary
    if feedback_only:
        parts: list[str] = []
        if digest.focus_items:
            parts.append(focus_summary)
        if digest.action_items:
            parts.append(action_summary)
        return " | ".join(parts) if parts else focus_summary
    if digest.focus_items and digest.action_items:
        return f"{digest_summary} | {focus_summary} | {action_summary}"
    if digest.focus_items:
        return f"{digest_summary} | {focus_summary}"
    if digest.action_items:
        return f"{digest_summary} | {action_summary}"
    return digest_summary


def _digest_has_notification_content(
    digest: DigestRun,
    *,
    feedback_only: bool,
) -> bool:
    if feedback_only:
        return bool(digest.focus_items or digest.action_items)
    return digest_has_papers(digest) or bool(digest.focus_items or digest.action_items)


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
    if message.kind in {"focus", "feedback"}:
        return f"{channel_name} sent to {destination} for Focus ({message.summary})"
    if message.kind == "action":
        return f"{channel_name} sent to {destination} for Action ({message.summary})"
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


def _include_focus(
    delivery: DeliveryConfig,
) -> bool:
    return delivery.include_focus


def _include_actions(
    delivery: DeliveryConfig,
) -> bool:
    return delivery.include_actions


def _focus_target(
    delivery: DeliveryConfig,
) -> str:
    return delivery.focus_target


def _action_target(
    delivery: DeliveryConfig,
) -> str:
    return delivery.action_target


def _action_only(
    delivery: DeliveryConfig,
) -> bool:
    return delivery.action_only


def _focus_statuses(
    delivery: DeliveryConfig,
) -> Sequence[str]:
    return delivery.focus_statuses


def _focus_reasons(
    delivery: DeliveryConfig,
) -> Sequence[str]:
    return delivery.focus_reasons


def _focus_max_items(
    delivery: DeliveryConfig,
) -> int | None:
    return delivery.focus_max_items


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
