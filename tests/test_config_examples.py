from __future__ import annotations

import unittest
from pathlib import Path

from paper_digest.config import FeishuWebhookConfig, load_config


class ConfigExamplesTests(unittest.TestCase):
    def test_feishu_lm_arxiv_example_loads_as_single_digest_delivery(self) -> None:
        config = load_config(Path("examples/feishu-lm-arxiv.toml"))

        self.assertEqual(config.timezone, "Asia/Shanghai")
        self.assertEqual(
            [feed.name for feed in config.feeds],
            ["LM", "Agent Runtime Security"],
        )
        self.assertEqual(config.feeds[0].source, "arxiv")
        self.assertEqual(config.feeds[1].source, "arxiv")
        self.assertIn("cs.CR", config.feeds[1].categories)
        self.assertIn("prompt injection", config.feeds[1].keywords)
        self.assertEqual(config.digest.template, "zh_daily_brief")
        self.assertIsNone(config.analysis)
        self.assertEqual(len(config.deliveries), 1)

        delivery = config.deliveries[0]
        self.assertIsInstance(delivery, FeishuWebhookConfig)
        self.assertEqual(delivery.target, "digest")
        self.assertEqual(delivery.focus_target, "digest")
        self.assertEqual(delivery.action_target, "digest")
        self.assertFalse(delivery.action_only)


if __name__ == "__main__":
    unittest.main()
