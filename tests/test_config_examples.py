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
            ["LLM", "Agent/Coding Benchmarks", "SWE", "Terminal-Bench"],
        )
        self.assertEqual(config.feeds[0].source, "arxiv")
        self.assertEqual(config.feeds[1].source, "arxiv")
        self.assertIn("cs.SE", config.feeds[1].categories)
        self.assertIn("coding agent benchmark", config.feeds[1].keywords)
        self.assertIn("SWE-bench", config.feeds[1].exclude_keywords)
        self.assertEqual(config.feeds[2].source, "arxiv")
        self.assertIn("cs.SE", config.feeds[2].categories)
        self.assertIn("SWE-bench", config.feeds[2].keywords)
        self.assertEqual(config.feeds[3].source, "arxiv")
        self.assertIn("cs.SE", config.feeds[3].categories)
        self.assertIn("terminal agent", config.feeds[3].keywords)
        for feed in config.feeds:
            self.assertIn("security", feed.exclude_keywords)
            self.assertIn("prompt injection", feed.exclude_keywords)
        self.assertEqual(config.digest.template, "zh_daily_brief")
        self.assertIsNone(config.analysis)
        self.assertIsNotNone(config.translation)
        assert config.translation is not None
        self.assertEqual(config.translation.provider, "argos")
        self.assertEqual(config.translation.max_papers, 32)
        self.assertEqual(config.translation.max_summary_chars, 600)
        self.assertFalse(config.translation.fail_on_error)
        self.assertEqual(len(config.deliveries), 1)

        delivery = config.deliveries[0]
        self.assertIsInstance(delivery, FeishuWebhookConfig)
        self.assertEqual(delivery.target, "digest")
        self.assertEqual(delivery.focus_target, "digest")
        self.assertEqual(delivery.action_target, "digest")
        self.assertFalse(delivery.action_only)


if __name__ == "__main__":
    unittest.main()
