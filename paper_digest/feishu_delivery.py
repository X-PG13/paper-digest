"""Feishu webhook delivery helpers."""

from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen

from .config import FeishuWebhookConfig

_MARKDOWN_LINK_PATTERN = re.compile(r"^(\d+\.\s*)\[(.+)]\((https?://[^)]+)\)$")


class FeishuDeliveryError(RuntimeError):
    """Raised when Feishu webhook delivery fails."""


def send_feishu_message(
    config: FeishuWebhookConfig,
    *,
    title: str,
    body: str,
) -> None:
    """Send a single notification to a Feishu incoming webhook."""

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
        raise FeishuDeliveryError(
            f"failed to send Feishu webhook notification: {exc}"
        ) from exc

    _validate_response(payload)


def _build_payload(title: str, body: str) -> dict[str, object]:
    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": _build_post_content(body),
                }
            }
        },
    }


def _build_post_content(body: str) -> list[list[dict[str, str]]]:
    rows: list[list[dict[str, str]]] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = _MARKDOWN_LINK_PATTERN.match(line)
        if match:
            prefix, text, href = match.groups()
            rows.append(
                [
                    {"tag": "text", "text": prefix},
                    {"tag": "a", "text": text, "href": href},
                ]
            )
            continue

        rows.append([{"tag": "text", "text": _normalize_text_line(line)}])
    return rows


def _normalize_text_line(line: str) -> str:
    if line.startswith("# "):
        return line[2:]
    if line.startswith("## "):
        return line[3:]
    if line.startswith("- "):
        return line[2:]
    return line


def _validate_response(payload: bytes) -> None:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise FeishuDeliveryError(
            "received malformed JSON from Feishu webhook"
        ) from exc

    if not isinstance(raw, dict):
        raise FeishuDeliveryError("Feishu webhook response payload is invalid")

    code = raw.get("code", raw.get("StatusCode", 0))
    if isinstance(code, int) and code == 0:
        return

    message = raw.get("msg") or raw.get("StatusMessage") or "unknown error"
    raise FeishuDeliveryError(
        f"Feishu webhook rejected notification with code {code}: {message}"
    )
