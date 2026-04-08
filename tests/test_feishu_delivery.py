from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from paper_digest.config import FeishuWebhookConfig
from paper_digest.feishu_delivery import FeishuDeliveryError, send_feishu_message


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class FeishuDeliveryTests(unittest.TestCase):
    @patch("paper_digest.feishu_delivery.urlopen")
    def test_send_feishu_message_posts_title_and_content(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(b'{"code":0,"msg":"success"}')
        config = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        send_feishu_message(
            config,
            title="[Robot] 2026-04-08 | LLM=1",
            body="# Daily Paper Digest\n\n1. [Agent systems](https://arxiv.org/abs/1)\n",
        )

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["msg_type"], "post")
        self.assertEqual(
            payload["content"]["post"]["zh_cn"]["title"],
            "[Robot] 2026-04-08 | LLM=1",
        )
        self.assertEqual(
            payload["content"]["post"]["zh_cn"]["content"][1][1]["href"],
            "https://arxiv.org/abs/1",
        )

    @patch("paper_digest.feishu_delivery.urlopen")
    def test_send_feishu_message_rejects_nonzero_code(self, mock_urlopen) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            b'{"code":9999,"msg":"bad request"}'
        )
        config = FeishuWebhookConfig(
            webhook_url="https://open.feishu.cn/example",
            title_prefix="[Robot]",
            skip_if_empty=True,
        )

        with self.assertRaises(FeishuDeliveryError):
            send_feishu_message(
                config,
                title="[Robot] 2026-04-08 | LLM=1",
                body="Digest body",
            )
