from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from paper_digest.config import DiscordWebhookConfig
from paper_digest.discord_delivery import DiscordDeliveryError, send_discord_message


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class DiscordDeliveryTests(unittest.TestCase):
    @patch("paper_digest.discord_delivery.urlopen")
    def test_send_discord_message_posts_embeds(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(b'{"id":"1234567890"}')
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/123456789012345678/secret",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        send_discord_message(
            config,
            title="[Robot] 2026-04-08 | LLM=1",
            body="# Daily Paper Digest\n\n1. [Agent systems](https://arxiv.org/abs/1)\n",
        )

        request = mock_urlopen.call_args.args[0]
        self.assertIn("wait=true", request.full_url)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["content"], "[Robot] 2026-04-08 | LLM=1")
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        self.assertEqual(len(payload["embeds"]), 1)
        self.assertIn("**Daily Paper Digest**", payload["embeds"][0]["description"])
        self.assertIn("1. **Agent systems**", payload["embeds"][0]["description"])
        self.assertIn("<https://arxiv.org/abs/1>", payload["embeds"][0]["description"])

    @patch("paper_digest.discord_delivery.urlopen")
    def test_send_discord_message_rejects_error_payload(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            b'{"message":"Invalid Webhook Token"}'
        )
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/123456789012345678/secret",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaises(DiscordDeliveryError):
            send_discord_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )
