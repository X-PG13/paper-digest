from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from paper_digest.config import WeComWebhookConfig
from paper_digest.wecom_delivery import WeComDeliveryError, send_wecom_message


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class WeComDeliveryTests(unittest.TestCase):
    @patch("paper_digest.wecom_delivery.urlopen")
    def test_send_wecom_message_posts_markdown_content(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(b'{"errcode":0,"errmsg":"ok"}')
        config = WeComWebhookConfig(
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        send_wecom_message(
            config,
            title="[Robot] 2026-04-08 | LLM=1",
            body="# Daily Paper Digest\n\n1. [Agent systems](https://arxiv.org/abs/1)\n",
        )

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["msgtype"], "markdown")
        self.assertIn("# [Robot] 2026-04-08 | LLM=1", payload["markdown"]["content"])
        self.assertIn("1. Agent systems", payload["markdown"]["content"])
        self.assertIn("> https://arxiv.org/abs/1", payload["markdown"]["content"])

    @patch("paper_digest.wecom_delivery.urlopen")
    def test_send_wecom_message_rejects_nonzero_code(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            b'{"errcode":93000,"errmsg":"invalid webhook url"}'
        )
        config = WeComWebhookConfig(
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaises(WeComDeliveryError):
            send_wecom_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )
