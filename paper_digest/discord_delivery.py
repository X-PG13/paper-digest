"""Discord webhook delivery helpers."""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .config import DiscordWebhookConfig

_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)]\((https?://[^)]+)\)")
_NUMBERED_LINK_PATTERN = re.compile(r"^(\d+\.\s*)\[(.+)]\((https?://[^)]+)\)$")
_MAX_CONTENT_TEXT = 2000
_MAX_EMBED_DESCRIPTION = 3800
_MAX_EMBED_TOTAL = 5800


class DiscordDeliveryError(RuntimeError):
    """Raised when Discord webhook delivery fails."""


def send_discord_message(
    config: DiscordWebhookConfig,
    *,
    title: str,
    body: str,
) -> None:
    """Send a single notification to a Discord incoming webhook."""

    request = Request(
        _with_wait_confirmation(config.webhook_url),
        data=json.dumps(_build_payload(title, body)).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    except OSError as exc:
        raise DiscordDeliveryError(
            f"failed to send Discord webhook notification: {exc}"
        ) from exc

    _validate_response(payload)


def _build_payload(title: str, body: str) -> dict[str, object]:
    description = _truncate_description(_normalize_markdown(body))
    embeds = [{"description": chunk} for chunk in _chunk_text(description)]
    return {
        "content": title[:_MAX_CONTENT_TEXT],
        "allowed_mentions": {"parse": []},
        "embeds": embeds,
    }


def _with_wait_confirmation(webhook_url: str) -> str:
    parts = urlsplit(webhook_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["wait"] = "true"
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


def _normalize_markdown(body: str) -> str:
    lines: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue

        numbered_link = _NUMBERED_LINK_PATTERN.match(stripped)
        if numbered_link:
            prefix, text, href = numbered_link.groups()
            lines.append(f"{prefix}**{text}**")
            lines.append(f"<{href}>")
            continue

        normalized = _convert_links(stripped)
        if normalized.startswith("# "):
            lines.append(f"**{normalized[2:]}**")
            continue
        if normalized.startswith("## "):
            lines.append(f"**{normalized[3:]}**")
            continue
        if normalized.startswith("### "):
            lines.append(f"**{normalized[4:]}**")
            continue
        if normalized.startswith("- "):
            lines.append(f"• {normalized[2:]}")
            continue
        if line.startswith("  - "):
            lines.append(f"• {stripped[2:]}")
            continue
        if line.startswith("   - "):
            lines.append(f"• {stripped[2:]}")
            continue
        lines.append(normalized)
    return "\n".join(lines).strip()


def _convert_links(value: str) -> str:
    return _MARKDOWN_LINK_PATTERN.sub(r"**\1** (<\2>)", value)


def _truncate_description(value: str) -> str:
    if len(value) <= _MAX_EMBED_TOTAL:
        return value

    suffix = "\n\n_Message truncated for Discord embed limits._"
    limit = _MAX_EMBED_TOTAL - len(suffix)
    truncated = value[:limit].rstrip()
    return truncated + suffix


def _chunk_text(value: str) -> list[str]:
    if not value:
        return ["_No digest content available._"]

    chunks: list[str] = []
    current = ""
    for line in value.splitlines():
        addition = line if not current else f"{current}\n{line}"
        if len(addition) <= _MAX_EMBED_DESCRIPTION:
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
    return chunks


def _split_long_line(value: str) -> list[str]:
    parts: list[str] = []
    remaining = value
    while remaining:
        parts.append(remaining[:_MAX_EMBED_DESCRIPTION])
        remaining = remaining[_MAX_EMBED_DESCRIPTION :]
    return parts


def _validate_response(payload: bytes) -> None:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DiscordDeliveryError(
            "received malformed JSON from Discord webhook"
        ) from exc

    if not isinstance(raw, dict):
        raise DiscordDeliveryError("Discord webhook response payload is invalid")

    if isinstance(raw.get("id"), str):
        return

    message = raw.get("message") or "unknown error"
    raise DiscordDeliveryError(f"Discord webhook rejected notification: {message}")
