"""Telegram bot delivery helpers."""

from __future__ import annotations

import html
import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import TelegramBotConfig

_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)]\((https?://[^)]+)\)")
_NUMBERED_LINK_PATTERN = re.compile(r"^(\d+\.\s*)\[(.+)]\((https?://[^)]+)\)$")
_MAX_MESSAGE_TEXT = 4000


class TelegramDeliveryError(RuntimeError):
    """Raised when Telegram delivery fails."""


def send_telegram_message(
    config: TelegramBotConfig,
    *,
    title: str,
    body: str,
) -> None:
    """Send a single notification to a Telegram chat via the Bot API."""

    for chunk in _chunk_text(_normalize_markdown(title, body)):
        payload = {
            "chat_id": config.chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        request = Request(
            _build_api_url(config.bot_token),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=30) as response:
                response_body = response.read()
        except OSError as exc:
            raise TelegramDeliveryError(
                f"failed to send Telegram notification: {exc}"
            ) from exc

        _validate_response(response_body)


def _build_api_url(bot_token: str) -> str:
    return f"https://api.telegram.org/bot{quote(bot_token, safe='')}/sendMessage"


def _normalize_markdown(title: str, body: str) -> str:
    lines = [f"<b>{html.escape(title)}</b>"]
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue

        numbered_link = _NUMBERED_LINK_PATTERN.match(stripped)
        if numbered_link:
            prefix, text, href = numbered_link.groups()
            lines.append(
                f"{html.escape(prefix)}<a href=\"{html.escape(href, quote=True)}\">"
                f"{html.escape(text)}</a>"
            )
            continue

        normalized = _convert_links(stripped)
        if normalized.startswith("# "):
            lines.append(f"<b>{normalized[2:]}</b>")
            continue
        if normalized.startswith("## "):
            lines.append(f"<b>{normalized[3:]}</b>")
            continue
        if normalized.startswith("### "):
            lines.append(f"<b>{normalized[4:]}</b>")
            continue
        if normalized.startswith("- "):
            lines.append(f"• {normalized[2:]}")
            continue
        if line.startswith("  - ") or line.startswith("   - "):
            lines.append(f"• {normalized[2:]}")
            continue
        lines.append(normalized)
    return "\n".join(lines).strip()


def _convert_links(value: str) -> str:
    pieces: list[str] = []
    last_end = 0
    for match in _MARKDOWN_LINK_PATTERN.finditer(value):
        prefix = value[last_end : match.start()]
        if prefix:
            pieces.append(html.escape(prefix))
        text, href = match.groups()
        pieces.append(
            f"<a href=\"{html.escape(href, quote=True)}\">{html.escape(text)}</a>"
        )
        last_end = match.end()

    suffix = value[last_end:]
    if suffix:
        pieces.append(html.escape(suffix))
    return "".join(pieces) if pieces else html.escape(value)


def _chunk_text(value: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in value.splitlines():
        addition = line if not current else f"{current}\n{line}"
        if len(addition) <= _MAX_MESSAGE_TEXT:
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
    return chunks or ["<i>No digest content available.</i>"]


def _split_long_line(value: str) -> list[str]:
    parts: list[str] = []
    remaining = value
    while remaining:
        parts.append(remaining[:_MAX_MESSAGE_TEXT])
        remaining = remaining[_MAX_MESSAGE_TEXT :]
    return parts


def _validate_response(payload: bytes) -> None:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise TelegramDeliveryError(
            "received malformed JSON from Telegram Bot API"
        ) from exc

    if not isinstance(raw, dict):
        raise TelegramDeliveryError("Telegram Bot API response payload is invalid")

    if raw.get("ok") is True:
        return

    message = raw.get("description") or "unknown error"
    raise TelegramDeliveryError(f"Telegram Bot API rejected notification: {message}")
