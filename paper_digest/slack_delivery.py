"""Slack incoming webhook delivery helpers."""

from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen

from .config import SlackWebhookConfig

_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)]\((https?://[^)]+)\)")
_MAX_SECTION_TEXT = 2900
_MAX_BLOCKS = 50


class SlackDeliveryError(RuntimeError):
    """Raised when Slack webhook delivery fails."""


def send_slack_message(
    config: SlackWebhookConfig,
    *,
    title: str,
    body: str,
) -> None:
    """Send a single notification to a Slack incoming webhook."""

    payload = _build_payload(title, body)
    request = Request(
        config.webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read()
    except OSError as exc:
        raise SlackDeliveryError(
            f"failed to send Slack webhook notification: {exc}"
        ) from exc

    _validate_response(response_body)


def _build_payload(title: str, body: str) -> dict[str, object]:
    content = _normalize_markdown(title, body)
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": chunk},
        }
        for chunk in _chunk_text(content)
    ]
    return {
        "text": title,
        "blocks": blocks,
    }


def _normalize_markdown(title: str, body: str) -> str:
    lines = [f"*{title}*"]
    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            lines.append("")
            continue
        normalized = _convert_links(stripped)
        if normalized.startswith("# "):
            lines.append(f"*{normalized[2:]}*")
            continue
        if normalized.startswith("## "):
            lines.append(f"*{normalized[3:]}*")
            continue
        if normalized.startswith("### "):
            lines.append(f"*{normalized[4:]}*")
            continue
        if normalized.startswith("- "):
            lines.append(f"• {normalized[2:]}")
            continue
        lines.append(normalized)
    return "\n".join(lines).strip()


def _convert_links(value: str) -> str:
    return _MARKDOWN_LINK_PATTERN.sub(r"<\2|\1>", value)


def _chunk_text(value: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in value.splitlines():
        addition = line if not current else f"{current}\n{line}"
        if len(addition) <= _MAX_SECTION_TEXT:
            current = addition
            continue
        if current:
            chunks.append(current)
            current = line
            continue
        chunks.extend(_split_long_line(line))
        current = ""

    if current:
        chunks.append(current)

    if len(chunks) <= _MAX_BLOCKS:
        return chunks
    trimmed = chunks[: _MAX_BLOCKS - 1]
    trimmed.append("_Message truncated for Slack block limits._")
    return trimmed


def _split_long_line(value: str) -> list[str]:
    parts: list[str] = []
    remaining = value
    while remaining:
        parts.append(remaining[:_MAX_SECTION_TEXT])
        remaining = remaining[_MAX_SECTION_TEXT :]
    return parts


def _validate_response(payload: bytes) -> None:
    text = payload.decode("utf-8", errors="replace").strip()
    if text.lower() == "ok":
        return
    raise SlackDeliveryError(
        f"Slack webhook rejected notification: {text or 'unknown error'}"
    )
