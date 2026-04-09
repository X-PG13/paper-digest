"""WeCom webhook delivery helpers."""

from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen

from .config import WeComWebhookConfig

_MARKDOWN_LINK_PATTERN = re.compile(r"^(\d+\.\s*)\[(.+)]\((https?://[^)]+)\)$")
_MAX_MARKDOWN_BYTES = 4096


class WeComDeliveryError(RuntimeError):
    """Raised when WeCom webhook delivery fails."""


def send_wecom_message(
    config: WeComWebhookConfig,
    *,
    title: str,
    body: str,
) -> None:
    """Send a single notification to a WeCom incoming webhook."""

    request = Request(
        config.webhook_url,
        data=json.dumps(_build_payload(title, body)).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    except OSError as exc:
        raise WeComDeliveryError(
            f"failed to send WeCom webhook notification: {exc}"
        ) from exc

    _validate_response(payload)


def _build_payload(title: str, body: str) -> dict[str, object]:
    content = _normalize_markdown(title, body)
    return {
        "msgtype": "markdown",
        "markdown": {
            "content": content,
        },
    }


def _normalize_markdown(title: str, body: str) -> str:
    lines = [f"# {title}", ""]
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue

        match = _MARKDOWN_LINK_PATTERN.match(stripped)
        if match:
            prefix, text, href = match.groups()
            lines.append(f"{prefix}{text}")
            lines.append(f"> {href}")
            continue

        if line.startswith("   - "):
            lines.append("- " + stripped[2:])
            continue
        lines.append(stripped)

    return _truncate_markdown("\n".join(lines).strip())


def _truncate_markdown(value: str) -> str:
    payload = value.encode("utf-8")
    if len(payload) <= _MAX_MARKDOWN_BYTES:
        return value

    suffix = "\n\n> 内容过长，已截断。"
    suffix_bytes = suffix.encode("utf-8")
    limit = _MAX_MARKDOWN_BYTES - len(suffix_bytes)
    truncated = payload[:limit]
    while truncated:
        try:
            normalized = truncated.decode("utf-8")
        except UnicodeDecodeError:
            truncated = truncated[:-1]
            continue
        return normalized.rstrip() + suffix
    return suffix.strip()


def _validate_response(payload: bytes) -> None:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise WeComDeliveryError("received malformed JSON from WeCom webhook") from exc

    if not isinstance(raw, dict):
        raise WeComDeliveryError("WeCom webhook response payload is invalid")

    code = raw.get("errcode", 0)
    if isinstance(code, int) and code == 0:
        return

    message = raw.get("errmsg") or "unknown error"
    raise WeComDeliveryError(
        f"WeCom webhook rejected notification with code {code}: {message}"
    )
