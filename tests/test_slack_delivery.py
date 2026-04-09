from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from paper_digest.config import SlackWebhookConfig
from paper_digest.slack_delivery import SlackDeliveryError, send_slack_message


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class SlackDeliveryTests(unittest.TestCase):
    @patch("paper_digest.slack_delivery.urlopen")
    def test_send_slack_message_posts_blocks(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(b"ok")
        config = SlackWebhookConfig(
            webhook_url="https://hooks.slack.com/services/T000/B000/secret",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        send_slack_message(
            config,
            title="[Robot] 2026-04-08 | LLM=1",
            body="# Daily Paper Digest\n\n1. [Agent systems](https://arxiv.org/abs/1)\n",
        )

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["text"], "[Robot] 2026-04-08 | LLM=1")
        self.assertEqual(payload["blocks"][0]["type"], "section")
        self.assertIn(
            "*[Robot] 2026-04-08 | LLM=1*",
            payload["blocks"][0]["text"]["text"],
        )
        self.assertIn(
            "1. <https://arxiv.org/abs/1|Agent systems>",
            payload["blocks"][0]["text"]["text"],
        )

    @patch("paper_digest.slack_delivery.urlopen")
    def test_send_slack_message_rejects_error_payload(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(b"invalid_payload")
        config = SlackWebhookConfig(
            webhook_url="https://hooks.slack.com/services/T000/B000/secret",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaises(SlackDeliveryError):
            send_slack_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )
