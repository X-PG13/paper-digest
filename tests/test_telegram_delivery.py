from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from paper_digest.config import TelegramBotConfig
from paper_digest.telegram_delivery import (
    TelegramDeliveryError,
    send_telegram_message,
)


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class TelegramDeliveryTests(unittest.TestCase):
    @patch("paper_digest.telegram_delivery.urlopen")
    def test_send_telegram_message_posts_html_payload(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            b'{"ok":true,"result":{"message_id":1}}'
        )
        config = TelegramBotConfig(
            bot_token="123456:telegram-token",
            chat_id="-1001234567890",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        send_telegram_message(
            config,
            title="[Robot] 2026-04-08 | LLM=1",
            body="# Daily Paper Digest\n\n1. [Agent systems](https://arxiv.org/abs/1)\n",
        )

        request = mock_urlopen.call_args.args[0]
        self.assertIn("/bot123456%3Atelegram-token/sendMessage", request.full_url)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["chat_id"], "-1001234567890")
        self.assertEqual(payload["parse_mode"], "HTML")
        self.assertTrue(payload["disable_web_page_preview"])
        self.assertIn("<b>[Robot] 2026-04-08 | LLM=1</b>", payload["text"])
        self.assertIn(
            '1. <a href="https://arxiv.org/abs/1">Agent systems</a>',
            payload["text"],
        )

    @patch("paper_digest.telegram_delivery.urlopen")
    def test_send_telegram_message_rejects_error_payload(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            b'{"ok":false,"description":"Bad Request: chat not found"}'
        )
        config = TelegramBotConfig(
            bot_token="123456:telegram-token",
            chat_id="-1001234567890",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaises(TelegramDeliveryError):
            send_telegram_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )
